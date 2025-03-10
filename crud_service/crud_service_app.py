# import os
# import traceback
# from contextlib import asynccontextmanager
# import cProfile
# import pstats
# from io import StringIO

# from fastapi import FastAPI, HTTPException, Request
# from pydantic import BaseModel, Field
# from typing import Optional
# from pymongo import MongoClient
# from kafka import KafkaProducer
# from kafka.errors import KafkaError
# # from prometheus_client import Counter, Histogram, Summary

# # Prometheus instrumentation
# from prometheus_fastapi_instrumentator import Instrumentator
# from prometheus_client import (
#     CollectorRegistry,
#     Counter,
#     Gauge,
#     Histogram,
#     Summary,
#     generate_latest,
# )

# # Environment Variables
# MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
# KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")

# # Lifecycle Management
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     print("=== LIFESPAN STARTUP ===")
#     yield
#     print("=== LIFESPAN SHUTDOWN ===")

# # Create the FastAPI app
# app = FastAPI(lifespan=lifespan)

# # ----------------- PROMETHEUS CUSTOM METRICS -----------------------
# # Register custom metrics
# registry = CollectorRegistry(auto_describe=True)

# # Define global metrics for HTTP requests
# REQUEST_COUNT = Counter(
#     "http_requests_total", "Total number of HTTP requests", ["method", "endpoint"]
# )

# REQUEST_LATENCY = Histogram(
#     "http_request_duration_seconds", "Request latency in seconds", ["method", "endpoint"]
# )

# ACTIVE_REQUESTS = Gauge(
#     "http_active_requests", "Number of active HTTP requests"
# )

# # Track Kafka message production
# kafka_messages_sent_total = Counter(
#     "kafka_messages_sent_total",
#     "Number of messages successfully sent to Kafka",
# )

# # Track database query latency
# db_query_latency_seconds = Histogram(
#     "db_query_duration_seconds",
#     "MongoDB query duration in seconds",
#     ["operation"],
# )

# # Track request size
# http_request_size_bytes = Summary(
#     "http_request_size_bytes",
#     "Content length of incoming requests",
# )





# # Middleware for Prometheus Metrics
# @app.middleware("http")
# async def prometheus_middleware(request: Request, call_next):
#     method = request.method
#     endpoint = request.url.path

#     # Increment active requests gauge
#     ACTIVE_REQUESTS.inc()

#     # Track request size
#     if request.headers.get("Content-Length"):
#         http_request_size_bytes.observe(int(request.headers["Content-Length"]))
    

#     # Measure request latency
#     with REQUEST_LATENCY.labels(method=method, endpoint=endpoint).time():
#         response = await call_next(request)

#     # Decrement active requests gauge
#     ACTIVE_REQUESTS.dec()

#     # Increment request count
#     REQUEST_COUNT.labels(method=method, endpoint=endpoint).inc()

#     return response

# # Standard Prometheus Instrumentation
# Instrumentator().instrument(app).expose(
#     app,
#     include_in_schema=True,
#     endpoint="/metrics",
# )





# # ----------------- KAFKA + MONGODB SETUP -----------------------
# producer = KafkaProducer(
#     bootstrap_servers=KAFKA_BROKER,
#     value_serializer=lambda v: v.encode("utf-8"),
# )

# client = MongoClient(MONGO_URI)
# db = client["iot_db"]
# collection = db["sensor_data"]

# def send_to_kafka(topic: str, message: str):
#     try:
#         future = producer.send(topic, value=message)
#         record_metadata = future.get(timeout=10)
#         kafka_messages_sent_total.inc()  # Increment Kafka metric
#         print(
#             f"Message sent to topic: {record_metadata.topic}, "
#             f"partition: {record_metadata.partition}, offset: {record_metadata.offset}"
#         )
#     except KafkaError as e:
#         print(f"Failed to send message to Kafka due to KafkaError: {e}")
#     except Exception as e:
#         print(f"Unexpected error while sending to Kafka: {e}")

# # ----------------- DATA MODEL -----------------------
# class SensorData(BaseModel):
#     device_id: str = Field(..., description="Unique device identifier")
#     timestamp: str = Field(..., description="Timestamp in ISO format")
#     temperature: float = Field(..., description="Temperature reading")
#     humidity: float = Field(..., description="Humidity reading")

# # ----------------- CRUD ENDPOINTS -----------------------
# @app.post("/sensor/", response_model=dict)
# async def create_sensor_data(data: SensorData):
#     # Start profiling
#     pr = cProfile.Profile()
#     pr.enable()

#     sensor_dict = data.dict()

#     # Track Kafka message production
#     send_to_kafka("workflow-events", data.json())

#     # Track database insert operation
#     with db_query_latency_seconds.labels(operation="insert").time():
#         result = collection.insert_one(sensor_dict)

