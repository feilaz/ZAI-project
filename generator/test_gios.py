from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
from io import StringIO
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import gios


class GiosImportTest(unittest.TestCase):
    def test_source_times_and_missing_readings(self):
        pages = [
            {"totalPages": 2, "Lista danych pomiarowych": [
                {"Data": "2026-11-01 12:00:00", "Wartość": 0},
                {"Data": "2026-11-01 13:00:00", "Wartość": None},
                {"Data": "2026-10-25 02:30:00", "Wartość": 15},
            ]},
            {"Lista danych pomiarowych": [
                {"Data": "2026-07-01 12:00:00", "Wartość": 12.5},
                {"Data": "2026-03-29 02:30:00", "Wartość": 20},
            ]},
        ]
        with patch.object(gios, "get_json", side_effect=pages) as fetch, redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            readings = gios.fetch_readings(3731)
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(readings, [
            (datetime(2026, 7, 1, 10, tzinfo=timezone.utc), 12.5),
            (datetime(2026, 11, 1, 11, tzinfo=timezone.utc), 0),
        ])

    def test_repeated_import_skips_saved_data_and_reports_source_corrections(self):
        args = SimpleNamespace(api_url="http://example.test", api_key="test-key", series_id="series-1", gios_sensor_id=3731, count=15)
        timestamp = datetime(2026, 11, 1, 11, tzinfo=timezone.utc)
        stored = []

        def get_json(url):
            if "/api/series/" in url:
                return {"name": "GIOŚ PM2.5"}
            return stored

        def send(api_url, api_key, value, time):
            stored.append({"timestamp": time.isoformat(), "value": value})
            return {"seriesId": args.series_id}

        with patch.object(gios, "get_json", side_effect=get_json), patch.object(gios, "fetch_readings", return_value=[(timestamp, 12.5)]) as source, redirect_stdout(StringIO()), redirect_stderr(StringIO()) as errors:
            self.assertEqual(gios.import_readings(args, send), 0)
            self.assertEqual(gios.import_readings(args, send), 0)
            self.assertEqual(len(stored), 1)
            source.return_value = [(timestamp, 14.0)]
            self.assertEqual(gios.import_readings(args, send), 1)
            self.assertEqual(stored, [{"timestamp": timestamp.isoformat(), "value": 12.5}])
            self.assertIn("Source value differs", errors.getvalue())
