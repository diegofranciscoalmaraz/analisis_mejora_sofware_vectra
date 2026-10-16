"""Conversiones explícitas a unidades canónicas y tiempo UTC."""
from datetime import datetime, timezone
from math import pi, sqrt
from typing import Any, Callable

from .models import TelemetryRecord, ValidationError


class TelemetryNormalizer:
    def normalize(self, raw: dict[str, Any], clock: Callable[[], datetime] | None = None) -> TelemetryRecord:
        m = raw["measurements"]
        acc = m["acceleration"]
        acc_factor = 1.0 if acc["unit"] == "g" else 1.0 / 9.80665
        x, y, z = (float(acc[axis]) * acc_factor for axis in ("x", "y", "z"))
        vib = m["vibration"]
        vibration_g = float(vib["value"]) * (1 if vib["unit"] == "g" else 1 / 9.80665)
        tilt = m["tilt"]
        tilt_deg = float(tilt["value"]) * (1 if tilt["unit"] == "deg" else 180 / pi)
        temp = m["temperature"]
        temp_c = float(temp["value"]) if temp["unit"] == "C" else (float(temp["value"]) - 32) * 5 / 9
        speed = m["speed"]
        speed_kmh = float(speed["value"]) * (1 if speed["unit"] == "km/h" else 3.6)
        # Rangos de plausibilidad del prototipo, no límites de seguridad vehicular.
        for field, value, lo, hi in (
            ("aceleración", max(abs(x), abs(y), abs(z)), 0, 50),
            ("vibración", vibration_g, 0, 50),
            ("inclinación", tilt_deg, -180, 180),
            ("temperatura", temp_c, -60, 150),
            ("velocidad", speed_kmh, 0, 350),
        ):
            if not lo <= value <= hi:
                raise ValidationError(f"{field}: valor convertido fuera del intervalo [{lo}, {hi}]")
        when = datetime.fromisoformat(raw["timestamp"].replace("Z", "+00:00"))
        measured_at = when.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
        received = (clock or (lambda: datetime.now(timezone.utc)))()
        if received.tzinfo is None or received.utcoffset() is None:
            raise ValueError("El reloj de recepción debe incluir zona horaria")
        received_at = received.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
        gps = raw.get("gps")
        return TelemetryRecord(
            record_id=f"{raw['device_id']}:{raw['trip_id']}:{raw['sequence']}",
            device_id=raw["device_id"], trip_id=raw["trip_id"], sequence=raw["sequence"],
            measured_at=measured_at, received_at=received_at,
            latitude=float(gps["lat"]) if gps is not None else None,
            longitude=float(gps["lon"]) if gps is not None else None,
            acc_x_g=x, acc_y_g=y, acc_z_g=z, vibration_g=vibration_g,
            tilt_deg=tilt_deg, temperature_c=temp_c, speed_kmh=speed_kmh,
            acceleration_magnitude_g=sqrt(x * x + y * y + z * z),
        )
