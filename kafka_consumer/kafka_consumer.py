from kafka import KafkaConsumer
import time

consumer = KafkaConsumer(
    'workflow-events',
    bootstrap_servers='localhost:9092',
    group_id='workflow-group',
    auto_offset_reset='earliest'
)

def consume_messages():
    print("Consumer started")
    for msg in consumer:
        print(f"Consumed message: {msg.value.decode()}")
        # Simulate processing
        time.sleep(2)  # Simulate async processing time
        print(f"Processed event: {msg.value.decode()}")

if __name__ == '__main__':
    consume_messages()