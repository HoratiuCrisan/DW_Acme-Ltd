from fastapi import FastAPI

from app.api import analytics, chat, consumption, data_sources, ingestion, instruments, logs, mcp, time_series

app = FastAPI(
    title="Acme Ltd Data Warehouse",
    description="Acme Ltd - Financial data warehouse API",
    version="1.0.0",
)

app.include_router(instruments.router, prefix="/instruments", tags=["instruments"])
app.include_router(data_sources.router, prefix="/sources", tags=["data-sources"])
app.include_router(time_series.router, prefix="/timeseries", tags=["time-series"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])
app.include_router(ingestion.router, prefix="/ingest", tags=["ingestion"])
app.include_router(logs.router, prefix="/logs", tags=["logs"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(mcp.router, prefix="/mcp", tags=["mcp"])
app.include_router(consumption.router, tags=["consumption"])

@app.get("/health")
def health():
    return {"status": "ok"}
