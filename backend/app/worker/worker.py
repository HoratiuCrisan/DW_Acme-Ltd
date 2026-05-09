"""
Worker process: consumes ingestion jobs from RabbitMQ and runs the pipeline.
Run with: python -m app.worker.consumer
"""
import json
import logging
import uuid
from datetime import datetime, timezone

import pika

from app.config import settings
from app.db.connection import get_session
from app.db.schema import apply_schema
from app.db.repositories.instrument import InstrumentRepository
from app.db.repositories.data_source import DataSourceRepository
from app.db.repositories.time_series import TimeSeriesRepository
from app.db.repositories.ingest_log import IngestLogRepository
from app.db.repositories.ingest_job import IngestJobRepository
from app.ingestion.pipeline import IngestionPipeline
from app.models.instrument import FinancialInstrument
from app.models.data_source import DataSource
from app.models.ingest_job import IngestJob

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _build_pipeline(session) -> tuple[IngestionPipeline, IngestJobRepository]:
    pipeline = IngestionPipeline(
        instrument_repo=InstrumentRepository(session),
        source_repo=DataSourceRepository(session),
        ts_repo=TimeSeriesRepository(session),
        log_repo=IngestLogRepository(session),
    )
    job_repo = IngestJobRepository(session)
    return pipeline, job_repo


def process_job(body: bytes, session) -> None:
    message = json.loads(body)
    job_id = uuid.UUID(message["job_id"])
    symbol = message["symbol"]
    datatable_code = message.get("datatable_code", "WIKI/PRICES")
    instrument_class = message.get("instrument_class", "stock")
    region = message.get("region", "US")
    currency = message.get("currency", "USD")

    pipeline, job_repo = _build_pipeline(session)

    now = datetime.now(timezone.utc)

    # Persist a running marker before ingestion so retries can observe job state.
    job_repo.save(IngestJob(
        job_id=job_id,
        symbol=symbol,
        datatable_code=datatable_code,
        status="running",
        queued_at=now,
        started_at=now,
    ))

    source = DataSource(
        source_id=uuid.uuid4(),
        source_name="NASDAQ_WIKI",
        source_type="rest",
        # Keep the stored source metadata aligned with the configured extractor URL.
        base_url=settings.nasdaq_base_url,
        api_key_required=True,
        description="Nasdaq Data Link WIKI prices",
        created_at=now,
    )
    instrument = FinancialInstrument(
        instrument_id=uuid.uuid4(),
        symbol=symbol,
        instrument_class=instrument_class,
        name=symbol,
        region=region,
        currency=currency,
        created_at=now,
    )

    try:
        result = pipeline.ingest(
            instrument=instrument,
            source=source,
            datatable_code=datatable_code,
            filters={"ticker": symbol},
        )
        status = "completed" if not result.errors else "failed"
        error_msg = "; ".join(result.errors) if result.errors else None
        record_count = result.stored
    except Exception as e:
        status = "failed"
        error_msg = str(e)
        record_count = 0

    completed_at = datetime.now(timezone.utc)
    job_repo.save(IngestJob(
        job_id=job_id,
        symbol=symbol,
        datatable_code=datatable_code,
        status=status,
        queued_at=now,
        started_at=now,
        completed_at=completed_at,
        record_count=record_count,
        error_message=error_msg,
    ))
    logger.info("Job %s for %s: %s (%d records)", job_id, symbol, status, record_count or 0)


def _connect_rabbitmq(retries: int = 10, delay: float = 3.0):
    import time
    for attempt in range(1, retries + 1):
        try:
            conn = pika.BlockingConnection(pika.URLParameters(settings.rabbitmq_url))
            logger.info("Connected to RabbitMQ on attempt %d", attempt)
            return conn
        except Exception as e:
            if attempt == retries:
                raise
            logger.warning("RabbitMQ not ready (attempt %d/%d): %s — retrying in %.0fs", attempt, retries, e, delay)
            time.sleep(delay)


def main() -> None:
    session = get_session()
    # Ensure the keyspace and tables exist before consuming jobs.
    apply_schema(session, settings.cassandra_keyspace)

    connection = _connect_rabbitmq()
    channel = connection.channel()
    channel.queue_declare(queue="ingestion_jobs", durable=True)
    channel.basic_qos(prefetch_count=1)

    def callback(ch, method, properties, body):
        try:
            process_job(body, session)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.error("Job failed: %s", e)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    channel.basic_consume(queue="ingestion_jobs", on_message_callback=callback)
    logger.info("Worker started. Waiting for jobs...")
    channel.start_consuming()


if __name__ == "__main__":
    main()
