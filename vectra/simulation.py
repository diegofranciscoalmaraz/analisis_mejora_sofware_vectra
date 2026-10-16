"""Muestras sintéticas; no proceden de vehículos ni de sensores reales."""
from copy import deepcopy


def sample(sequence: int = 1) -> dict:
    return {
        "schema_version": 1,
        "device_id": "esp32_demo_01",
        "trip_id": "ruta_demo_01",
        "sequence": sequence,
        "timestamp": f"2026-10-15T12:{sequence % 60:02d}:00-06:00",
        "gps": {"lat": 20.5888, "lon": -100.3899},
        "measurements": {
            "acceleration": {"x": 0.10, "y": 0.01, "z": 1.00, "unit": "g"},
            "vibration": {"value": 0.25, "unit": "g"},
            "tilt": {"value": 5.0, "unit": "deg"},
            "temperature": {"value": 28.0, "unit": "C"},
            "speed": {"value": 38.0, "unit": "km/h"},
        },
    }


def sample_anomaly(sequence: int = 2) -> dict:
    payload = deepcopy(sample(sequence))
    payload["measurements"]["vibration"]["value"] = 2.8
    payload["measurements"]["tilt"]["value"] = 42
    return payload
