"""Validación del sobre de transporte; no normaliza ni consulta SQLite."""
import json
import math
import re
from datetime import datetime
from typing import Any

from .models import ValidationError

IDENTIFIER = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
MAX_MESSAGE_BYTES = 16_384


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"Campo JSON repetido: {key}")
        result[key] = value
    return result


def _reject_constant(constant: str) -> None:
    raise ValidationError(f"Constante numérica JSON no permitida: {constant}")


def decode_message(data: bytes) -> dict[str, Any]:
    """Decodifica un único objeto JSON estricto, limitado a 16 KiB."""
    if len(data) > MAX_MESSAGE_BYTES:
        raise ValidationError("Mensaje demasiado grande (máximo 16 KiB)")
    try:
        obj = json.loads(data.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys,
                         parse_constant=_reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError("JSON inválido o no codificado en UTF-8") from exc
    if not isinstance(obj, dict):
        raise ValidationError("La telemetría debe ser un objeto JSON")
    return obj


def _object(value: Any, field: str, required: set[str], optional: set[str] = frozenset()) -> dict:
    if not isinstance(value, dict):
        raise ValidationError(f"{field}: se espera un objeto")
    missing = required - value.keys()
    extra = value.keys() - required - optional
    if missing:
        raise ValidationError(f"{field}: faltan campos {', '.join(sorted(missing))}")
    if extra:
        raise ValidationError(f"{field}: campos desconocidos {', '.join(sorted(extra))}")
    return value


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{field}: se espera un número")
    try:
        number = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValidationError(f"{field}: número fuera de rango") from exc
    if not math.isfinite(number):
        raise ValidationError(f"{field}: debe ser finito")
    return number


class TelemetryValidator:
    """Confirma forma, tipos, unidades aceptadas y fecha con zona horaria."""

    def validate(self, raw: dict[str, Any]) -> dict[str, Any]:
        _object(raw, "mensaje", {"schema_version", "device_id", "trip_id", "sequence",
                                 "timestamp", "measurements"}, {"gps"})
        if type(raw["schema_version"]) is not int or raw["schema_version"] != 1:
            raise ValidationError("schema_version: se requiere versión 1")
        for field in ("device_id", "trip_id"):
            if not isinstance(raw[field], str) or not IDENTIFIER.fullmatch(raw[field]):
                raise ValidationError(f"{field}: utilice 1–64 caracteres [A-Za-z0-9_-]")
        if type(raw["sequence"]) is not int or not 0 <= raw["sequence"] <= 2_147_483_647:
            raise ValidationError("sequence: entero entre 0 y 2147483647")
        value = raw["timestamp"]
        if not isinstance(value, str):
            raise ValidationError("timestamp: se requiere ISO 8601 con zona horaria")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError("timestamp: fecha ISO 8601 inválida") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValidationError("timestamp: falta zona horaria (ej. Z o -06:00)")
        measurements = _object(raw["measurements"], "measurements",
                               {"acceleration", "vibration", "tilt", "temperature", "speed"})
        acceleration = _object(measurements["acceleration"], "acceleration", {"x", "y", "z", "unit"})
        for axis in ("x", "y", "z"):
            _number(acceleration[axis], f"acceleration.{axis}")
        self._unit(acceleration, "acceleration", {"g", "m/s2"})
        for field, units in (("vibration", {"g", "m/s2"}), ("tilt", {"deg", "rad"}),
                             ("temperature", {"C", "F"}), ("speed", {"km/h", "m/s"})):
            sensor = _object(measurements[field], field, {"value", "unit"})
            _number(sensor["value"], field)
            self._unit(sensor, field, units)
        gps = raw.get("gps", None)
        if gps is not None:
            coords = _object(gps, "gps", {"lat", "lon"})
            lat = _number(coords["lat"], "gps.lat")
            lon = _number(coords["lon"], "gps.lon")
            if not -90 <= lat <= 90 or not -180 <= lon <= 180:
                raise ValidationError("gps: latitud o longitud fuera de rango")
        return raw

    @staticmethod
    def _unit(sensor: dict, name: str, units: set[str]) -> None:
        if type(sensor["unit"]) is not str or sensor["unit"] not in units:
            raise ValidationError(f"{name}: unidad no admitida; use {', '.join(sorted(units))}")
