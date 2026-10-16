"""Pruebas de HTTP en localhost, sin dependencias de red externas."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from vectra.http_api import build_server
from vectra.simulation import sample


class HttpTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.token = "token_de_pruebas_super_seguro"
        self.server = build_server("127.0.0.1", 0, str(Path(self.temp.name) / "test.db"), self.token)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, method, path, payload=None, authorized=True, content_type="application/json"):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        headers = {"Content-Type": content_type}
        if authorized:
            headers["Authorization"] = "Bearer " + self.token
        body = json.dumps(payload).encode() if payload is not None else None
        conn.request(method, path, body, headers=headers)
        r = conn.getresponse()
        result = r.status, json.loads(r.read().decode())
        conn.close()
        return result

    def test_authorization_and_ingest(self):
        self.assertEqual(self.request("GET", "/health", authorized=False)[0], 200)
        self.assertEqual(self.request("GET", "/api/v1/summary", authorized=False)[0], 401)
        self.assertEqual(self.request("POST", "/api/v1/telemetry", sample(), authorized=False)[0], 401)
        status, result = self.request("POST", "/api/v1/telemetry", sample())
        self.assertEqual((status, result["status"]), (201, "accepted"))
        self.assertEqual(self.request("POST", "/api/v1/telemetry", sample())[0], 200)
        self.assertEqual(self.request("GET", "/api/v1/summary")[1]["records"], 1)

    def test_invalid_and_conflicting(self):
        self.assertEqual(self.request("POST", "/api/v1/telemetry", {"foo": 2})[0], 422)
        self.assertEqual(self.request("POST", "/api/v1/telemetry", sample(), content_type="text/plain")[0], 415)
        self.request("POST", "/api/v1/telemetry", sample())
        other = sample()
        other["measurements"]["speed"]["value"] = 40
        self.assertEqual(self.request("POST", "/api/v1/telemetry", other)[0], 409)

    def test_forbidden_public_bind(self):
        with self.assertRaises(ValueError):
            build_server("0.0.0.0", 0, str(Path(self.temp.name) / "x.db"), self.token)

    def test_dashboard_static_and_no_token_disclosed(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        conn.request("GET", "/")
        result = conn.getresponse()
        self.assertEqual(result.status, 200)
        self.assertIn("Content-Security-Policy", result.headers)
        html = result.read().decode("utf-8")
        self.assertIn("VECTRA", html)
        self.assertNotIn(self.token, html)
        conn.close()

    def test_payload_size_limit(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        conn.request("POST", "/api/v1/telemetry", body=b"x" * 17000, headers={
            "Content-Type": "application/json", "Authorization": "Bearer " + self.token})
        r = conn.getresponse()
        self.assertEqual(r.status, 413)
        r.read()
        conn.close()


if __name__ == "__main__":
    unittest.main()