#     # Stop profiling
#     pr.disable()
#     s = StringIO()
#     ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
#     ps.print_stats()
#     print(s.getvalue())  # Print profiling results to logs

#     if result.inserted_id:
#         return {"message": "Data inserted successfully", "id": str(result.inserted_id)}
#     raise HTTPException(status_code=500, detail="Error inserting data")

# @app.get("/sensor/{device_id}", response_model=list)
# async def get_sensor_data(device_id: str):
#     # Track database find operation
#     with db_query_latency_seconds.labels(operation="find").time():
#         documents = list(collection.find({"device_id": device_id}, {"_id": 0}))

#     if not documents:
#         raise HTTPException(status_code=404, detail="No data found for this device")
#     return documents

# @app.put("/sensor/{device_id}", response_model=dict)
# async def update_sensor_data(device_id: str, data: SensorData):
#     update_filter = {"device_id": device_id, "timestamp": data.timestamp}
#     new_values = {"$set": data.dict()}

#     # Track database update operation
#     with db_query_latency_seconds.labels(operation="update").time():
#         result = collection.update_one(update_filter, new_values)

#     if result.matched_count == 0:
#         raise HTTPException(status_code=404, detail="No matching record to update")

#     # Track Kafka message production
#     send_to_kafka("workflow-events", data.json())
#     return {"message": "Data updated successfully"}

# @app.delete("/sensor/{device_id}", response_model=dict)
# async def delete_sensor_data(device_id: str, timestamp: Optional[str] = None):
#     delete_filter = {"device_id": device_id} if not timestamp else {"device_id": device_id, "timestamp": timestamp}

#     # Track database delete operation
#     with db_query_latency_seconds.labels(operation="delete").time():
#         result = collection.delete_many(delete_filter)

#     if result.deleted_count == 0:
#         raise HTTPException(status_code=404, detail="No matching data found to delete")

#     # Track Kafka message production
#     send_to_kafka("workflow-events", str(delete_filter))
#     return {"message": f"Deleted {result.deleted_count} record(s)"}

# # Middleware for Error Logging
# @app.middleware("http")
# async def kafka_error_middleware(request: Request, call_next):
#     try:
#         response = await call_next(request)
#         return response
#     except Exception as exc:
#         error_details = {
#             "path": request.url.path,
#             "method": request.method,
#             "error": str(exc),
#             "traceback": traceback.format_exc(),
#         }

#         # Log errors to Kafka
#         send_to_kafka("error-events", str(error_details))
#         raise

# # ----------------- RUN THE APP -----------------------
# if __name__ == "__main__":
#     import uvicorn

#     uvicorn.run(
#         "crud_service_app:app",
#         host="0.0.0.0",  # Allow external access inside Docker
#         port=8000,
#         reload=True,
#     )



# import os
# import traceback
# from contextlib import asynccontextmanager
import cProfile
import pstats
from io import StringIO

import os
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional
from pymongo import MongoClient
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError

# Prometheus instrumentation
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import (
    Counter,
    Histogram,
    Summary,
    Gauge,
    generate_latest,
)

# Environment Variables
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")

# Lifecycle Management
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=== LIFESPAN STARTUP ===")
    yield
    print("=== LIFESPAN SHUTDOWN ===")

# Create the FastAPI app
app = FastAPI(lifespan=lifespan)

# ----------------- PROMETHEUS CUSTOM METRICS -----------------------
# Define global metrics for HTTP requests
REQUEST_COUNT = Counter(
    "http_requests_total", "Total number of HTTP requests", ["method", "endpoint"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "Request latency in seconds", ["method", "endpoint"]
)

ACTIVE_REQUESTS = Gauge(
    "http_active_requests", "Number of active HTTP requests"
)

# Track Kafka message production
kafka_messages_sent_total = Counter(
    "kafka_messages_sent_total",
    "Number of messages successfully sent to Kafka",
)

kafka_consumer_lag = Gauge(
    "kafka_consumer_lag",
    "Kafka consumer lag (difference between last offset and current position)",
    ["topic"]
)

# Track database query latency
db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "MongoDB query duration in seconds",
    ["operation"],
)

# Track request size
http_request_size_bytes = Summary(
    "http_request_size_bytes",
    "Content length of incoming requests",
)

# Middleware for Prometheus Metrics
@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    method = request.method
    endpoint = request.url.path

    # Increment active requests gauge
    ACTIVE_REQUESTS.inc()

    # Track request size
    if request.headers.get("Content-Length"):
        http_request_size_bytes.observe(int(request.headers["Content-Length"]))

    # Measure request latency
    with REQUEST_LATENCY.labels(method=method, endpoint=endpoint).time():
        response = await call_next(request)

    # Decrement active requests gauge
    ACTIVE_REQUESTS.dec()

    # Increment request count
    REQUEST_COUNT.labels(method=method, endpoint=endpoint).inc()

    return response

