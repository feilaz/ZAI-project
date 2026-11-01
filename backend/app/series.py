from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response

from app.auth import require_admin
from app.database import get_connection
from app.schemas import SeriesInput


router = APIRouter(prefix="/api/series", tags=["series"])
COLUMNS = 'id, name, min_value AS "minValue", max_value AS "maxValue", color, icon, unit'


@router.post("", status_code=201, dependencies=[Depends(require_admin)])
def create_series(body: SeriesInput, response: Response):
    if body.minValue >= body.maxValue:
        raise HTTPException(422, "minValue must be less than maxValue")
    with get_connection() as connection:
        series = connection.execute(
            "INSERT INTO series (id, name, min_value, max_value, color, icon, unit) "
            f"VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING {COLUMNS}",
            (uuid4(), body.name, body.minValue, body.maxValue, body.color, body.icon, body.unit),
        ).fetchone()
    response.headers["Location"] = f"/api/series/{series['id']}"
    return series


@router.put("/{seriesId}", dependencies=[Depends(require_admin)])
def update_series(seriesId: UUID, body: SeriesInput):
    if body.minValue >= body.maxValue:
        raise HTTPException(422, "minValue must be less than maxValue")
    with get_connection() as connection:
        # Prevent new readings while checking and changing the bounds.
        series = connection.execute(
            "SELECT id FROM series WHERE id = %s FOR UPDATE", (seriesId,)
        ).fetchone()
        if series is None:
            raise HTTPException(404, "Series not found")
        outside_range = connection.execute(
            "SELECT id FROM measurements WHERE series_id = %s "
            "AND (value < %s OR value > %s) LIMIT 1",
            (seriesId, body.minValue, body.maxValue),
        ).fetchone()
        if outside_range is not None:
            raise HTTPException(409, "The new range excludes existing measurements")
        series = connection.execute(
            "UPDATE series SET name = %s, min_value = %s, max_value = %s, "
            f"color = %s, icon = %s, unit = %s WHERE id = %s RETURNING {COLUMNS}",
            (body.name, body.minValue, body.maxValue, body.color, body.icon, body.unit, seriesId),
        ).fetchone()
    return series


@router.delete("/{seriesId}", status_code=204, dependencies=[Depends(require_admin)])
def delete_series(seriesId: UUID):
    with get_connection() as connection:
        deleted = connection.execute("DELETE FROM series WHERE id = %s RETURNING id", (seriesId,)).fetchone()
    if deleted is None:
        raise HTTPException(404, "Series not found")
    return Response(status_code=204)


@router.get("")
def list_series():
    with get_connection() as connection:
        return connection.execute(f"SELECT {COLUMNS} FROM series ORDER BY name, id").fetchall()


@router.get("/{seriesId}")
def get_series(seriesId: UUID):
    with get_connection() as connection:
        series = connection.execute(f"SELECT {COLUMNS} FROM series WHERE id = %s", (seriesId,)).fetchone()
    if series is None:
        raise HTTPException(404, "Series not found")
    return series
