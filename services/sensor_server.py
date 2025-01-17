from concurrent import futures
import grpc
import sensor_pb2
import sensor_pb2_grpc

class SensorService(sensor_pb2_grpc.SensorServiceServicer):
    def __init__(self):
        self.data_store = []

    def CollectSensorData(self, request, context):
        self.data_store.append(request)
        return sensor_pb2.Response(message="Data received successfully")

    def GetSensorSummary(self, request, context):
        if not self.data_store:
            return sensor_pb2.SensorSummary(total_devices=0, avg_temperature=0.0, avg_humidity=0.0)

        total_devices = len(self.data_store)
        avg_temperature = sum(d.temperature for d in self.data_store) / total_devices
        avg_humidity = sum(d.humidity for d in self.data_store) / total_devices
        return sensor_pb2.SensorSummary(
            total_devices=total_devices,
            avg_temperature=avg_temperature,
            avg_humidity=avg_humidity
        )

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    sensor_pb2_grpc.add_SensorServiceServicer_to_server(SensorService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("gRPC Server running on port 50051")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
