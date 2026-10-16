"""Reglas demostrativas sustituibles; no equivalen a un detector ML calibrado."""
from dataclasses import dataclass
from .models import Anomaly, TelemetryRecord


@dataclass(frozen=True, slots=True)
class RulesConfig:
    acceleration_axis_g: float = 3.0
    vibration_g: float = 2.0
    tilt_degrees: float = 35.0
    temperature_c: float = 70.0
    speed_kmh: float = 120.0


class RuleBasedAnomalyAnalyzer:
    def __init__(self, config: RulesConfig | None = None):
        self.config = config or RulesConfig()

    def analyze(self, data: TelemetryRecord) -> list[Anomaly]:
        rules = (
            ("HIGH_ACCELERATION", "critical", "Aceleración elevada", max(abs(data.acc_x_g), abs(data.acc_y_g), abs(data.acc_z_g)), self.config.acceleration_axis_g),
            ("HIGH_VIBRATION", "warning", "Vibración elevada", data.vibration_g, self.config.vibration_g),
            ("HIGH_TILT", "warning", "Inclinación elevada", abs(data.tilt_deg), self.config.tilt_degrees),
            ("HIGH_TEMPERATURE", "critical", "Temperatura elevada", data.temperature_c, self.config.temperature_c),
            ("HIGH_SPEED", "warning", "Velocidad elevada", data.speed_kmh, self.config.speed_kmh),
        )
        return [Anomaly(code, severity, message, value, limit)
                for code, severity, message, value, limit in rules if value > limit]
