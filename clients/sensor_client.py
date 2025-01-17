import grpc
import sensor_pb2
import sensor_pb2_grpc

def run():
    with grpc.insecure_channel("localhost:50051") as channel:
        stub = sensor_pb2_grpc.SensorServiceStub(channel)

        # Send sensor data
        response = stub.CollectSensorData(sensor_pb2.SensorData(
            device_id="sensor-123",
            timestamp="2025-01-15T12:00:00Z",
            temperature=25.5,
            humidity=60.2
        ))
        print("CollectSensorData Response:", response.message)

        # Get sensor summary
        summary = stub.GetSensorSummary(sensor_pb2.Empty())
        print("GetSensorSummary Response:", summary)

if __name__ == "__main__":
    run()
