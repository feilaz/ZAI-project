from fastapi import FastAPI

from app import auth, measurements, sensors, series
from app.database import get_connection
from app.errors import install_error_handlers

app = FastAPI(title="ZAI API")
install_error_handlers(app)
app.include_router(auth.router)
app.include_router(series.router)
app.include_router(sensors.router)
app.include_router(measurements.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    with get_connection() as connection:
        connection.execute("SELECT 1").fetchone()
    return {"status": "ok"}
