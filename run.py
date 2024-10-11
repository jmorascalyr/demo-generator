import time
import requests
import json
import os
import subprocess
import sys
from datetime import datetime

#Accept Site ID as Argument
ACCOUNT_ID = int(sys.argv[1])
SITE_ID = int(sys.argv[2])

#SentinelOne MGMT Console API KEY
S1_API_KEY = os.getenv('S1_API_KEY')


# Replace with your actual tokens

#READ_TOKEN = os.getenv('READ_TOKEN')
WRITE_TOKEN = os.getenv('WRITE_TOKEN')

# Function to read JSON data from a file
def read_json_file(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# Function to write modified JSON data to a file with each object on its own line
def write_json_file(data, file_path):
    with open(file_path, 'w') as file:
        for item in data:
            json.dump(item, file)
            file.write('\n')

def convert_offset_to_nanoseconds(offset):
    """Convert time offset string (e.g., '-800s', '-2d') to nanoseconds."""
    if offset.endswith('s'):
        return int(offset[:-1]) * 1_000_000_000
    elif offset.endswith('m'):
        return int(offset[:-1]) * 60 * 1_000_000_000
    elif offset.endswith('h'):
        return int(offset[:-1]) * 3600 * 1_000_000_000
    elif offset.endswith('d'):
        return int(offset[:-1]) * 86400 * 1_000_000_000
    return 0

# Function to query the SentinelOne API and get the first agent.uuid and endpoint.name
def query_sentinelone(query, start_time, end_time):
    url = "https://xdr.us1.sentinelone.net/api/powerQuery"
    payload = json.dumps({
      #  "token": READ_TOKEN,  Replace with your actual token
        "query": query,
        "startTime": start_time,
        "endTime": end_time
    })
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {S1_API_KEY}',
        'S1-Scope': f'{ACCOUNT_ID}:{SITE_ID}'
    }
    response = requests.post(url, headers=headers, data=payload)
    response.raise_for_status()  # Ensure we notice bad responses
    print(response.text)
    return response.json()


def upload_to_api(file_path):
    url = "https://xdr.us1.sentinelone.net/api/addEvents"
    
    # Read the modified file and prepare payload
    with open(file_path, 'r') as file:
        events = [json.loads(line) for line in file]  # Assumes each line contains a JSON object
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {S1_API_KEY}',
        'S1-Scope': f'{ACCOUNT_ID}:{SITE_ID}'
    }

    # Session-related details
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
            message = json.dumps(event)

            # Extract the timestamp from the event and convert it to nanoseconds
            event_timestamp = event.get('timestamp')
            if event_timestamp:
                # Convert the timestamp to Unix time in nanoseconds
                ts = int(datetime.strptime(event_timestamp, '%Y-%m-%dT%H:%M:%S.%fZ').timestamp() * 1_000_000_000)
            else:
                ts = int(datetime.now().timestamp() * 1_000_000_000)  # Fallback to current time if no timestamp is found

            payload["events"].append({
                "thread": event.get('thread', "1"),  # Default thread ID
                "ts": ts,  # Use the event's timestamp
                "sev": int(event.get('sev', 3)),  # Severity as integer
                "attrs": {
                    "message": message,
                    "parser": "json",
                    "test": "5"  # Adjust this as needed
                }
            })
        
        print("Payload to upload:", json.dumps(payload, indent=2))

        for attempt in range(3):
            try:
                response = requests.post(url, headers=headers, json=payload)
                response.raise_for_status()  # Check if request was successful
                print(f"Uploaded batch {i // batch_size + 1}: {response.status_code}, {response.text}")
                break
            except requests.exceptions.RequestException as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff


