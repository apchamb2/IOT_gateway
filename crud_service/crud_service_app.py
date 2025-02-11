"""
a FastAPI app that demonstrates create, read, update, and delete (CRUD) operations. 
It’s “time-decoupled” because the CRUD service persists data to the MongoDB database 
independently of when the sensor data arrives.
http://localhost:8000/docs or http://127.0.0.1:8000/docs
http://127.0.0.1:8000/metrics
"""
"""
CRUD FastAPI service with Prometheus instrumentation using lifespan.
"""

import os, traceback
from contextlib import asynccontextmanager
import cProfile, pstats
from io import StringIO

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional
from pymongo import MongoClient
from kafka import KafkaProducer
from kafka.errors import KafkaError

# Prometheus instrumentation
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import CollectorRegistry, Counter, REGISTRY


MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/")
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # If you have other startup/shutdown logic, keep it here
    print("=== LIFESPAN STARTUP ===")
    yield
    print("=== LIFESPAN SHUTDOWN ===")

# Create the FastAPI app (with a lifespan if needed)
app = FastAPI(lifespan=lifespan)

# ----------------- PROMETHEUS INSTRUMENTATION -----------------------
# Instrument the app BEFORE it starts, so we can add middleware safely
Instrumentator().instrument(app).expose(
    app,
    include_in_schema=True,
    endpoint="/metrics",
)

# --------------- KAFKA + MONGODB SETUP ---------------
producer = KafkaProducer(
    bootstrap_servers='kafka:9092',
    value_serializer=lambda v: v.encode('utf-8')
)

# Avoid duplicated metric on reload
def get_kafka_messages_sent_metric():
    for collector in list(REGISTRY._collector_to_names.keys()):
        names = REGISTRY._collector_to_names[collector]
        if "kafka_messages_sent_total" in names:
            return collector
    return Counter(
        "kafka_messages_sent_total",
        "Number of messages successfully sent to Kafka"
    )

kafka_messages_sent = get_kafka_messages_sent_metric()

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

# ----------------- DATA MODEL + MIDDLEWARE -----------------------
class SensorData(BaseModel):
    device_id: str = Field(..., description="Unique device identifier")
    timestamp: str = Field(..., description="Timestamp in ISO format")
    temperature: float = Field(..., description="Temperature reading")
    humidity: float = Field(..., description="Humidity reading")

@app.middleware("http")
async def kafka_error_middleware(request: Request, call_next):
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

# ----------------- CRUD ENDPOINTS -----------------------
# @app.post("/sensor/", response_model=dict)
# async def create_sensor_data(data: SensorData):
#     sensor_dict = data.dict()
#     send_to_kafka('workflow-events', data.json())
#     result = collection.insert_one(sensor_dict)
#     if result.inserted_id:
#         return {"message": "Data inserted successfully", "id": str(result.inserted_id)}
#     raise HTTPException(status_code=500, detail="Error inserting data")

@app.post("/sensor/", response_model=dict)
async def create_sensor_data(data: SensorData):
    # Start profiling
    pr = cProfile.Profile()
    pr.enable()

    sensor_dict = data.dict()
    send_to_kafka('workflow-events', data.json())
    result = collection.insert_one(sensor_dict)

    # Stop profiling
    pr.disable()
    s = StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats()
    print(s.getvalue())  # Print profiling results to logs

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "crud_service_app:app",
        host="0.0.0.0", # Changed from 127.0.0.1 to allow external access inside Docker
        port=8000,
        reload=True,  # for dev auto-reload
    )
