import pika



def create_connection():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    return connection



def create_channel(connection):
    channel = connection.channel()
    return channel

def create_queue(channel,queue_name):
    channel.queue_declare(queue=queue_name, durable=True)
    return queue_name