def update_json_data(json_data, response_data, time_offsets, time_offset_default):
    # Print the type and content of response_data for debugging
    print(f"Type of response_data: {type(response_data)}")
    print(f"Content of response_data: {response_data}")

    if isinstance(response_data, dict):
        columns = response_data.get('columns', [])
        values = response_data.get('values', [])

        if not values:
            print("No values found in the response_data")
            return json_data

        # Use the first record from values to extract the required information
        first_record_data = values[0]  # This should be the list containing actual data

        # Build a dictionary of column names to their indices
        column_indices = {col['name']: idx for idx, col in enumerate(columns)}

        # Extract endpoint name and timestamp based on column indices
        endpoint_name_index = column_indices.get('endpoint.name', -1)
        timestamp_index = column_indices.get('timestamp', -1)

        if timestamp_index != -1:
            first_timestamp = int(first_record_data[timestamp_index])
        else:
            print("Timestamp column not found in response_data")
            first_timestamp = None

        if endpoint_name_index != -1:
            first_endpoint_name = first_record_data[endpoint_name_index]
        else:
            first_endpoint_name = None

        # Print the extracted data for debugging
        print(f"First endpoint name: {first_endpoint_name}")
        print(f"First timestamp: {first_timestamp}")

        for idx, item in enumerate(json_data):
            if "endpoint.name" in item and first_endpoint_name is not None:
                item["endpoint.name"] = first_endpoint_name

            if "timestamp" in item and first_timestamp is not None:
                # Determine the correct time offset for this index
                if idx < len(time_offsets):
                    time_offset = time_offsets[idx]
                else:
                    time_offset = time_offset_default

                # Convert time_offset to seconds and update the timestamp
                time_offset_seconds = convert_offset_to_nanoseconds(time_offset)
                updated_timestamp = first_timestamp + time_offset_seconds

                # Convert updated timestamp to ISO 8601 format
                updated_timestamp_iso = datetime.utcfromtimestamp(updated_timestamp / 1e9).isoformat() + 'Z'  # Assuming timestamp is in nanoseconds

                item["timestamp"] = updated_timestamp_iso

                print(f"Updated timestamp for index {idx} to {updated_timestamp_iso}")  # Debugging line
            else:
                print(f"Skipping index {idx}: 'timestamp' not in item or 'first_timestamp' is None")

    else:
        print("Error: response_data is not a dictionary")
        return json_data  # Return the original data if there's an error

    return json_data




# Function to read configurations from a config file
def read_config(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def call_static_script():
    print("Calling static.py script...")
    subprocess.run(["python3", "static.py", str(ACCOUNT_ID), str(SITE_ID) ], check=True)

def main():
    # Load the configuration file
    config = read_config('config.json')
    for config_item in config:
        # Extract values from the config
        query = config_item.get('query', '')
        time_offset_array = config_item.get('time_offset', [])
        time_offset_default = config_item.get('time_offset_default', '+0m')
        file_path = config_item.get('file')
        start_time = config_item.get('startTime')
        end_time = config_item.get('endTime')

        # Read the original JSON data
        json_data = read_json_file(file_path)

        if query:  # Only run the query if a query string is provided
            # Query the SentinelOne API
            query_results = query_sentinelone(query, start_time, end_time)

            # Debugging: Print the query results
            print(f"Query results: {query_results}")

            # Check if 'values' is present and non-empty
            if isinstance(query_results, dict) and 'values' in query_results and query_results['values']:
                # Update the JSON data with the response data
                updated_data = update_json_data(json_data, query_results, time_offset_array, time_offset_default)
            else:
                print(f"No data returned from the query: {query}")
                updated_data = json_data  # No changes, just use the original data
        else:
            updated_data = json_data  # No query, just use the original data

        # Write the modified data to a new file
        modified_file_path = file_path.replace('.json', '-modified.json')
        write_json_file(updated_data, modified_file_path)

        # Upload the modified data to the API
        upload_to_api(modified_file_path)

        print(f"Modified data has been written to {modified_file_path} and uploaded to the API.")




if __name__ == "__main__":
    main()
    call_static_script()
