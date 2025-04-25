import pika

def publish_to_mq(message, channel, queue_name):
    ""
    print("queue name",queue_name)
    channel.basic_publish(
        exchange='',
        routing_key=queue_name,
        body=message,
        properties=pika.BasicProperties(
            delivery_mode=2,  # Make message persistent
        )
    )

    print(f"[x] Sent: {message}")

    # Close connection
    
