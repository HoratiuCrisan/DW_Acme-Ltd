from fastapi import FastAPI

app = FastAPI(
    title="Acme Ltd Data Warehouse",
    description="Acme Ltd - Financial data warehouse API",
    version="1.0.0",
)

@app.get("/health")
def health():
    return {"status": "ok"}