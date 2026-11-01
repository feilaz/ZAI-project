import secrets
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response

from app.auth import hash_token, require_admin
from app.database import get_connection
from app.schemas import SensorInput


router = APIRouter(prefix="/api/sensors", tags=["sensors"], dependencies=[Depends(require_admin)])
COLUMNS = 'id, name, series_id AS "seriesId", created_at AS "createdAt"'


@router.post("", status_code=201)
def create_sensor(body: SensorInput, response: Response):
    api_key = secrets.token_urlsafe(32)
    with get_connection() as connection:
        series = connection.execute(
            "SELECT id FROM series WHERE id = %s FOR KEY SHARE", (body.seriesId,)
        ).fetchone()
        if series is None:
            raise HTTPException(422, "Series not found")
        sensor = connection.execute(
            "INSERT INTO sensors (id, series_id, name, api_key_hash) "
            f"VALUES (%s, %s, %s, %s) RETURNING {COLUMNS}",
            (uuid4(), body.seriesId, body.name, hash_token(api_key)),
        ).fetchone()
    response.headers["Location"] = f"/api/sensors/{sensor['id']}"
    return {**sensor, "apiKey": api_key}


@router.get("")
def list_sensors():
    with get_connection() as connection:
        return connection.execute(f"SELECT {COLUMNS} FROM sensors ORDER BY created_at, id").fetchall()


@router.get("/{sensorId}")
def get_sensor(sensorId: UUID):
    with get_connection() as connection:
        sensor = connection.execute(f"SELECT {COLUMNS} FROM sensors WHERE id = %s", (sensorId,)).fetchone()
    if sensor is None:
        raise HTTPException(404, "Sensor not found")
    return sensor
