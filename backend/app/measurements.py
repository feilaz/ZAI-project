import logging
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.security import APIKeyHeader
from pydantic import AwareDatetime

from app.auth import hash_token
from app.database import get_connection
from app.schemas import MeasurementInput


router = APIRouter(prefix="/api/measurements", tags=["measurements"])
sensor_key = APIKeyHeader(name="X-API-Key", auto_error=False)
logger = logging.getLogger(__name__)
COLUMNS = 'id, series_id AS "seriesId", sensor_id AS "sensorId", value, measured_at AS timestamp'


@router.post("", status_code=201)
def create_measurement(body: MeasurementInput, response: Response, api_key: str | None = Depends(sensor_key)):
    if not api_key:
        raise HTTPException(401, "A valid sensor API key is required")
    if body.timestamp > datetime.now(timezone.utc) + timedelta(minutes=5):
        raise HTTPException(422, "timestamp cannot be more than five minutes in the future")
    with get_connection() as connection:
        # Keep the source and its bounds unchanged until the reading is saved.
        sensor = connection.execute(
            "SELECT s.id, s.series_id, r.min_value, r.max_value "
            "FROM sensors s JOIN series r ON r.id = s.series_id "
            "WHERE s.api_key_hash = %s FOR SHARE OF s, r", (hash_token(api_key),)
        ).fetchone()
        if sensor is None:
            raise HTTPException(401, "A valid sensor API key is required")
        if not sensor["min_value"] <= body.value <= sensor["max_value"]:
            logger.warning("Measurement rejected: value outside bounds for series %s", sensor["series_id"])
            raise HTTPException(422, "Value is outside the series range")
        measurement = connection.execute(
            "INSERT INTO measurements (id, measured_at, series_id, sensor_id, value) "
            f"VALUES (%s, %s, %s, %s, %s) RETURNING {COLUMNS}",
            (uuid4(), body.timestamp, sensor["series_id"], sensor["id"], body.value),
        ).fetchone()
    response.headers["Location"] = f"/api/measurements/{measurement['id']}"
    return measurement


@router.get("")
def list_measurements(
    series: str | None = None,
    from_time: AwareDatetime | None = Query(default=None, alias="from"),
    to_time: AwareDatetime | None = Query(default=None, alias="to"),
    sort: Literal["timestamp", "-timestamp"] = "timestamp",
    limit: int = Query(default=1000, ge=1, le=10000),
):
    conditions, parameters = [], []
    if series is not None:
        try:
            series_ids = [UUID(value.strip()) for value in series.split(",")]
        except ValueError:
            raise HTTPException(400, "series must contain comma-separated UUIDs") from None
        conditions.append("series_id = ANY(%s)")
        parameters.append(series_ids)
    if from_time is not None and to_time is not None and from_time > to_time:
        raise HTTPException(400, "from must not be after to")
    if from_time is not None:
        conditions.append("measured_at >= %s")
        parameters.append(from_time)
    if to_time is not None:
        conditions.append("measured_at <= %s")
        parameters.append(to_time)
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    direction = "DESC" if sort == "-timestamp" else "ASC"
    parameters.append(limit)
    with get_connection() as connection:
        measurements = connection.execute(
            f"SELECT {COLUMNS} FROM measurements{where} ORDER BY measured_at {direction}, id {direction} LIMIT %s",
            parameters,
        ).fetchall()
    # A deleted sensor's optional ID must be omitted rather than returned as null.
    return [{key: value for key, value in row.items() if value is not None} for row in measurements]


@router.get("/{measurementId}")
def get_measurement(measurementId: UUID):
    with get_connection() as connection:
        measurement = connection.execute(
            f"SELECT {COLUMNS} FROM measurements WHERE id = %s", (measurementId,)
        ).fetchone()
    if measurement is None:
        raise HTTPException(404, "Measurement not found")
    return {key: value for key, value in measurement.items() if value is not None}
