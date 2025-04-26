import pika

def create_connection_factory():
    connection = None

    def create_connection():
        nonlocal connection
        if connection is not None:
            return connection

        connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
        return connection
    
    return create_connection


def create_channel(connection):
    channel = connection.channel()
    return channel

def create_queue(channel,queue_name):
    channel.queue_declare(queue=queue_name, durable=True)
    return queue_name