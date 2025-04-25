import pika
from mq import create_connection, create_channel, create_queue 
def publish_to_mq(message):
    ""
    connection = create_connection()
    producer_channel = create_channel(connection)
    queue_name = "parse_csv_queue"
    create_queue(producer_channel,queue_name)

    print("queue name",)
    producer_channel.basic_publish(
        exchange='',
        routing_key=queue_name,
        body=message,
        properties=pika.BasicProperties(
            delivery_mode=2,  # Make message persistent
        )
    )

    

    print(f"[x] Sent: {message}")
    connection.close()

    # Close connection
    