# Standard Prometheus Instrumentation
Instrumentator().instrument(app).expose(app, include_in_schema=True, endpoint="/metrics")

# ----------------- KAFKA + MONGODB SETUP -----------------------
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: v.encode("utf-8"),
)

consumer = KafkaConsumer(
    bootstrap_servers=KAFKA_BROKER,
    group_id="prometheus-group",
    auto_offset_reset="earliest",
    enable_auto_commit=False
)

client = MongoClient(MONGO_URI)
db = client["iot_db"]
collection = db["sensor_data"]

def send_to_kafka(topic: str, message: str):
    try:
        future = producer.send(topic, value=message)
        record_metadata = future.get(timeout=10)
        kafka_messages_sent_total.inc()  # Increment Kafka metric
        print(f"Message sent to topic: {record_metadata.topic}, partition: {record_metadata.partition}, offset: {record_metadata.offset}")
    except KafkaError as e:
        print(f"Failed to send message to Kafka due to KafkaError: {e}")
    except Exception as e:
        print(f"Unexpected error while sending to Kafka: {e}")

def track_kafka_consumer_lag(topic: str):
    """Track Kafka consumer lag for a given topic."""
    partitions = consumer.partitions_for_topic(topic)
    if not partitions:
        print(f"No partitions found for topic: {topic}")
        return

    total_lag = 0
    for partition in partitions:
        tp = f"{topic}-{partition}"
        end_offset = consumer.end_offsets([tp])[tp]
        current_position = consumer.position(tp)
        lag = max(0, end_offset - current_position)
        total_lag += lag

    kafka_consumer_lag.labels(topic=topic).set(total_lag)
    print(f"Kafka consumer lag for topic {topic}: {total_lag}")

# Schedule Kafka lag tracking periodically
import asyncio
async def periodic_kafka_lag_tracking(interval: int = 10):
    while True:
        track_kafka_consumer_lag("workflow-events")
        await asyncio.sleep(interval)

# Start Kafka lag tracking in the background
import threading
threading.Thread(target=lambda: asyncio.run(periodic_kafka_lag_tracking()), daemon=True).start()

# ----------------- DATA MODEL -----------------------
class SensorData(BaseModel):
    device_id: str = Field(..., description="Unique device identifier")
    timestamp: str = Field(..., description="Timestamp in ISO format")
    temperature: float = Field(..., description="Temperature reading")
    humidity: float = Field(..., description="Humidity reading")

# ----------------- CRUD ENDPOINTS -----------------------
@app.post("/sensor/", response_model=dict)
async def create_sensor_data(data: SensorData):
    sensor_dict = data.dict()

    # Track Kafka message production
    send_to_kafka("workflow-events", data.json())

    # Track database insert operation
    with db_query_duration_seconds.labels(operation="insert").time():
        result = collection.insert_one(sensor_dict)

    if result.inserted_id:
        return {"message": "Data inserted successfully", "id": str(result.inserted_id)}
    raise HTTPException(status_code=500, detail="Error inserting data")

@app.get("/sensor/{device_id}", response_model=list)
async def get_sensor_data(device_id: str):
    # Track database find operation
    with db_query_duration_seconds.labels(operation="find").time():
        documents = list(collection.find({"device_id": device_id}, {"_id": 0}))

    if not documents:
        raise HTTPException(status_code=404, detail="No data found for this device")
    return documents

@app.put("/sensor/{device_id}", response_model=dict)
async def update_sensor_data(device_id: str, data: SensorData):
    update_filter = {"device_id": device_id, "timestamp": data.timestamp}
    new_values = {"$set": data.dict()}

    # Track database update operation
    with db_query_duration_seconds.labels(operation="update").time():
        result = collection.update_one(update_filter, new_values)

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="No matching record to update")

    # Track Kafka message production
    send_to_kafka("workflow-events", data.json())
    return {"message": "Data updated successfully"}

@app.delete("/sensor/{device_id}", response_model=dict)
async def delete_sensor_data(device_id: str, timestamp: Optional[str] = None):
    delete_filter = {"device_id": device_id} if not timestamp else {"device_id": device_id, "timestamp": timestamp}

    # Track database delete operation
    with db_query_duration_seconds.labels(operation="delete").time():
        result = collection.delete_many(delete_filter)

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No matching data found to delete")

    # Track Kafka message production
    send_to_kafka("workflow-events", str(delete_filter))
    return {"message": f"Deleted {result.deleted_count} record(s)"}

# Middleware for Error Logging
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
        }

        # Log errors to Kafka
        send_to_kafka("error-events", str(error_details))
        raise

# ----------------- RUN THE APP -----------------------
if __name__ == "__main__":
    import uvicorn

    # Start the FastAPI application
    uvicorn.run(
        "crud_service_app:app",
        host="0.0.0.0",  # Allow external access inside Docker
        port=8000,
        reload=True,
    )