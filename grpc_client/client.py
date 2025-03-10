import sys
import os
import grpc

# Append parent directory to the system path to import grpc_service modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))) 

from grpc_service import sensor_pb2
from grpc_service import sensor_pb2_grpc
import random
import time
import json  # For converting sensor data to JSON format
from datetime import datetime, timezone
from openai import OpenAI  # Import the OpenAI API client




# =============================================================================
# OpenAI API Configuration
# =============================================================================

openai_api_key = ""
client_gpt = OpenAI(api_key=openai_api_key)

# Define the expected sensor ranges for temperature and humidity.
# These thresholds will be used to detect anomalies.
THRESHOLDS = {
    "temperature": {"min": 15.0, "max": 45.0},  # Expected temperature range: 15–45 °C
    "humidity": {"min": 20.0, "max": 80.0}         # Expected humidity range: 20–80%
}

# =============================================================================
# Anomaly Detection and GPT Explanation Functions
# =============================================================================
def detect_anomaly(sensor_data):
    """
    Check sensor readings against defined thresholds.
    If a reading is outside the expected range or missing (-999), record it as an anomaly.
    Returns a dictionary of anomalies if any are found, otherwise returns None.
    """
    anomalies = {}

    if not (THRESHOLDS["temperature"]["min"] <= sensor_data["temperature"] <= THRESHOLDS["temperature"]["max"]):
        anomalies["temperature"] = sensor_data["temperature"]

    if not (THRESHOLDS["humidity"]["min"] <= sensor_data["humidity"] <= THRESHOLDS["humidity"]["max"]):
        anomalies["humidity"] = sensor_data["humidity"]

    if sensor_data["temperature"] == -999 or sensor_data["humidity"] == -999:
        anomalies["sensor_failure"] = "Missing sensor readings detected"

    return anomalies if anomalies else None

def get_gpt_explanation(sensor_data):
    """
    Build a conversation for the GPT model that includes:
      - A system message instructing the AI to analyze IoT sensor data for anomalies.
      - A user message containing the sensor data in JSON format.
    Calls the OpenAI chat completion API and returns the explanation.
    """
    messages = [
        {
            "role": "system",
            "content": "You are an AI specializing in IoT anomaly detection. Analyze the given sensor data, detect possible anomalies, and explain any unusual patterns. Note that the expected range for temperature is 15-45 °C and humidity range: 20–80%"
        },
        {
            "role": "user",
            "content": f"Sensor data: {json.dumps(sensor_data, indent=2)}\n\nIdentify any issues and explain what might be causing them."
        }
    ]
    
    response = client_gpt.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.5,
        max_tokens=300
    )
    return response.choices[0].message.content

# =============================================================================
# Synthetic Sensor Data Generation
# =============================================================================
def generate_synthetic_data():
    """
    Generate random temperature and humidity values.
    Occasionally, introduce an anomaly:
      - A temperature spike,
      - A humidity drop,
      - Or simulate a sensor failure.
    """
    temperature = round(random.uniform(20.0, 30.0), 2)
    humidity = round(random.uniform(40.0, 60.0), 2)

    # Introduce an anomaly with 10% probability
    if random.random() < 0.1:
        anomaly_type = random.choice(["temperature_spike", "humidity_drop", "sensor_failure"])
        
        if anomaly_type == "temperature_spike":
            temperature = round(random.uniform(50.0, 80.0), 2)  # Abnormally high temperature
        elif anomaly_type == "humidity_drop":
            humidity = round(random.uniform(5.0, 15.0), 2)  # Abnormally low humidity
        elif anomaly_type == "sensor_failure":
            temperature = None  # Simulate missing sensor data
            humidity = None

    return temperature, humidity

# =============================================================================
# Main Execution Loop: Data Generation, Anomaly Detection, and gRPC Transmission
# =============================================================================
def run():
    """
    Continuously generate synthetic sensor data, check for anomalies, and send data to the gRPC server.
    If an anomaly is detected, also request an explanation from the GPT model.
    """
    # Create a gRPC channel to communicate with the sensor service.
    channel = grpc.insecure_channel('grpc-service:50051')
    stub = sensor_pb2_grpc.SensorServiceStub(channel)

    iterations = 100  # Number of sensor readings to simulate

    # for if in range(iterations):
    while True:
    # temp, hum = generate_synthetic_data()
        temp, hum = generate_synthetic_data()
        current_time = datetime.now(timezone.utc).isoformat()

        # Prepare sensor data as a dictionary for anomaly detection.
        sensor_data_dict = {
            "temperature": temp if temp is not None else -999,
            "humidity": hum if hum is not None else -999
        }

        # Check if the sensor data has any anomalies.
        anomalies = detect_anomaly(sensor_data_dict)
        if anomalies:
            print("🚨 Anomaly detected! Requesting GPT explanation...")
            explanation = get_gpt_explanation(sensor_data_dict)
            print(f"🤖 GPT Explanation:\n{explanation}")
        else:
            print("✅ No anomalies detected.")

        # Create the SensorData message to send to the gRPC server.
        sensor_data = sensor_pb2.SensorData(
            device_id="sensor-001",
            timestamp=current_time,
            temperature=temp if temp is not None else -999,  # Use -999 for missing values
            humidity=hum if hum is not None else -999
        )

        # Send the sensor data to the gRPC server.
        response = stub.SendSensorData(sensor_data)
        print(f"📡 [{current_time}] Sent Data: Temp: {temp}, Hum: {hum} | Server Response: {response.message}")

        # Wait for 10 seconds before sending the next reading.
        time.sleep(10)

if __name__ == "__main__":
    run()