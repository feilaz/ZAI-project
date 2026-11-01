from datetime import datetime, timezone
import json
import math
import sys
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen
from zoneinfo import ZoneInfo


SOURCE_URL = "https://api.gios.gov.pl/pjp-api/v1/rest"
WARSAW = ZoneInfo("Europe/Warsaw")


def get_json(url):
    with urlopen(url, timeout=20) as response:
        return json.load(response)


def source_timestamp(value):
    timestamp = datetime.fromisoformat(value)
    if timestamp.tzinfo is None:
        first = timestamp.replace(tzinfo=WARSAW, fold=0)
        second = timestamp.replace(tzinfo=WARSAW, fold=1)
        # GIOŚ's local timestamp cannot identify an instant during a clock change.
        if first.utcoffset() != second.utcoffset():
            raise ValueError("ambiguous or nonexistent local time during a clock change")
        timestamp = first
    return timestamp.astimezone(timezone.utc)


def fetch_readings(sensor_id):
    url = f"{SOURCE_URL}/data/getData/{sensor_id}?size=500"
    first_page = get_json(url + "&page=0")
    rows = first_page["Lista danych pomiarowych"]
    for page in range(1, first_page["totalPages"]):
        rows.extend(get_json(url + f"&page={page}")["Lista danych pomiarowych"])

    readings = {}
    skipped = 0
    for row in rows:
        value = row.get("Wartość")
        if type(value) not in (int, float) or not math.isfinite(value):
            skipped += 1
            continue
        try:
            timestamp = source_timestamp(row["Data"])
        except (ValueError, TypeError):
            print(f"Skipped GIOŚ timestamp {row.get('Data')!r}: invalid or ambiguous time.", file=sys.stderr)
            skipped += 1
            continue
        if timestamp in readings and readings[timestamp] != value:
            raise ValueError("GIOŚ returned conflicting values for the same timestamp")
        readings[timestamp] = value
    print(f"GIOŚ point {sensor_id}: {len(readings)} valid readings, {skipped} missing/invalid readings skipped.", flush=True)
    return sorted(readings.items())


def import_readings(args, send_measurement):
    readings = fetch_readings(args.gios_sensor_id)[-args.count:]
    if not readings:
        raise ValueError("GIOŚ returned no usable readings for this measurement point")

    api_url = args.api_url.rstrip("/")
    series = get_json(f"{api_url}/api/series/{args.series_id}")
    print(f"Destination: {series['name']} ({args.series_id}). Source: GIOŚ, https://powietrze.gios.gov.pl/", flush=True)
    query = urlencode({
        "series": args.series_id, "from": readings[0][0].isoformat(),
        "to": readings[-1][0].isoformat(), "limit": 10000,
    })
    stored = get_json(f"{api_url}/api/measurements?{query}")
    if len(stored) == 10000:
        raise ValueError("Too many stored readings in this time window to check duplicates safely")
    existing = {}
    for row in stored:
        timestamp = datetime.fromisoformat(row["timestamp"]).astimezone(timezone.utc)
        existing.setdefault(timestamp, []).append(row["value"])

    saved, skipped, rejected = 0, 0, 0
    for timestamp, value in readings:
        if timestamp in existing:
            if value not in existing[timestamp]:
                print(f"Source value differs at {timestamp.isoformat()}: GIOŚ={value}, stored={existing[timestamp]}. Kept stored data.", file=sys.stderr)
                rejected += 1
            else:
                skipped += 1
            continue
        try:
            result = send_measurement(args.api_url, args.api_key, value, timestamp)
        except HTTPError as error:
            if error.code != 422:
                raise
            print(f"Rejected: {value:g} at {timestamp.isoformat()} (HTTP 422). Check the series bounds; value was not altered.", file=sys.stderr)
            rejected += 1
            continue
        if str(result["seriesId"]) != args.series_id:
            raise ValueError(
                f"Sensor key belongs to series {result['seriesId']}, not {args.series_id}. "
                "One reading was saved to that series; stopped. Correct the key/series pairing before continuing."
            )
        saved += 1
        print(f"Saved: {value:g} at {timestamp.isoformat()}", flush=True)
    print(f"Finished: {saved} saved, {skipped} already imported, {rejected} rejected/conflicting.", flush=True)
    return 1 if rejected else 0


def run(args, send_measurement):
    while True:
        result = import_readings(args, send_measurement)
        if result or not args.poll:
            return result
        print(f"Waiting {args.poll:g} seconds for the next source check. Ctrl+C stops.", flush=True)
        time.sleep(args.poll)
