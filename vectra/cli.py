"""Uso: python -m vectra.cli {demo,ingest,summary,serve}."""
import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from .models import ConflictError, ValidationError
from .pipeline import TelemetryPipeline
from .repository import SQLiteTelemetryRepository
from .simulation import sample, sample_anomaly
from .validation import decode_message


def main() -> int:
    parser = argparse.ArgumentParser(description="VECTRA: prototipo didáctico de telemetría")
    parser.add_argument("--db", default="data/vectra.sqlite3", help="Ruta de SQLite local")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("demo", help="Procesar 2 lecturas simuladas")
    ingestion = commands.add_parser("ingest", help="Ingerir un archivo JSON")
    ingestion.add_argument("file", type=Path)
    commands.add_parser("summary", help="Mostrar resumen del repositorio")
    server = commands.add_parser("serve", help="Iniciar API HTTP SOLO en loopback")
    server.add_argument("--port", type=int, default=8081)
    args = parser.parse_args()
    if args.command == "serve":
        from .http_api import build_server
        try:
            api = build_server("127.0.0.1", args.port, args.db, os.getenv("VECTRA_API_TOKEN", ""))
        except ValueError as exc:
            parser.error(str(exc))
        print(f"API de demostración: http://127.0.0.1:{api.server_port} (solo localhost)")
        try:
            api.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            api.server_close()
        return 0
    repo = SQLiteTelemetryRepository(args.db)
    if args.command == "summary":
        result = {"summary": repo.summary(), "alerts": repo.pending_alerts()}
    else:
        pipeline = TelemetryPipeline(repo)
        try:
            if args.command == "demo":
                result = {"ingestions": [asdict(pipeline.process(m)) for m in (sample(), sample_anomaly())],
                          "summary": repo.summary(), "alerts": repo.pending_alerts()}
            else:
                result = asdict(pipeline.process(decode_message(args.file.read_bytes())))
        except (ValidationError, ConflictError) as exc:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
            return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
