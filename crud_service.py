"""
a FastAPI app that demonstrates create, read, update, and delete (CRUD) operations. 
It’s “time-decoupled” because the CRUD service persists data to the MongoDB database 
independently of when the sensor data arrives.
http://localhost:8000/docs
"""
"""
CRUD FastAPI service with Prometheus instrumentation using lifespan.
"""

import os, traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional
from pymongo import MongoClient
from kafka import KafkaProducer
from kafka.errors import KafkaError

# Prometheus instrumentation
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter


@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP CODE
    # Attach Prometheus Instrumentator
    Instrumentator().instrument(app).expose(app, include_in_schema=True, endpoint="/metrics")
    
    yield  # The app is now ready to handle requests

    # SHUTDOWN CODE (optional)
    # e.g., close database connections, finalize logs, etc.

# Create the FastAPI app, passing the lifespan context manager
app = FastAPI(lifespan=lifespan)

# ---------------------------------------------------------------------------
# KAFKA + MONGODB SETUP
# ---------------------------------------------------------------------------
producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: v.encode('utf-8')
)

# Count how many messages we send to Kafka
kafka_messages_sent = Counter(
    'kafka_messages_sent_total',
    'Number of messages successfully sent to Kafka'
)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["iot_db"]
collection = db["sensor_data"]

def send_to_kafka(topic: str, message: str):
    try:
        future = producer.send(topic, value=message)
        record_metadata = future.get(timeout=10)
        kafka_messages_sent.inc()
        print(f"Message sent to topic: {record_metadata.topic}, "
              f"partition: {record_metadata.partition}, offset: {record_metadata.offset}")
    except KafkaError as e:
        print(f"Failed to send message to Kafka due to KafkaError: {e}")
    except Exception as e:
        print(f"Unexpected error while sending to Kafka: {e}")

# ---------------------------------------------------------------------------
# Pydantic Model
# ---------------------------------------------------------------------------
class SensorData(BaseModel):
    device_id: str = Field(..., description="Unique device identifier")
    timestamp: str = Field(..., description="Timestamp in ISO format")
    temperature: float = Field(..., description="Temperature reading")
    humidity: float = Field(..., description="Humidity reading")

# ---------------------------------------------------------------------------
# MIDDLEWARE
# ---------------------------------------------------------------------------
@app.middleware("http")
async def kafka_error_middleware(request: Request, call_next):
    """
    Catches exceptions, sends them to Kafka, then re-raises.
    """
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        error_details = {
            "path": request.url.path,
            "method": request.method,
            "error": str(exc),
            "traceback": traceback.format_exc()
        }
        send_to_kafka('error-events', str(error_details))
        raise

# ---------------------------------------------------------------------------
# CRUD ENDPOINTS
# ---------------------------------------------------------------------------
@app.post("/sensor/", response_model=dict)
async def create_sensor_data(data: SensorData):
    sensor_dict = data.dict()
    send_to_kafka('workflow-events', data.json())  # or data.model_dump_json()
    result = collection.insert_one(sensor_dict)
    if result.inserted_id:
        return {"message": "Data inserted successfully", "id": str(result.inserted_id)}
    raise HTTPException(status_code=500, detail="Error inserting data")

@app.get("/sensor/{device_id}", response_model=list)
async def get_sensor_data(device_id: str):
    documents = list(collection.find({"device_id": device_id}, {"_id": 0}))
    if not documents:
        raise HTTPException(status_code=404, detail="No data found for this device")
    return documents

@app.put("/sensor/{device_id}", response_model=dict)
async def update_sensor_data(device_id: str, data: SensorData):
    update_filter = {"device_id": device_id, "timestamp": data.timestamp}
    new_values = {"$set": data.dict()}
    result = collection.update_one(update_filter, new_values)
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="No matching record to update")
    send_to_kafka('workflow-events', data.json())
    return {"message": "Data updated successfully"}

@app.delete("/sensor/{device_id}", response_model=dict)
async def delete_sensor_data(device_id: str, timestamp: Optional[str] = None):
    if timestamp:
        delete_filter = {"device_id": device_id, "timestamp": timestamp}
    else:
        delete_filter = {"device_id": device_id}
    result = collection.delete_many(delete_filter)
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No matching data found to delete")
    send_to_kafka('workflow-events', str(delete_filter))
    return {"message": f"Deleted {result.deleted_count} record(s)"}
