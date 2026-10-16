"""Orquestador liviano con dependencias inyectables."""
from typing import Any, Callable
from datetime import datetime

from .validation import TelemetryValidator
from .normalization import TelemetryNormalizer
from .anomaly import RuleBasedAnomalyAnalyzer
from .models import IngestResult
from .repository import SQLiteTelemetryRepository


class TelemetryPipeline:
    def __init__(self, repository: SQLiteTelemetryRepository,
                 validator: TelemetryValidator | None = None,
                 normalizer: TelemetryNormalizer | None = None,
                 analyzer: RuleBasedAnomalyAnalyzer | None = None,
                 clock: Callable[[], datetime] | None = None):
        self.repository = repository
        self.validator = validator or TelemetryValidator()
        self.normalizer = normalizer or TelemetryNormalizer()
        self.analyzer = analyzer or RuleBasedAnomalyAnalyzer()
        self.clock = clock

    def process(self, payload: dict[str, Any]) -> IngestResult:
        validated = self.validator.validate(payload)
        normalized = self.normalizer.normalize(validated, clock=self.clock)
        anomalies = self.analyzer.analyze(normalized)
        return self.repository.save(normalized, anomalies)
