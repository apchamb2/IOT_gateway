# IOT_gateway
Distributed IoT Gateway System with Edge ML for Distrubuted Systems 2025

 Quick Start Guide
=====================================


CONTENTS:
1. Prerequisites
2. Setup Instructions
3. Running the Server
4. Running the Client
5. Verifying Data in MongoDB
6. Troubleshooting

-----------------------------------------------------
1) PREREQUISITES
-----------------------------------------------------
- Python 3.11+ installed
- A local or remote MongoDB instance:
  - Local: Download & install MongoDB Community Edition
  - Remote: MongoDB Atlas account with a connection URI
- Installed Python dependencies (see requirements.txt):
  - grpcio, grpcio-tools, pymongo
- Installed Java (JDK)
- Installed Kafka
- Installed Docker (http://localhost:9090)
   - Installed/updated WSL 2 if needed (Windows)
- Installed Grafana (http://localhost:3000 )

-----------------------------------------------------
2) SETUP INSTRUCTIONS
-----------------------------------------------------
1. CLONE THE REPOSITORY
   git clone <REPO_URL>
   cd <PROJECT_FOLDER>

2. CREATE AND ACTIVATE A VIRTUAL ENVIRONMENT 
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Mac/Linux:
   source venv/bin/activate

3. INSTALL REQUIRED DEPENDENCIES
   pip install -r requirements.txt

4. ENSURE MONGODB IS RUNNING
   - Local:
       - mongod
       - mongosh --host localhost --port 27017
   - MongoDB Atlas:
       Make sure your connection URI is correct in server.py

5. KAFKA INSTALLATION AND SETUP (macOS)
   - Install:
       brew install kafka
   - Start Kafka Service:
       - brew services start zookeeper
       - brew services start kafka
   - Verify Kafka Service is Running:
       kafka-topics --list --bootstrap-server localhost:9092
   - Install JDK:
       brew install openjdk
   - Install Confluent Kafka Python Package:
       pip install confluent-kafka

    KAFKA SETUP (Windows)
   - Start Zookeeper
      - In powershell: 
      cd C:\kafka_2.13-3.9.0
      .\bin\windows\zookeeper-server-start.bat .\config\zookeeper.properties
   - Start Kafka
      - In another powershell window:
      cd C:\kafka_2.13-3.9.0
      .\bin\windows\kafka-server-start.bat .\config\server.properties
   


6. CREATE KAFKA TOPIC
   kafka-topics --create --topic workflow-events --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1

   CREATE KAFKA TOPIC (Windows)
   - in powershell:
   .\bin\windows\kafka-topics.bat --create --topic topic --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1

-----------------------------------------------------
3) RUNNING THE SERVER
-----------------------------------------------------
1. Open a terminal in the project folder.
2. Start the gRPC server:
   python server.py
3. The server listens on port 50051 by default.
4. In another terminal in the project folder, start the Kafka Consumer to Listen to Events:
   python kafka_consumer.py

-----------------------------------------------------
4) RUNNING THE CLIENT
-----------------------------------------------------
1. Open another terminal (keep the server running).
2. Run the client to send synthetic sensor data:
   python client.py

   The client sends multiple data points to the gRPC server and kafka consumer,
   which in turn stores them in MongoDB.

-----------------------------------------------------
5) VERIFYING DATA IN MONGODB
-----------------------------------------------------
A) MONGODB COMPASS:
   1. Launch MongoDB Compass.
   2. Connect to your MongoDB instance (e.g., mongodb://localhost:27017).
   3. Find the "iot_db" database and "sensor_data" collection.
   4. Check for newly inserted documents containing fields:
      device_id, timestamp, temperature, humidity, etc.

B) MONGO SHELL (OPTIONAL):
   1. Run: mongo
   2. Switch to the database: 
        use iot_db
   3. Query the collection:
        db.sensor_data.find().pretty()

-----------------------------------------------------
6) PROMETHEUS AND GRAFANA
-----------------------------------------------------
1. From docker-compose.yml 'run all services' or in a bash terminal: docker compose up -d --build

A) PROMETHEUS
   1. open browser to http://localhost:9090, navigate to Status -> targets 
   2. generate graphs to test
B) GRAFANA
   1. open browser to http://localhost:3000, log in as admin password: admin
   2. Configuration → Data Sources
   3. add data source Prometheus
   4. Configure http://localhost:9090 or if running in docker: http://prometheus:9090
   5. Save and test
   6. Dashboards → New → New Dashboard
   7. Add new panels for: fastapi_requests_total, prometheus_http_requests_total, kafka_messages_sent_total
   8. send requests to the FastAPI service, produce Kafka messages


-----------------------------------------------------
6) TROUBLESHOOTING
-----------------------------------------------------
1. If you receive "Connection refused" or "Failed to connect to server":
   - Make sure your MongoDB instance is running (mongod).
   - Check the database URI in server.py for typos.

2. If "ModuleNotFoundError" for grpcio or pymongo:
   - Make sure you've installed dependencies with: pip install -r requirements.txt
   - Confirm you are in the correct Python virtual environment.

3. If data doesn't appear in Compass:
   - Refresh Compass or ensure you're looking at the correct database and collection.
   - Check the server logs for any errors during insertion.

4. For Kafka, we need to install Kafka-python-ng otherwise, it shows a module not found error.


