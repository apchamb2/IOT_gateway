"""
A gRPC server that receives sensor data from gRPC clients and stores it in MongoDB.
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import grpc, json
from concurrent import futures
from . import sensor_pb2 as sensor_pb2
from . import sensor_pb2_grpc as sensor_pb2_grpc
# MongoDB driver
from pymongo import MongoClient

# Kafka Message Sending Package
from kafka import KafkaProducer

producer = KafkaProducer(bootstrap_servers='kafka:9092')


class SensorService(sensor_pb2_grpc.SensorServiceServicer):
    """
    Implements the SensorService defined in sensor.proto.
    Receives sensor data and stores it in MongoDB.
    """
    def __init__(self):
        # Initialize MongoDB connection
        # For a local MongoDB instance: "mongodb://localhost:27017/"
        self.client = MongoClient("mongodb://mongodb:27017/")
        self.db = self.client["iot_db"]
        self.collection = self.db["sensor_data"]
        self.producer = producer
        
    def SendSensorData(self, request, context):
        """
        Receives sensor data from the client and stores it in MongoDB.
        Returns an acknowledgment to the client.
        """
        record = {
            "device_id": request.device_id,
            "timestamp": request.timestamp,
            "temperature": request.temperature,
            "humidity": request.humidity
        }

        # Insert the record into MongoDB
        insert_result = self.collection.insert_one(record)
        
        self.producer.send('workflow-events', value=f" Device ID: {request.device_id} \n \
                           Timestamp: {request.timestamp} \n \
                           Temperature: {request.temperature:.2f} °C \n \
                           Humidity: {request.humidity:.2f}%\n \
                           -------------------------------------------------------------------------------------".encode())


        # Log for demonstration
        print(f"Inserted record ID {insert_result.inserted_id} from device '{request.device_id}' into MongoDB.")
        print(f"  Timestamp: {request.timestamp}")
        print(f"  Temperature: {request.temperature:.2f} °C")
        print(f"  Humidity: {request.humidity:.2f}%\n")

        # Return acknowledgment
        return sensor_pb2.SensorAck(message="Data received and stored successfully")

def serve():
    """
    Starts the gRPC server and listens on port 50051.
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    sensor_pb2_grpc.add_SensorServiceServicer_to_server(SensorService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("gRPC server is running on port 50051...")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
