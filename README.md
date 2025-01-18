# IOT_gateway
Distributed IoT Gateway System with Edge ML

=====================================================
 IoT gRPC Server with MongoDB - Quick Start Guide
=====================================================

This project demonstrates a simple gRPC microservice that accepts synthetic sensor data 
and stores it in MongoDB for later retrieval and analysis.

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
       mongod
   - MongoDB Atlas:
       Make sure your connection URI is correct in server.py

-----------------------------------------------------
3) RUNNING THE SERVER
-----------------------------------------------------
1. Open a terminal in the project folder.
2. Start the gRPC server:
   python server.py
3. The server listens on port 50051 by default.

-----------------------------------------------------
4) RUNNING THE CLIENT
-----------------------------------------------------
1. Open another terminal (keep the server running).
2. Run the client to send synthetic sensor data:
   python client.py

   The client sends multiple data points to the gRPC server, 
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




