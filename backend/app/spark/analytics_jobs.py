from __future__ import annotations

import argparse
from datetime import datetime, timezone
from typing import Any

from app.config import settings

CASSANDRA_FORMAT = "org.apache.spark.sql.cassandra"
TIME_SERIES_TABLE = "time_series_by_instrument"
YEARLY_TOTALS_TABLE = "yearly_totals"
REGRESSION_DATA_TABLE = "regression_data"
REGRESSION_RESULTS_TABLE = "regression_results"


def create_spark_session(app_name: str = "Acme Warehouse Analytics"):
    try:
        from pyspark.sql import SparkSession
    except ImportError as exc:  # pragma: no cover - depends on local Spark install
        raise RuntimeError(
            "pyspark is required to run Spark analytics jobs. Install project dependencies "
            "and run this module with a Spark-capable Python environment."
        ) from exc

    return (
        SparkSession.builder.appName(app_name)
        .config("spark.cassandra.connection.host", settings.cassandra_hosts)
        .config("spark.cassandra.connection.port", str(settings.cassandra_port))
        .getOrCreate()
    )


def run_yearly_total_job(
    spark,
    keyspace: str | None = None,
    source_id: str | None = None,
    output_table: str = YEARLY_TOTALS_TABLE,
) -> Any:
    from pyspark.sql import functions as F

    keyspace = keyspace or settings.cassandra_keyspace
    df = _read_cassandra_table(spark, keyspace, TIME_SERIES_TABLE)
    if source_id:
        df = df.filter(F.col("source_id") == source_id)

    result = (
        df.groupBy("instrument_id", "source_id", "record_year")
        .agg(
            F.count("*").alias("record_count"),
            F.sum("volume").cast("long").alias("total_volume"),
            F.avg(F.col("close_price").cast("double")).alias("avg_close"),
        )
        .withColumn("computed_at", F.current_timestamp())
    )
    _write_cassandra_table(result, keyspace, output_table)
    return result


def run_regression_job(
    spark,
    asset_id: str,
    source_id: str,
    keyspace: str | None = None,
    regression_data_table: str = REGRESSION_DATA_TABLE,
    regression_results_table: str = REGRESSION_RESULTS_TABLE,
) -> Any:
    from pyspark.ml.feature import Normalizer, VectorAssembler
    from pyspark.ml.regression import LinearRegression
    from pyspark.sql import functions as F

    keyspace = keyspace or settings.cassandra_keyspace
    raw = _read_cassandra_table(spark, keyspace, TIME_SERIES_TABLE)
    dataset = (
        raw.filter((F.col("instrument_id") == asset_id) & (F.col("source_id") == source_id))
        .select(
            "instrument_id",
            "source_id",
            "record_date",
            F.unix_timestamp("record_date").cast("long").alias("seconds"),
            F.col("open_price").cast("double").alias("open"),
            F.col("close_price").cast("double").alias("close"),
            F.col("low_price").cast("double").alias("low"),
            F.col("high_price").cast("double").alias("high"),
        )
        .dropna(subset=["seconds", "open", "close", "low", "high"])
    )
    _write_cassandra_table(dataset, keyspace, regression_data_table)

    assembled = VectorAssembler(
        inputCols=["seconds", "close", "low", "high"],
        outputCol="features",
    ).transform(dataset)
    normalized = Normalizer(inputCol="features", outputCol="normFeatures", p=2.0).transform(assembled)
    training, test = normalized.randomSplit([0.7, 0.3], seed=42)

    model = LinearRegression(
        labelCol="open",
        featuresCol="normFeatures",
        maxIter=10,
        regParam=1.0,
        elasticNetParam=1.0,
    ).fit(training)

    predictions = (
        model.transform(test)
        .select("instrument_id", "source_id", "record_date", "seconds", "open", "prediction")
        .withColumn("computed_at", F.lit(datetime.now(timezone.utc)))
    )
    _write_cassandra_table(predictions, keyspace, regression_results_table)
    return predictions


def _read_cassandra_table(spark, keyspace: str, table: str):
    return spark.read.format(CASSANDRA_FORMAT).options(keyspace=keyspace, table=table).load()


def _write_cassandra_table(df, keyspace: str, table: str) -> None:
    df.write.format(CASSANDRA_FORMAT).mode("append").options(keyspace=keyspace, table=table).save()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Spark analytics jobs for the data warehouse.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    totals = subparsers.add_parser("yearly-totals")
    totals.add_argument("--keyspace", default=settings.cassandra_keyspace)
    totals.add_argument("--source-id")

    regression = subparsers.add_parser("regression")
    regression.add_argument("--keyspace", default=settings.cassandra_keyspace)
    regression.add_argument("--asset-id", required=True)
    regression.add_argument("--source-id", required=True)

    args = parser.parse_args()
    spark = create_spark_session()
    try:
        if args.command == "yearly-totals":
            run_yearly_total_job(spark, keyspace=args.keyspace, source_id=args.source_id)
        elif args.command == "regression":
            run_regression_job(spark, asset_id=args.asset_id, source_id=args.source_id, keyspace=args.keyspace)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
