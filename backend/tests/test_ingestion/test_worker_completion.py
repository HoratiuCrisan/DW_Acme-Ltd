import uuid
from unittest.mock import MagicMock

from app.worker import worker


def test_completion_analytics_runs_yearly_totals(monkeypatch):
    source_id = uuid.uuid4()
    spark = MagicMock()
    create_spark_session = MagicMock(return_value=spark)
    run_yearly_total_job = MagicMock()

    monkeypatch.setattr(worker.settings, "run_yearly_totals_on_ingest", True)
    monkeypatch.setattr("app.spark.analytics_jobs.create_spark_session", create_spark_session)
    monkeypatch.setattr("app.spark.analytics_jobs.run_yearly_total_job", run_yearly_total_job)

    worker.run_completion_analytics(source_id)

    create_spark_session.assert_called_once_with(app_name="Acme Warehouse Yearly Totals Trigger")
    run_yearly_total_job.assert_called_once_with(spark, source_id=str(source_id))
    spark.stop.assert_called_once()


def test_completion_analytics_can_be_disabled(monkeypatch):
    create_spark_session = MagicMock()

    monkeypatch.setattr(worker.settings, "run_yearly_totals_on_ingest", False)
    monkeypatch.setattr("app.spark.analytics_jobs.create_spark_session", create_spark_session)

    worker.run_completion_analytics(uuid.uuid4())

    create_spark_session.assert_not_called()
