from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 5)  # Random wait time between requests

    @task
    def create_sensor_data(self):
        payload = {
            "device_id": "test_device_001",
            "timestamp": "2023-10-01T12:00:00Z",
            "temperature": 25.5,
            "humidity": 60.0
        }
        self.client.post("/sensor/", json=payload)

    @task
    def get_sensor_data(self):
        self.client.get("/sensor/test_device_001")

    @task
    def update_sensor_data(self):
        payload = {
            "device_id": "test_device_001",
            "timestamp": "2023-10-01T12:00:00Z",
            "temperature": 26.0,
            "humidity": 65.0
        }
        self.client.put("/sensor/test_device_001", json=payload)

    @task
    def delete_sensor_data(self):
        self.client.delete("/sensor/test_device_001")