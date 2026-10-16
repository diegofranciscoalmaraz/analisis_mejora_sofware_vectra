"""Contratos internos inmutables entre las etapas del pipeline."""
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class TelemetryRecord:
    record_id: str
    device_id: str
    trip_id: str
    sequence: int
    measured_at: str
    received_at: str
    latitude: float | None
    longitude: float | None
    acc_x_g: float
    acc_y_g: float
    acc_z_g: float
    vibration_g: float
    tilt_deg: float
    temperature_c: float
    speed_kmh: float
    acceleration_magnitude_g: float = 0.0


@dataclass(frozen=True, slots=True)
class Anomaly:
    code: str
    severity: Literal["warning", "critical"]
    message: str
    value: float
    threshold: float


@dataclass(frozen=True, slots=True)
class IngestResult:
    record_id: str
    status: Literal["accepted", "duplicate"]
    new_alerts: int


class ValidationError(ValueError):
    """Lectura incompatible con el contrato de telemetría v1."""


class ConflictError(ValueError):
    """Mismo ID lógico con contenido diferente."""
