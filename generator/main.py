import argparse
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import random
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from dotenv import load_dotenv


def parse_arguments():
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    parser = argparse.ArgumentParser(description="Send simulated measurements through the sensor API.")
    parser.add_argument("mode", choices=["historical", "live"])
    parser.add_argument("--api-url", default=os.getenv("GENERATOR_API_URL", "http://127.0.0.1:8000"),
                        help="Server address without /api; defaults to GENERATOR_API_URL or localhost:8000")
    parser.add_argument("--api-key", default=os.getenv("GENERATOR_SENSOR_API_KEY"),
                        help="Sensor key; defaults to GENERATOR_SENSOR_API_KEY")
    parser.add_argument("--count", type=int, default=15, help="Number of readings (default: 15)")
    parser.add_argument("--interval", type=float, default=60,
                        help="Seconds between historical timestamps or live submissions (default: 60)")
    parser.add_argument("--min", dest="min_value", type=float, default=0, help="Lowest value (default: 0)")
    parser.add_argument("--max", dest="max_value", type=float, default=100, help="Highest value (default: 100)")
    args = parser.parse_args()
    if not args.api_key:
        parser.error("Set GENERATOR_SENSOR_API_KEY in .env or provide --api-key")
    address = urlsplit(args.api_url)
    if address.scheme not in {"http", "https"} or not address.netloc or address.path not in {"", "/"} or address.query or address.fragment:
        parser.error("--api-url must be a server address such as http://127.0.0.1:8000, without /api")
    if args.count < 1:
        parser.error("--count must be positive")
    if not math.isfinite(args.interval) or args.interval <= 0:
        parser.error("--interval must be a positive finite number")
    if not all(math.isfinite(value) for value in (args.min_value, args.max_value, args.max_value - args.min_value)):
        parser.error("--min and --max must define a finite numeric range")
    if args.min_value > args.max_value:
        parser.error("--min must not exceed --max")
    return args


def send_measurement(api_url, api_key, value, timestamp):
    payload = json.dumps({"value": value, "timestamp": timestamp.isoformat()}).encode()
    request = Request(
        api_url.rstrip("/") + "/api/measurements",
        data=payload,
        headers={"Content-Type": "application/json", "X-API-Key": api_key},
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
        if response.status != 201:
            raise RuntimeError(f"Expected HTTP 201, received HTTP {response.status}")


def main():
    args = parse_arguments()
    start = datetime.now(timezone.utc)
    if args.mode == "historical":
        try:
            start -= timedelta(seconds=args.count * args.interval)
        except OverflowError:
            raise SystemExit("The requested historical time span is too large.") from None

    started = time.monotonic()
    saved, rejected = 0, 0
    for index in range(args.count):
        if args.mode == "live":
            time.sleep(max(0, started + index * args.interval - time.monotonic()))
            timestamp = datetime.now(timezone.utc)
        else:
            timestamp = start + timedelta(seconds=index * args.interval)
        value = random.uniform(args.min_value, args.max_value)
        try:
            send_measurement(args.api_url, args.api_key, value, timestamp)
        except HTTPError as error:
            try:
                detail = json.loads(error.read()).get("detail", error.reason)
            except (ValueError, AttributeError):
                detail = error.reason
            print(f"[{index + 1}/{args.count}] Rejected (HTTP {error.code}): {detail}", file=sys.stderr, flush=True)
            if error.code != 422:
                return 1
            rejected += 1
        except (URLError, OSError, RuntimeError) as error:
            print(f"Submission failed: {error}. Stopped without retrying; check the API before resending.", file=sys.stderr)
            return 1
        else:
            saved += 1
            print(f"[{index + 1}/{args.count}] Saved: {value:g} at {timestamp.isoformat()}", flush=True)

    print(f"Finished: {saved} saved, {rejected} rejected.")
    return 1 if rejected else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nStopped by user.", file=sys.stderr)
        sys.exit(130)
