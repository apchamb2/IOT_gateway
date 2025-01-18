"""
A gRPC server that receives sensor data from gRPC clients and stores it in MongoDB.
"""

import grpc
from concurrent import futures
import sensor_pb2
import sensor_pb2_grpc

# MongoDB driver
from pymongo import MongoClient

class SensorService(sensor_pb2_grpc.SensorServiceServicer):
    """
    Implements the SensorService defined in sensor.proto.
    Receives sensor data and stores it in MongoDB.
    """
    def __init__(self):
        # Initialize MongoDB connection
        # For a local MongoDB instance: "mongodb://localhost:27017/"
        self.client = MongoClient("mongodb://localhost:27017/")
        self.db = self.client["iot_db"]
        self.collection = self.db["sensor_data"]

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
