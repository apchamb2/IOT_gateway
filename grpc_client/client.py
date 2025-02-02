import grpc
import grpc_service.sensor_pb2 as sensor_pb2
import grpc_service.sensor_pb2_grpc as sensor_pb2_grpc
import random
import time
from datetime import datetime, timezone

def generate_synthetic_data():
    """
    Generate random temperature and humidity values.
    For example, temperature between 20–30 °C, humidity between 40–60%.
    """
    temperature = round(random.uniform(20.0, 30.0), 2)
    humidity = round(random.uniform(40.0, 60.0), 2)
    return temperature, humidity

def run():
    # Connect to the gRPC server
    with grpc.insecure_channel("grpc_service:50051") as channel:
        stub = sensor_pb2_grpc.SensorServiceStub(channel)

        # Simulate sending multiple sensor readings
        iterations = 30

        for i in range(iterations):
            temp, hum = generate_synthetic_data()
            current_time = datetime.now(timezone.utc).isoformat()

            # Create the SensorData message
            sensor_data = sensor_pb2.SensorData(
                device_id="sensor-001",
                timestamp=current_time,
                temperature=temp,
                humidity=hum
            )

            # Send the data to the server
            response = stub.SendSensorData(sensor_data)
            print(f"[{current_time}] Server response: {response.message}")

            # Wait a bit before sending the next reading
            time.sleep(10)

if __name__ == "__main__":
    run()
