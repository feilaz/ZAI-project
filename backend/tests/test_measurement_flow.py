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

    def test_password_change_and_logout(self):
        login_body = {"username": "admin", "password": self.password}
        token = self.request("POST", "/api/auth/login", 200, json=login_body).json()["accessToken"]
        admin = {"Authorization": f"Bearer {token}"}
        new_password = "changed-" + uuid4().hex
        change = {"currentPassword": self.password, "newPassword": new_password}

        self.request("PUT", "/api/auth/password", 401, json=change)
        self.request("PUT", "/api/auth/password", 403, headers=admin, json={**change, "currentPassword": "wrong"})
        self.request("PUT", "/api/auth/password", 422, headers=admin, json={**change, "newPassword": "short"})
        # Rejected changes must leave the original credentials usable.
        self.request("POST", "/api/auth/login", 200, json=login_body)
        changed = self.request("PUT", "/api/auth/password", 204, headers=admin, json=change)
        self.assertEqual(changed.content, b"")
        self.request("POST", "/api/auth/login", 401, json=login_body)
        new_token = self.request("POST", "/api/auth/login", 200, json={
            "username": "admin", "password": new_password,
        }).json()["accessToken"]

        self.request("POST", "/api/auth/logout", 401)
        logged_out = self.request("POST", "/api/auth/logout", 204, headers=admin)
        self.assertEqual(logged_out.content, b"")
        self.request("GET", "/api/sensors", 401, headers=admin)
        self.request("POST", "/api/auth/logout", 401, headers=admin)
        # Logout affects this session, not another independently issued token.
        self.request("GET", "/api/sensors", 200, headers={"Authorization": f"Bearer {new_token}"})

    def test_series_updates_and_sensor_and_series_deletion(self):
        token = self.request("POST", "/api/auth/login", 200, json={
            "username": "admin", "password": self.password,
        }).json()["accessToken"]
        admin = {"Authorization": f"Bearer {token}"}
        original = {"name": "PM2.5", "minValue": 0, "maxValue": 100, "color": "#123456", "icon": "circle", "unit": "µg/m³"}
        series = self.request("POST", "/api/series", 201, headers=admin, json=original).json()
        series_url = f"/api/series/{series['id']}"
        sensor_body = {"name": "Importer", "seriesId": series["id"]}
        sensor = self.request("POST", "/api/sensors", 201, headers=admin, json=sensor_body).json()
        sensor_url = f"/api/sensors/{sensor['id']}"
        key = {"X-API-Key": sensor["apiKey"]}
        measurement = self.request("POST", "/api/measurements", 201, headers=key, json={"value": 12.5}).json()
        measurement_url = f"/api/measurements/{measurement['id']}"

        self.request("PUT", series_url, 401, json=original)
        self.request("PUT", series_url, 422, headers=admin, json={**original, "maxValue": 0})
        self.request("PUT", series_url, 409, headers=admin, json={**original, "minValue": 20})
        self.assertEqual(self.request("GET", series_url, 200).json(), series)
        replacement = {"name": "Updated PM2.5", "minValue": 12.5, "maxValue": 50, "color": "#abcdef"}
        expected = {**replacement, "id": series["id"], "icon": None, "unit": None}
        self.assertEqual(self.request("PUT", series_url, 200, headers=admin, json=replacement).json(), expected)
        self.assertEqual(self.request("GET", series_url, 200).json(), expected)
        self.request("POST", "/api/measurements", 422, headers=key, json={"value": 75})
        self.request("PUT", f"/api/series/{uuid4()}", 404, headers=admin, json=replacement)

        self.request("DELETE", sensor_url, 401)
        self.assertEqual(self.request("DELETE", sensor_url, 204, headers=admin).content, b"")
        self.request("GET", sensor_url, 404, headers=admin)
        self.request("DELETE", sensor_url, 404, headers=admin)
        self.request("POST", "/api/measurements", 401, headers=key, json={"value": 25})
        retained = {field: value for field, value in measurement.items() if field != "sensorId"}
        self.assertEqual(self.request("GET", measurement_url, 200).json(), retained)

        # Deleting the series must remove both old readings and a currently registered sensor.
        sensor = self.request("POST", "/api/sensors", 201, headers=admin, json=sensor_body).json()
        key = {"X-API-Key": sensor["apiKey"]}
        newer = self.request("POST", "/api/measurements", 201, headers=key, json={"value": 25}).json()
        self.request("DELETE", series_url, 401)
        self.assertEqual(self.request("DELETE", series_url, 204, headers=admin).content, b"")
        self.request("GET", series_url, 404)
        self.request("DELETE", series_url, 404, headers=admin)
        self.request("GET", f"/api/sensors/{sensor['id']}", 404, headers=admin)
        self.request("GET", measurement_url, 404)
        self.request("GET", f"/api/measurements/{newer['id']}", 404)
        self.request("POST", "/api/measurements", 401, headers=key, json={"value": 25})
        self.assertEqual(self.request("GET", "/api/measurements", 200, params={"series": series["id"]}).json(), [])
