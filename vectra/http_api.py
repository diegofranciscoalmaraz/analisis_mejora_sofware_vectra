"""API local de demostración (sin TLS). No exponer directamente a internet."""
import json
import secrets
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from pathlib import Path

from .models import ConflictError, ValidationError
from .pipeline import TelemetryPipeline
from .repository import SQLiteTelemetryRepository
from .validation import MAX_MESSAGE_BYTES, decode_message


def build_server(host: str, port: int, db_path: str, token: str) -> ThreadingHTTPServer:
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("La demostración HTTP solo admite loopback; no usar en una red abierta")
    if not token or len(token) < 16:
        raise ValueError("Configure VECTRA_API_TOKEN con al menos 16 caracteres")
    repo = SQLiteTelemetryRepository(db_path)
    pipeline = TelemetryPipeline(repo)

    class Handler(BaseHTTPRequestHandler):
        server_version = "VectraDemo/1.0"

        def _json(self, status: int, data: dict) -> None:
            encoded = json.dumps(data, ensure_ascii=False, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(encoded)

        def _authenticated(self) -> bool:
            auth = self.headers.get("Authorization", "")
            if secrets.compare_digest(auth, "Bearer " + token):
                return True
            self._json(401, {"error": "Se requiere token Bearer válido"})
            return False

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path in ("/", "/dashboard"):
                # Interfaz estática: el secreto se introduce en el navegador, no se incluye en el HTML.
                document = (Path(__file__).parent / "static" / "dashboard.html").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(document)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Frame-Options", "DENY")
                self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
                self.end_headers()
                self.wfile.write(document)
            elif path == "/health":
                self._json(200, {"status": "ok", "service": "vectra-demo"})
            elif path in ("/api/v1/summary", "/api/v1/alerts", "/api/v1/recent"):
                if not self._authenticated():
                    return
                if path.endswith("summary"):
                    self._json(200, repo.summary())
                elif path.endswith("alerts"):
                    self._json(200, {"alerts": repo.pending_alerts(30)})
                else:
                    self._json(200, {"records": repo.recent(30)})
            else:
                self._json(404, {"error": "Ruta desconocida"})

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/api/v1/telemetry":
                self._json(404, {"error": "Ruta desconocida"})
                return
            if not self._authenticated():
                return
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                self._json(415, {"error": "Se requiere Content-Type: application/json"})
                return
            content_length = self.headers.get("Content-Length")
            if content_length is None or not content_length.isascii() or not content_length.isdigit():
                self._json(411, {"error": "Se requiere Content-Length válido"})
                return
            size = int(content_length)
            if size > MAX_MESSAGE_BYTES:
                self._json(413, {"error": "Cuerpo demasiado grande (16 KiB)"})
                return
            if size == 0:
                self._json(400, {"error": "JSON vacío"})
                return
            try:
                payload = decode_message(self.rfile.read(size))
                result = pipeline.process(payload)
                self._json(201 if result.status == "accepted" else 200, asdict(result))
            except ValidationError as exc:
                self._json(422, {"error": str(exc)})
            except ConflictError as exc:
                self._json(409, {"error": str(exc)})
            except Exception:
                self._json(500, {"error": "Error interno; consulte los registros del servidor"})
                return

    class SafeThreadingServer(ThreadingHTTPServer):
        daemon_threads = True
        def get_request(self):
            socket, address = super().get_request()
            socket.settimeout(10)
            return socket, address

    return SafeThreadingServer((host, port), Handler)
