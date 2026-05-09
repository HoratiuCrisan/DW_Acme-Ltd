from uuid import UUID
from typing import Iterable
from cassandra.cluster import Session

from app.db.repositories.base import CassandraRepository, WarehouseRepository
from app.models.ingest_job import IngestJob


class IngestJobRepository(CassandraRepository, WarehouseRepository[IngestJob, UUID]):
    def __init__(self, session: Session):
        super().__init__(session)
        self._insert = session.prepare(
            """
            INSERT INTO ingest_jobs
              (job_id, symbol, datatable_code, status, queued_at,
               started_at, completed_at, record_count, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        )
        self._select = session.prepare(
            "SELECT * FROM ingest_jobs WHERE job_id = ?"
        )

    def save(self, job: IngestJob) -> IngestJob:
        self._execute(self._insert, [
            job.job_id, job.symbol, job.datatable_code, job.status,
            job.queued_at, job.started_at, job.completed_at,
            job.record_count, job.error_message,
        ])
        return job

    def delete(self, key: UUID) -> None:
        # Job rows are immutable audit records.
        raise NotImplementedError("Ingest jobs are append-only")

    def delete_all(self, partition_key: UUID) -> None:
        # Job history should be retained for operational debugging.
        raise NotImplementedError("Ingest jobs are append-only")

    def find_latest(self, partition_key: UUID) -> IngestJob | None:
        row = self._fetch_one(self._select, [partition_key])
        if row is None:
            return None
        return IngestJob(
            job_id=row.job_id,
            symbol=row.symbol,
            datatable_code=row.datatable_code,
            status=row.status,
            queued_at=row.queued_at,
            started_at=getattr(row, "started_at", None),
            completed_at=getattr(row, "completed_at", None),
            record_count=getattr(row, "record_count", None),
            error_message=getattr(row, "error_message", None),
        )

    def find_all(self, partition_key: UUID) -> Iterable[IngestJob]:
        # A job_id maps to a single row, so this keeps the repository contract intact.
        job = self.find_latest(partition_key)
        return [job] if job is not None else []

    def find(self, job_id: UUID) -> IngestJob | None:
        return self.find_latest(job_id)
