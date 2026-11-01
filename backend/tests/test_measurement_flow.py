import os
from datetime import datetime
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from psycopg import sql

from app.database import get_connection
from app.main import app
from app.passwords import password_hasher


class MeasurementFlowTest(unittest.TestCase):
    def setUp(self):
        # Only the fixture uses SQL; the scenario below exercises the HTTP API.
        self.database = "zai_flow_test_" + uuid4().hex
        self.management = get_connection()
        self.management.autocommit = True
        self.addCleanup(self.management.close)
        self.management.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(self.database)))
        self.addCleanup(self.drop_database)
        self.enterContext(patch.dict(os.environ, {"POSTGRES_DB": self.database}))
        self.password = "test-" + uuid4().hex
        setup_sql = Path(__file__).resolve().parents[2] / "database/setup.sql"
        with get_connection() as connection:
            connection.execute(setup_sql.read_text())
            connection.execute(
                "INSERT INTO users (id, username, password_hash) VALUES (%s, %s, %s)",
                (uuid4(), "admin", password_hasher.hash(self.password)),
            )
        self.client = self.enterContext(TestClient(app))

    def drop_database(self):
        self.management.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(self.database)))

    def request(self, method, path, expected_status, **kwargs):
        response = self.client.request(method, path, **kwargs)
        self.assertEqual(response.status_code, expected_status, response.text)
        return response

    def test_administrator_registers_sensor_and_public_can_read_its_measurements(self):
        self.request("POST", "/api/auth/login", 401, json={"username": "admin", "password": "wrong"})
        login = self.request("POST", "/api/auth/login", 200, json={
            "username": "admin", "password": self.password,
        }).json()
        self.assertEqual(login["tokenType"], "Bearer")
        self.assertGreater(login["expiresIn"], 0)
        admin = {"Authorization": f"Bearer {login['accessToken']}"}

        series_data = {"name": "Warsaw PM2.5", "minValue": 0, "maxValue": 100, "color": "#123456", "unit": "µg/m³"}
        self.request("POST", "/api/series", 401, json=series_data)
        created = self.request("POST", "/api/series", 201, headers=admin, json=series_data)
        series = created.json()
        self.assertEqual(self.request("GET", created.headers["Location"], 200).json(), series)
        self.assertEqual(self.request("GET", "/api/series", 200).json(), [series])

        created = self.request("POST", "/api/sensors", 201, headers=admin, json={
            "name": "Warsaw importer", "seriesId": series["id"],
        })
        sensor = created.json()
        self.assertGreaterEqual(len(sensor["apiKey"]), 32)
        sensor_headers = {"X-API-Key": sensor["apiKey"]}
        sensor_url = created.headers["Location"]
        self.request("GET", sensor_url, 401)
        public_sensor_fields = {key: value for key, value in sensor.items() if key != "apiKey"}
        self.assertEqual(self.request("GET", sensor_url, 200, headers=admin).json(), public_sensor_fields)
        self.assertEqual(self.request("GET", "/api/sensors", 200, headers=admin).json(), [public_sensor_fields])

        # An administrator cannot submit readings; only the sensor key can.
        reading = {"value": 12.5, "timestamp": "2026-01-01T12:00:00+01:00"}
        self.request("POST", "/api/measurements", 401, headers=admin, json=reading)
        rejected = self.request("POST", "/api/measurements", 422, headers=sensor_headers, json={"value": 101})
        self.assertEqual(rejected.headers["content-type"], "application/problem+json")
        self.assertEqual(rejected.json()["status"], 422)
        self.assertEqual(self.request("GET", "/api/measurements", 200).json(), [])

        created = self.request("POST", "/api/measurements", 201, headers=sensor_headers, json=reading)
        measurement = created.json()
        self.assertEqual(datetime.fromisoformat(measurement["timestamp"]), datetime.fromisoformat(reading["timestamp"]))
        expected = {
            "id": measurement["id"], "seriesId": series["id"], "sensorId": sensor["id"],
            "value": 12.5, "timestamp": measurement["timestamp"],
        }
        self.assertEqual(measurement, expected)
        measurement_url = created.headers["Location"]
        later = self.request("POST", "/api/measurements", 201, headers=sensor_headers, json={
            "value": 25, "timestamp": "2026-01-01T12:00:00Z",
        }).json()

        # A fresh anonymous client must see persisted readings, including inclusive boundaries.
        with TestClient(app) as reader:
            response = reader.get(measurement_url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), expected)
            response = reader.get("/api/measurements", params={
                "series": series["id"], "from": expected["timestamp"], "to": expected["timestamp"],
            })
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), [expected])
            self.assertEqual(reader.get("/api/measurements", params={"series": str(uuid4())}).json(), [])
            self.assertEqual(reader.get("/api/measurements").json(), [expected, later])
            self.assertEqual(reader.get("/api/measurements", params={"sort": "-timestamp", "limit": 1}).json(), [later])
