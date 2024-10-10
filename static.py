import csv
import json
import threading
import time
import requests
import random
from datetime import datetime, timedelta
import os
import ssl
import sys

#Accept Site ID as Argument
ACCOUNT_ID = int(sys.argv[1])
SITE_ID = int(sys.argv[2])

#SentinelOne MGMT Console API KEY
S1_API_KEY = os.getenv('S1_API_KEY')

# Function to read the noise configuration file
def read_noise_config(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# Function to read events from a CSV file
def read_events_from_csv(file_path):
    with open(file_path, mode='r') as file:
        reader = csv.DictReader(file)
        events = list(reader)
        print(f"Read {len(events)} events from {file_path}.")  # Debug print
        return events

# Function to parse start time strings (e.g., "24h", "1d") into timedelta
def parse_start_time(start_time_str):
    if start_time_str.endswith('h'):
        hours = int(start_time_str[:-1])
        return timedelta(hours=hours)
    elif start_time_str.endswith('d'):
        days = int(start_time_str[:-1])
        return timedelta(days=days)
    return timedelta()

def format_utc_timestamp(dt):
    # Format the datetime in UTC as a string
    return f"{dt.strftime('%Y-%m-%dT%H:%M:%S.%f')}Z"  # Appending 'Z' to indicate UTC

# Function to upload events to the API
def upload_events(events):
    url = "https://xdr.us1.sentinelone.net/api/addEvents"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {S1_API_KEY}',
        'S1-Scope': f'{ACCOUNT_ID}:{SITE_ID}'
    }

    session_id = "your_session_id_here"
    session_info = {
        "serverType": "your_server_type",
        "serverId": "your_server_id"
    }

    batch_size = 500
    for i in range(0, len(events), batch_size):
        batch = events[i:i + batch_size]

        payload = {
            "session": session_id,
            "sessionInfo": session_info,
            "events": []
        }

        for event in batch:
            # Convert the entire event to JSON string for the message field
            message = json.dumps(event)  # Convert event to JSON string

            payload["events"].append({
                "thread": event.get('thread', "1"),  # Default thread ID
                "ts": int(datetime.now().timestamp() * 1_000_000_000),  # Current timestamp
                "sev": int(event.get('sev', 3)),  # Ensure severity is an integer
                "attrs": {
                    "message": message,  # Set the message as the JSON string
                    "parser": "json",
                    "test": "5"
                }
            })
        print("Payload to upload:", json.dumps(payload, indent=2))

        for attempt in range(3):
            try:
                response = requests.post(url, headers=headers, json=payload)
                response.raise_for_status()
                print(f"Uploaded batch {i // batch_size + 1}: {response.status_code}, {response.text}")
                break
            except requests.exceptions.RequestException as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                time.sleep(2 ** attempt)

def generate_and_upload_events(file_path, start_time, stop_event, num_batches, events_per_batch, min_sleep, max_sleep):
    events = read_events_from_csv(file_path)
    timestamp_field_exists = 'timestamp' in events[0].keys() if events else False
    
    # Calculate time increment for evenly distributing events over one hour
    time_increment = 3600 / events_per_batch  # 3600 seconds in an hour

    for batch_num in range(num_batches):
        if stop_event.is_set():  # Check if stop event is triggered
            break
        
        current_batch_start_time = start_time + timedelta(hours=batch_num)  # Start time for this batch
        output = []

        for event_num in range(events_per_batch):  # Generate events for this batch
            n = random.randint(0, len(events) - 1)
            event = events[n].copy()

            # Set the timestamp for each event, evenly distributed over one hour
            event_timestamp = current_batch_start_time + timedelta(seconds=time_increment * event_num)
            event['timestamp'] = format_utc_timestamp(event_timestamp)  # Set timestamp in UTC

            output.append(event)

        upload_events(output)  # Upload the batch of generated events
        time.sleep(random.randint(1, max_sleep))  # Sleep for a random interval

def continuous_event_generation(file_path, stop_event, events_per_batch, min_sleep, max_sleep):
    events = read_events_from_csv(file_path)

    while not stop_event.is_set():  # Run until stop event is triggered
        current_time = datetime.utcnow()  # Get current time in UTC
        output = []

        for event_num in range(events_per_batch // 60):
            n = random.randint(0, len(events) - 1)
            event = events[n].copy()
            event['timestamp'] = format_utc_timestamp(current_time)  # Use the current UTC timestamp
            output.append(event)

        upload_events(output)  # Upload the batch of generated events
        time.sleep(random.randint(min_sleep, max_sleep))  # Sleep for a random interval


def main():
    print(S1_API_KEY)
    noise_config = read_noise_config('noise.conf')
    stop_event = threading.Event()  # Create a stop event
    threads = []  # Keep track of all threads

    for config in noise_config:
        file_path = config.get("file")
        start_time_str = config.get("startTime")
        num_batches = config.get("numBatches", 24)  # Default to 24 if not specified
        events_per_batch = config.get("eventsPerBatch", 500)  # Default to 500 if not specified
        continuous_generation = config.get("continuous_generation", False)
        min_sleep = config.get("minSleepInterval", 10)  # Default to 10 seconds
        max_sleep = config.get("maxSleepInterval", 30)  # Default to 30 seconds

        if not start_time_str:
            print(f"Warning: 'startTime' not found for {file_path}. Skipping this file.")
            continue
        
        start_time_delta = parse_start_time(start_time_str)
        start_time = datetime.utcnow() - start_time_delta  # Calculate start time based on config

        # Start generating events for batches
        thread = threading.Thread(target=generate_and_upload_events, args=(file_path, start_time, stop_event, num_batches, events_per_batch, min_sleep, max_sleep))
        thread.start()
        threads.append(thread)  # Keep track of batch thread

        if continuous_generation:
            print("Continuous generation mode enabled. Generating events indefinitely...")
            continuous_thread = threading.Thread(target=continuous_event_generation, args=(file_path, stop_event, events_per_batch, min_sleep, max_sleep))
            continuous_thread.start()
            threads.append(continuous_thread)  # Keep track of continuous thread

    try:
        while any(t.is_alive() for t in threads):  # Keep main thread alive while any worker threads are running
            time.sleep(1)
    except KeyboardInterrupt:
        print("Interrupted! Stopping all threads...")
        stop_event.set()  # Signal threads to stop
        for t in threads:
            t.join()  # Wait for all threads to finish
        print("All threads have been stopped.")

if __name__ == "__main__":
    main()
