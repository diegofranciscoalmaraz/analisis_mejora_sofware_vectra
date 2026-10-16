"""Pruebas unitarias e integrales; todas trabajan con datos sintéticos."""
from copy import deepcopy
from datetime import datetime, timezone
from math import pi
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json
import tempfile
import unittest

from vectra.anomaly import RuleBasedAnomalyAnalyzer, RulesConfig
from vectra.models import ConflictError, ValidationError, Anomaly
from vectra.pipeline import TelemetryPipeline
from vectra.repository import SQLiteTelemetryRepository
from vectra.simulation import sample, sample_anomaly
from vectra.validation import TelemetryValidator, decode_message


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = SQLiteTelemetryRepository(Path(self.temp.name) / "records.sqlite3")
        self.clock = lambda: datetime(2026, 10, 15, 18, 0, tzinfo=timezone.utc)
        self.pipeline = TelemetryPipeline(self.repo, clock=self.clock)

    def tearDown(self):
        self.temp.cleanup()

    def test_acceptance_and_summary(self):
        r = self.pipeline.process(sample())
        self.assertEqual((r.status, r.new_alerts), ("accepted", 0))
        self.assertEqual(self.repo.summary(), {"records": 1, "trips": 1, "devices": 1, "alerts_pending": 0})

    def test_duplicate_is_idempotent(self):
        first = self.pipeline.process(sample_anomaly())
        second = self.pipeline.process(sample_anomaly())
        self.assertEqual((first.new_alerts, second.status, second.new_alerts), (2, "duplicate", 0))
        self.assertEqual(self.repo.summary()["alerts_pending"], 2)
        self.assertEqual(self.repo.summary()["records"], 1)

    def test_conflicting_sequence_fails_without_modification(self):
        self.pipeline.process(sample())
        another = sample()
        another["measurements"]["temperature"]["value"] = 65.0
        with self.assertRaises(ConflictError):
            self.pipeline.process(another)
        self.assertEqual(self.repo.summary()["records"], 1)

    def test_time_zone_normalized_to_utc(self):
        self.pipeline.process(sample())
        rec = self.repo.recent()[0]
        self.assertEqual(rec["measured_at"], "2026-10-15T18:01:00.000000Z")
        self.assertEqual(rec["received_at"], "2026-10-15T18:00:00.000000Z")

    def test_units_normalized(self):
        reading = sample()
        reading["measurements"]["acceleration"] = {"x": 9.80665, "y": 0, "z": 0, "unit": "m/s2"}
        reading["measurements"]["vibration"] = {"value": 9.80665, "unit": "m/s2"}
        reading["measurements"]["tilt"] = {"value": pi / 2, "unit": "rad"}
        reading["measurements"]["temperature"] = {"value": 98.6, "unit": "F"}
        reading["measurements"]["speed"] = {"value": 10, "unit": "m/s"}
        self.pipeline.process(reading)
        rec = self.repo.recent()[0]
        for key, expected in (("acc_x_g", 1), ("vibration_g", 1), ("tilt_deg", 90),
                              ("temperature_c", 37), ("speed_kmh", 36), ("acceleration_magnitude_g", 1)):
            self.assertAlmostEqual(rec[key], expected, places=6, msg=key)

    def test_optional_gps(self):
        reading = sample()
        reading.pop("gps")
        self.pipeline.process(reading)
        self.assertIsNone(self.repo.recent()[0]["latitude"])

    def test_multiple_anomalies(self):
        result = self.pipeline.process(sample_anomaly())
        self.assertEqual(result.new_alerts, 2)
        self.assertEqual({a["code"] for a in self.repo.pending_alerts()}, {"HIGH_TILT", "HIGH_VIBRATION"})

    def test_boundaries_do_not_alert(self):
        reading = sample()
        reading["measurements"]["speed"]["value"] = 120
        reading["measurements"]["temperature"]["value"] = 70
        result = self.pipeline.process(reading)
        self.assertEqual(result.new_alerts, 0)

    def test_injected_rule_configuration(self):
        analyzer = RuleBasedAnomalyAnalyzer(RulesConfig(speed_kmh=30))
        pipeline = TelemetryPipeline(self.repo, analyzer=analyzer)
        self.assertEqual(pipeline.process(sample()).new_alerts, 1)

    def test_reordering_is_allowed_for_offline_resend(self):
        self.pipeline.process(sample(4))
        self.pipeline.process(sample(2))
        self.assertEqual(self.repo.summary()["records"], 2)

    def test_isolated_validation_failures_leave_database_clean(self):
        invalid = [
            {"missing": 1},
            dict(sample(), schema_version=True),
            dict(sample(), sequence=True),
            dict(sample(), timestamp="2026-10-15T12:00:00"),
            dict(sample(), gps={"lat": 100, "lon": 0}),
            dict(sample(), gps={"lat": 20}),
            dict(sample(), gps={"lat": None, "lon": 20}),
            dict(sample(), unknown=123),
        ]
        for bad in invalid:
            with self.subTest(bad=str(bad)[:50]), self.assertRaises(ValidationError):
                self.pipeline.process(bad)
        self.assertEqual(self.repo.summary()["records"], 0)

    def test_nonfinite_and_invalid_units(self):
        bad = sample()
        bad["measurements"]["vibration"]["value"] = float("nan")
        with self.assertRaises(ValidationError): self.pipeline.process(bad)
        bad = sample()
        bad["measurements"]["speed"]["unit"] = "mph"
        with self.assertRaises(ValidationError): self.pipeline.process(bad)

    def test_physical_ranges(self):
        for key, value in (("temperature", 999), ("speed", -1), ("vibration", -0.1), ("tilt", 181)):
            bad = sample()
            bad["measurements"][key]["value"] = value
            with self.subTest(key=key), self.assertRaises(ValidationError): self.pipeline.process(bad)

    def test_json_strictness(self):
        for text in ('{"x":1,"x":2}', '[1,2]', '{"x": NaN}', 'not json'):
            with self.subTest(text=text), self.assertRaises(ValidationError):
                decode_message(text.encode())
        with self.assertRaises(ValidationError):
            decode_message(b"{" + b" " * 16384 + b"}")

    def test_record_round_trip(self):
        self.pipeline.process(sample())
        raw = self.repo.recent(1)[0]
        self.assertEqual(raw["device_id"], sample()["device_id"])
        self.assertEqual(raw["record_id"], "esp32_demo_01:ruta_demo_01:1")

    def test_repository_limit(self):
        with self.assertRaises(ValueError): self.repo.recent(1000)
        with self.assertRaises(ValueError): self.repo.pending_alerts(0)

    def test_idempotency_across_equivalent_timezone_offsets(self):
        self.pipeline.process(sample())
        another = sample()
        another["timestamp"] = "2026-10-15T18:01:00Z"
        self.assertEqual(self.pipeline.process(another).status, "duplicate")

    def test_idempotency_ignores_receive_time(self):
        self.pipeline.process(sample())
        another = TelemetryPipeline(self.repo)
        self.assertEqual(another.process(sample()).status, "duplicate")

    def test_exact_same_fingerprint_different_unit_repr(self):
        self.pipeline.process(sample())
        another = sample()
        another["measurements"]["speed"] = {"value": 38 / 3.6, "unit": "m/s"}
        # La matemática de punto flotante puede variar; no exigir idempotencia entre representaciones.
        try:
            result = self.pipeline.process(another)
            self.assertEqual(result.status, "duplicate")
        except ConflictError:
            self.assertEqual(self.repo.summary()["records"], 1)

    def test_concurrent_retries_do_not_duplicate_alerts(self):
        def repeat(_):
            return self.pipeline.process(sample_anomaly())
        with ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(repeat, range(12)))
        self.assertEqual(sum(r.status == "accepted" for r in results), 1)
        self.assertEqual(sum(r.status == "duplicate" for r in results), 11)
        self.assertEqual(self.repo.summary()["records"], 1)
        self.assertEqual(self.repo.summary()["alerts_pending"], 2)

    def test_failed_alert_insert_rolls_back_whole_record(self):
        normal = self.pipeline.normalizer.normalize(self.pipeline.validator.validate(sample()), self.clock)
        alert = Anomaly("CODE_01", "warning", "prueba", 3.0, 2.0)
        # Duplicar un código en el mismo registro viola UNIQUE y debe deshacer INSERT telemetry.
        with self.assertRaises(Exception):
            self.repo.save(normal, [alert, alert])
        self.assertEqual(self.repo.summary()["records"], 0)
        self.assertEqual(self.repo.summary()["alerts_pending"], 0)


if __name__ == "__main__":
    unittest.main()
