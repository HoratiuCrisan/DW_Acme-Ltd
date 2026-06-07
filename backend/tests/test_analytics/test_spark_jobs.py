import importlib

from app.db.schema import SCHEMA_STATEMENTS


def test_spark_jobs_module_imports_without_local_spark():
    module = importlib.import_module("app.spark.analytics_jobs")

    assert module.TIME_SERIES_TABLE == "time_series_by_instrument"
    assert module.YEARLY_TOTALS_TABLE == "yearly_totals"
    assert module.REGRESSION_DATA_TABLE == "regression_data"
    assert module.REGRESSION_RESULTS_TABLE == "regression_results"


def test_schema_contains_spark_output_tables():
    schema = "\n".join(SCHEMA_STATEMENTS)

    assert "CREATE TABLE IF NOT EXISTS yearly_totals" in schema
    assert "CREATE TABLE IF NOT EXISTS regression_data" in schema
    assert "CREATE TABLE IF NOT EXISTS regression_results" in schema
