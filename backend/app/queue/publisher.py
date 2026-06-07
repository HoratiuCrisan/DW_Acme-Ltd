import json
import pika
from app.config import settings

def publish_ingest_job(message: dict) -> None:
    """Publish a job message to the ingestion_jobs queue"""
    connection = pika.BlockingConnection(
        pika.URLParameters(settings.rabbitmq_url)
    )

    channel = connection.channel()
    channel.queue_declare(queue="ingestion_jobs", durable=True)
    channel.basic_publish(
        exchange = "",
        routing_key = "ingestion_jobs",
        body = json.dumps(message),
        properties = pika.BasicProperties(delivery_mode = 2), # persistant
    )

    connection.close()