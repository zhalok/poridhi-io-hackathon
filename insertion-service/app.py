# the insertion service will be responsible for adding new data 
# it will be responsible for handling the csv parsing and sending the message in the queue
# this will be triggered by the main service after the file uploading via a queue

import csv
import sys
import json
from publisher import publish_to_mq
import uuid
from mq import create_connection_factory,create_channel,create_queue
import requests
import io
import os
import uuid

create_connection = create_connection_factory()

csv.field_size_limit(sys.maxsize)

def download_csv(url: str, local_path: str) -> None:
    """
    Downloads the content at `url` and writes it as a binary file to `local_path`.
    """
    response = requests.get(url)
    response.raise_for_status()
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    with open(local_path, 'wb') as f:
        f.write(response.content)

def process_local_csv(local_path: str, channel, queue_name: str) -> None:
    """
    Reads the CSV at `local_path`, and for each row with non-empty 'title' and
    'description', publishes a JSON payload to the given MQ channel/queue.
    """
    with open(local_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get("title", "").strip()
            desc  = row.get("description", "").strip()


            payload = {
                "id": str(uuid.uuid4()),
                "title": title,
                "description": desc
            }
            publish_to_mq(json.dumps(payload), channel, queue_name)

def download_and_process(url: str, local_path: str, channel, queue_name: str) -> None:
    """
    High-level function: fetches the CSV, saves it, then reads & publishes messages.
    """
    download_csv(url, local_path)
    # process_local_csv(local_path, channel, queue_name)

def process_csv_from_url(url, tenant_id, channel, queue_name):
  
    with requests.get(url, stream=True) as response:
        response.raise_for_status()
        if response.ok == False:
            return
        lines = response.iter_lines(decode_unicode=True)
        reader = csv.DictReader(lines)

        for row in reader:
            data = {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
               **row
            }
            publish_to_mq(json.dumps(data), channel, queue_name)

connection = create_connection()
consumer_channel = create_channel(connection)
consumer_queue = "parse_csv_queue"
create_queue(consumer_channel,consumer_queue)


def handler(event, context):
    payload = event["payload"]
    file_path = payload["file_path"]
    tenant_id = payload["tenant_id"]
    create_connection = create_connection_factory()
    producer_connection = create_connection()
    producer_channel = create_channel(connection)
    producer_queue = "product_sync"
    create_queue(producer_channel,producer_queue)



    try:
        process_csv_from_url(file_path, tenant_id, producer_channel, producer_queue)
    except Exception as e:
        print(e)
    
    producer_connection.close()
    return







print("consumer channel closed",consumer_channel.is_closed)


def callback(ch, method, properties, body):
    dict_body = json.loads(body.decode())
    print("Received message:", dict_body)

    handler(json.loads(body), None)
    consumer_channel.basic_ack(delivery_tag=method.delivery_tag)


consumer_channel.basic_consume(queue=consumer_queue, on_message_callback=callback)

print('[*] Waiting for up to 3 messages at a time. To exit press CTRL+C')
consumer_channel.start_consuming()




{

"payload":{
"file_path":"http://localhost:8001/files/amazon-products.csv"

}}