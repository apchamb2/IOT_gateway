"""a FastAPI app that demonstrates create, read, update, and delete (CRUD) operations. It’s “time-decoupled” because the CRUD service persists data to the MongoDB database independently of when the sensor data arrives, 
meaning your gRPC microservice can operate in parallel or feed data at any time.
http://localhost:8000/docs
"""

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional
from pymongo import MongoClient
from kafka import KafkaProducer
from kafka.errors import KafkaError
import os, traceback

app = FastAPI()

# 1. Configure the MongoDB connection
#    If running locally, use "mongodb://localhost:27017"
#    For MongoDB Atlas, replace with your connection string
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["iot_db"]  # Database name
collection = db["sensor_data"]  # Collection name

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: v.encode('utf-8')
)


# Helper function to send messages to Kafka with error handling
def send_to_kafka(topic: str, message: str):
    try:
        future = producer.send(topic, value=message)
        record_metadata = future.get(timeout=10)  # Wait for acknowledgment
        print(f"Message sent to topic: {record_metadata.topic}, "
              f"partition: {record_metadata.partition}, offset: {record_metadata.offset}")
    except KafkaError as e:
        print(f"Failed to send message to Kafka due to KafkaError: {e}")
    except Exception as e:
        print(f"Unexpected error while sending to Kafka: {e}")

# 2. Define a Pydantic model for sensor data
class SensorData(BaseModel):
    device_id: str = Field(..., description="Unique device identifier")
    timestamp: str = Field(..., description="Timestamp in ISO format")
    temperature: float = Field(..., description="Temperature reading")
    humidity: float = Field(..., description="Humidity reading")

# Middleware to send Kafka messages on exceptions
@app.middleware("http")
async def kafka_error_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        # Log and send the exception details to Kafka
        error_details = {
            "path": request.url.path,
            "method": request.method,
            "error": str(exc),
            "traceback": traceback.format_exc()
        }
        send_to_kafka('error-events', str(error_details))
        raise
    
# 3. Create (POST) - Insert sensor data into MongoDB
@app.post("/sensor/", response_model=dict)
async def create_sensor_data(data: SensorData):
    sensor_dict = data.dict()
    send_to_kafka('workflow-events', data.model_dump_json())
    result = collection.insert_one(sensor_dict)
    if result.inserted_id:
        return {"message": "Data inserted successfully", "id": str(result.inserted_id)}
    raise HTTPException(status_code=500, detail="Error inserting data")

# 4. Read (GET) - Fetch sensor data by device_id
@app.get("/sensor/{device_id}", response_model=list)
async def get_sensor_data(device_id: str):
    # Retrieve all documents with the given device_id
    documents = list(collection.find({"device_id": device_id}, {"_id": 0}))
    if not documents:
        raise HTTPException(status_code=404, detail="No data found for this device")
    return documents

# 5. Update (PUT) - Update sensor data by device_id
@app.put("/sensor/{device_id}", response_model=dict)
async def update_sensor_data(device_id: str, data: SensorData):
    # We assume 'timestamp' might differ or that the record we want to update
    # is identified by device_id and the provided timestamp
    update_filter = {"device_id": device_id, "timestamp": data.timestamp}
    new_values = {"$set": data.dict()}
    result = collection.update_one(update_filter, new_values)

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="No matching record to update")
    send_to_kafka('workflow-events', data.model_dump_json())
    return {"message": "Data updated successfully"}

# 6. Delete (DELETE) - Remove sensor data by device_id
@app.delete("/sensor/{device_id}", response_model=dict)
async def delete_sensor_data(device_id: str, timestamp: Optional[str] = None):
    # If 'timestamp' is provided, remove a specific reading; otherwise remove all readings for this device
    if timestamp:
        delete_filter = {"device_id": device_id, "timestamp": timestamp}
    else:
        delete_filter = {"device_id": device_id}
    result = collection.delete_many(delete_filter)

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No matching data found to delete")
    send_to_kafka('workflow-events', str(delete_filter))
    return {"message": f"Deleted {result.deleted_count} record(s)"}
