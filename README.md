# DW_Acme-Ltd

Financial data warehouse project for Acme Ltd. The system ingests market data from Nasdaq Data Link, stores historical time-series data in Cassandra, exposes REST APIs for consumers, runs analytics jobs with Spark, and provides an MCP endpoint for AI-agent access.

## Architecture

```text
Nasdaq Data Link
      |
      v
FastAPI ingestion endpoint ----> RabbitMQ queue ----> Worker
      |                                                |
      |                                                v
      |                                      Ingestion pipeline
      |                                                |
      v                                                v
REST / MCP / Chat APIs <---------------------- Cassandra keyspace
      |                                                |
      |                                                v
      +-------------------------------------- Spark analytics jobs
                                                       |
                                                       v
                                      yearly_totals / regression_results
```

## Main Components

- `FastAPI`: REST endpoints for ingestion, consumption, analytics, logs, chat, and MCP.
- `RabbitMQ`: durable queue for ingestion jobs.
- `Worker`: consumes queued jobs, fetches Nasdaq data, writes warehouse records, and triggers yearly Spark totals after successful ingestion.
- `Cassandra`: warehouse storage for metadata, time-series facts, ingestion audit, analytics output, portfolio data, and LLM logs.
- `Spark`: batch analytics layer for yearly aggregates and regression datasets/results.
- `MCP`: JSON-RPC endpoint exposing warehouse tools for agentic AI consumers.

## Cassandra Tables

Core metadata:

- `financial_instruments`
- `instrument_versions`
- `instruments_by_class`
- `data_sources`
- `exchanges`

Fact data:

- `time_series_by_instrument`

Ingestion and audit:

- `ingest_jobs`
- `ingest_log`

Analytics and ML:

- `analytics_results`
- `yearly_totals`
- `regression_data`
- `regression_results`
- `risk_signals`

Consumer and LLM layer:

- `users`
- `owners`
- `portfolios_by_owner`
- `portfolio_assets`
- `recommendations`
- `llm_query_log`

## Operational Procedures

### Start Infrastructure

From the repository root:

```bash
docker compose up -d cassandra rabbitmq
```

Check services:

```bash
docker ps
```

RabbitMQ management UI is available at:

```text
http://localhost:15672
```

Default credentials:

```text
guest / guest
```

### Start API Locally

From `backend`:

```bash
venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

API docs:

```text
http://localhost:8000/docs
```

### Start Worker Locally

From `backend`:

```bash
venv\Scripts\python.exe -m app.worker.worker
```

The worker consumes RabbitMQ messages from `ingestion_jobs`.

### Run Full Docker Stack

From the repository root:

```bash
docker compose up --build
```

The Docker API is exposed on:

```text
http://localhost:8080
```

### Ingest Real Nasdaq Data

Queue ingestion:

```http
POST http://localhost:8000/ingest
Content-Type: application/json

{
  "symbols": ["AAPL", "MSFT", "GOOG", "AMZN", "NFLX"],
  "datatable_code": "WIKI/PRICES"
}
```

Check job status:

```http
GET http://localhost:8000/ingest/status/{job_id}
```

Successful jobs return `status: completed` and a positive `record_count`.

### Spark Yearly Totals Trigger

After a worker completes an ingestion job with stored records, it calls:

```text
run_yearly_total_job()
```

The job reads `time_series_by_instrument` and appends yearly aggregates into `yearly_totals`.

The trigger is controlled by:

```text
RUN_YEARLY_TOTALS_ON_INGEST=true
```

If Spark is unavailable, the worker logs a warning but keeps the completed ingestion job intact.

Manual Spark run:

```bash
venv\Scripts\python.exe -m app.spark.analytics_jobs yearly-totals
```

Run for one source:

```bash
venv\Scripts\python.exe -m app.spark.analytics_jobs yearly-totals --source-id {source_id}
```

### Consumption APIs

List assets:

```http
GET http://localhost:8000/assets?offset=0&limit=20
```

List data sources:

```http
GET http://localhost:8000/data-sources?offset=0&limit=20
```

List valid asset/source pairs that have time-series rows:

```http
GET http://localhost:8000/data-pairs?offset=0&limit=20
```

Read time-series data:

```http
GET http://localhost:8000/data?assetId={asset_id}&dataSourceId={source_id}&startBusinessDate=2016-12-01&endBusinessDate=2017-01-01&includeAttributes=true&limit=5
```

Run aggregate analytics:

```http
GET http://localhost:8000/analytics/{asset_id}/{source_id}?start_date=2016-12-01&end_date=2018-01-01
```

### MCP API

List MCP tools:

```http
POST http://localhost:8000/mcp
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list"
}
```

Call a warehouse tool:

```http
POST http://localhost:8000/mcp
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "get_time_series_data",
    "arguments": {
      "assetId": "{asset_id}",
      "dataSourceId": "{source_id}",
      "startBusinessDate": "2016-12-01",
      "endBusinessDate": "2017-01-01",
      "includeAttributes": true,
      "limit": 5
    }
  }
}
```

### Inspect Cassandra

Open `cqlsh`:

```bash
docker exec -it cassandra cqlsh
```

Inspect keyspace:

```sql
USE financial_dw;
DESCRIBE TABLES;
DESCRIBE TABLE time_series_by_instrument;
DESCRIBE TABLE yearly_totals;
```

Sample time-series query:

```sql
SELECT record_date, system_date, open_price, close_price, volume
FROM time_series_by_instrument
WHERE instrument_id = {asset_id}
AND source_id = {source_id}
LIMIT 10;
```

## Tests

From `backend`:

```bash
venv\Scripts\pytest.exe -q
```
