# **Demo Generator**

This project contains a Python script (`run.py`) designed to query endpoint logs (such as Windows Event Logs and Okta logs), and then supplement them with additional noise or synthetic logs. The goal is to provide comprehensive data for demos, testing, and simulations by combining real log queries with configurable supplemental logs.

## **Table of Contents**

* Requirements  
* Installation  
* Configuration  
  * Config File Structure  
* Noise Generator  
  * Noise Config File Structure  
* Running the Script  
* Examples  
* Logs  
* Contributing  
* License

## **Requirements**

Ensure that the following dependencies are installed on your system:

* Python 3.x

Required Python packages (install via `requirements.txt`):  
bash  

`pip install -r requirements.txt`

* 

## **Installation**

Clone this repository to your local machine:  
bash  

`git clone https://github.com/your-repo/demo-generator.git`

1. 

Navigate to the project directory:  
bash  

`cd demo-generator`

2. 

Install the required dependencies:  
bash  

`pip install -r requirements.txt`

3. 

## **Configuration**

The script relies on a configuration file (`config.json`) that defines the log queries for endpoints and the time ranges to fetch. Each query can be supplemented with noise logs to create a richer dataset.

### **Config File Structure**

Below is an example of the `config.json` structure:

json  

`[`  
    `{`  
        `"name": "windows event logs client",`  
        `"query": "agent.uuid = * endpoint.name contains 'W10-Attk'| group timestamp = oldest(timestamp), count = count() by agent.uuid, endpoint.name | limit 1",`  
        `"time_offset": ["+1m", "-5m", "+2m"],`  
        `"time_offset_default": "+5m",`  
        `"startTime": "8d",`  
        `"endTime": "0h",`  
        `"file": "wel-client.json"`  
    `},`  
    `{`  
        `"name": "windows server client",`  
        `"query": "agent.uuid = * endpoint.name contains 'BORG'| group timestamp = oldest(timestamp), count = count() by agent.uuid, endpoint.name | limit 1",`  
        `"time_offset": ["+1m", "-5m", "+2m"],`  
        `"time_offset_default": "-5m",`    
        `"startTime": "8d",`  
        `"endTime": "0h",`  
        `"file": "wel-server.json"`  
    `},`  
    `{`  
        `"name": "okta",`  
        `"query": "agent.uuid = * | limit 1 | columns timestamp",`  
        `"time_offset": ["-800s", "-755s", "-743s","-733s","-725s"],`  
        `"time_offset_default": "-5m",`    
        `"startTime": "8d",`  
        `"endTime": "0h",`  
        `"file": "okta.json"`  
    `}`  
`]`

### **Explanation of Config File Fields**

* **`name`**: Descriptive name for the data source (e.g., Windows Event Logs or Okta logs).  
* **`query`**: The query to fetch logs, specific to the log data source (e.g., `agent.uuid = * endpoint.name contains 'W10-Attk'`).  
* **`time_offset`**: A list of time offsets that can adjust the query’s time range.  
* **`time_offset_default`**: The default time offset applied when no other offset is provided.  
* **`startTime`**: Relative start time for the query (e.g., "8d" means 8 days ago).  
* **`endTime`**: Relative end time for the query (e.g., "0h" means current time).  
* **`file`**: The file to which the query results are saved in JSON format.

## **Noise Generator**

The **noise generator** supplements real log queries by generating additional log events. This is useful for demos, testing, or simulation where more comprehensive datasets are required.

### **Noise Config File Structure**

Below is an example of the `noise_config.json` structure:

json  

`[`  
    `{`  
        `"file": "noise/okta_ocsf.csv",`  
        `"startTime": "24h",`  
        `"numBatches": 24,`  
        `"eventsPerBatch": 60,`  
        `"continuous_generation": "true",`  
        `"minSleepInterval": 1,`  
        `"maxSleepInterval": 1`  
    `},`  
    `{`  
        `"file": "noise/wel_ocsf.csv",`  
        `"startTime": "24h",`  
        `"numBatches": 24,`  
        `"eventsPerBatch": 60,`  
        `"continuous_generation": "true",`  
        `"minSleepInterval": 1,`  
        `"maxSleepInterval": 1`  
    `},`  
    `{`  
        `"file": "noise/cloudflare.csv",`  
        `"startTime": "24h",`  
        `"numBatches": 24,`  
        `"eventsPerBatch": 60,`  
        `"continuous_generation": "true",`  
        `"minSleepInterval": 1,`  
        `"maxSleepInterval": 1`  
    `}`  
`]`

### **Explanation of Noise Config File Fields**

* **`file`**: The output CSV file where the noise events are written.  
* **`startTime`**: The time from which the noise generation begins (e.g., "24h" means 24 hours ago).  
* **`numBatches`**: The number of batches of events to generate.  
* **`eventsPerBatch`**: The number of events in each batch.  
* **`continuous_generation`**: If set to `"true"`, events will continue generating, with intervals between batches.  
* **`minSleepInterval`**: Minimum sleep time between batches (in seconds).  
* **`maxSleepInterval`**: Maximum sleep time between batches (in seconds).

## **Running the Script**

You need to provide the required parameters to run the script, such as the account ID and site ID.

### **Command Syntax**

bash  

`python3 run.py {accountid} {siteid}`

For example:

bash  

`python3 run.py 123456 7890`

This will execute the query for the provided `accountid` and `siteid`.

### **Running the Noise Generator**

The noise generator is automatically executed based on the configurations in `noise_config.json`, generating additional noise events as defined.

## **Examples**

### **Example 1: Query Windows Event Logs and Supplement with Noise**

json  

`{`  
    `"name": "windows event logs client",`  
    `"query": "agent.uuid = * endpoint.name contains 'W10-Attk'| group timestamp = oldest(timestamp), count = count() by agent.uuid, endpoint.name | limit 1",`  
    `"time_offset": ["+1m", "-5m", "+2m"],`  
    `"time_offset_default": "+5m",`  
    `"startTime": "8d",`  
    `"endTime": "0h",`  
    `"file": "wel-client.json"`  
`}`

This query fetches Windows Event Logs for the client machine `W10-Attk` with a default time offset of \+5 minutes and writes the results to `wel-client.json`.

### **Example 2: Generate Okta Noise Data**

json  

`{`  
    `"file": "noise/okta_ocsf.csv",`  
    `"startTime": "24h",`  
    `"numBatches": 24,`  
    `"eventsPerBatch": 60,`  
    `"continuous_generation": "true",`  
    `"minSleepInterval": 1,`  
    `"maxSleepInterval": 1`  
`}`

This configuration generates noise logs for Okta, writing to `okta_ocsf.csv`, simulating 24 hours of data with 60 events per batch.

## **Logs**

Execution logs are printed to the console, showing query progress and noise generation. Errors or warnings are logged to help with troubleshooting.

## **Contributing**

Contributions are welcome\! To contribute:

1. Fork this repository.  
2. Create a feature branch: `git checkout -b feature-branch`.  
3. Commit your changes: `git commit -m 'Add new feature'`.  
4. Push to the branch: `git push origin feature-branch`.  
5. Open a pull request.

## **License**

This project is licensed under the MIT License. See the `LICENSE` file for details.

---

This revised `README.md` now reflects the repository's purpose of querying endpoint logs and supplementing them with noise for demos and testing, and is renamed as **Demo Generator**.

