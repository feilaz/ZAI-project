import psycopg
from fastapi import FastAPI, HTTPException

from app.database import get_connection

app = FastAPI(title="ZAI API")


@app.get("/api/health")
def health() -> dict[str, str]:
    try:
        with get_connection() as connection:
            connection.execute("SELECT 1").fetchone()
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="Database unavailable") from None
    return {"status": "ok"}
