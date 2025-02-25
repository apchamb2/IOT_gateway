from openai import OpenAI

# Set your API key
openai_api_key = "....."

client = OpenAI(
    api_key=openai_api_key,  # This is the default and can be omitted
)

def generate_response(user_input):
    """
    Analyzes IoT gateway sensor data for anomalies using GPT.
    Assumes `sensor_data` is a structured JSON or string representation of network logs.
    """
    messages = [
        {"role": "system", "content": "You are an AI specializing in IoT anomaly detection and cybersecurity. Your task is to analyze network traffic, device behavior, and sensor logs to detect and explain anomalies."},
        {"role": "user", "content": f"Analyze the following sensor data and identify any anomalies. Provide explanations for detected issues:\n\n{sensor_data}"}   
    ]
    
    response = client.chat.completions.create(
        model="gpt-4-turbo",  # Use "gpt-3.5-turbo" if needed
        messages=messages,
        temperature=0.5,
        max_tokens=300,
        top_p=1.0,
        frequency_penalty=0.5,
        presence_penalty=0.3
    )

    # Correct way to extract content
    return response.choices[0].message.content

# Example Usage: Feed sample sensor data
if __name__ == "__main__":
    sample_data = """{
        "device_id": "sensor_12",
        "timestamp": "2025-02-17T12:45:00Z",
        "cpu_usage": 95.2,
        "memory_usage": 87.5,
        "network_activity": "sudden spike in outbound traffic",
        "anomalous_behavior": true
    }"""

    ai_analysis = analyze_anomaly(sample_data)
    print(ai_analysis)

"""messages = [
    {"role": "system", "content": "You are an AI specializing in IoT anomaly detection and cybersecurity."},
    {"role": "user", "content": "Device sensor_45 reported CPU usage of 15% and normal network traffic."},
    {"role": "assistant", "content": "This is normal behavior; no anomalies detected."},
    {"role": "user", "content": "Device sensor_12 reported CPU usage of 98% and a sudden outbound network spike."},
    {"role": "assistant", "content": "This behavior suggests potential malware activity or unauthorized data exfiltration. Further investigation required."}
]
"""