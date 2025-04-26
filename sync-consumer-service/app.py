import pika
import json
from handler import handle
from vector_store import get_client
from model import get_model
from vector_store import get_collection
from vector_store import create_collection
import traceback


vstore_client = get_client()

model = get_model(model_name="sentence-transformers/all-MiniLM-L6-v2")

collection_name = "test_collection"

collection = get_collection(collection_name=collection_name,client=vstore_client)


if collection == None:
    collection = create_collection(client=vstore_client,collection_name=collection_name)
    print("collection created !!")
else:
     print("collection already exists !!")
     
connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
channel = connection.channel()

# Declare the queue
queue_name = 'product_sync'
channel.queue_declare(queue=queue_name, durable=True)

# Set prefetch count to 3 (i.e., only process 3 unacked messages at once)
channel.basic_qos(prefetch_count=1)
# Message handler
def callback(ch, method, properties, body):
    
    message = body.decode('utf-8')
    json_payload = json.loads(message)
    event = {
        "payload": json_payload,
        "event_name":"PROCESS"
    }
    context = {
        "model": model,
        "collection_name": collection_name,
        "client": vstore_client
    }

    try:
        response = handle(event=event, context=context)
        print("qdrant response",response)
    except Exception as e:
            traceback.print_exc()
     

        
        
    # Simulate some processing if needed
    # time.sleep(1)  # Optional delay
    ch.basic_ack(delivery_tag=method.delivery_tag)


# Start consuming
channel.basic_consume(queue=queue_name, on_message_callback=callback)

print('[*] Waiting for up to 3 messages at a time. To exit press CTRL+C')
channel.start_consuming()
