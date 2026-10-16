# Contrato de telemetría v1

`POST /api/v1/telemetry` — JSON UTF-8 con `Content-Type: application/json` y `Authorization: Bearer <TOKEN>` para el servidor local de demostración. Tamaño máximo **16 KiB**. Se rechazan claves duplicadas, valores no finitos, claves desconocidas y números escritos como texto.

## Ejemplo aceptado

```json
{
  "schema_version": 1,
  "device_id": "esp32_demo_01",
  "trip_id": "ruta_demo_01",
  "sequence": 1,
  "timestamp": "2026-10-15T12:01:00-06:00",
  "gps": {"lat": 20.5888, "lon": -100.3899},
  "measurements": {
    "acceleration": {"x": 0.1, "y": 0.01, "z": 1.0, "unit": "g"},
    "vibration": {"value": 0.25, "unit": "g"},
    "tilt": {"value": 5.0, "unit": "deg"},
    "temperature": {"value": 28.0, "unit": "C"},
    "speed": {"value": 38.0, "unit": "km/h"}
  }
}
```

## Semántica de campos

| Campo | Requisito | Validación / canonicalización |
|---|---|---|
| `schema_version` | obligatorio, entero literal | solo `1` |
| `device_id` / `trip_id` | obligatorio | `[A-Za-z0-9_-]` 1–64 caracteres |
| `sequence` | obligatorio, entero literal | 0–2147483647; estable tras reintentos |
| `timestamp` | obligatorio | ISO 8601 con UTC `Z` o zona explícita; normalizado a UTC |
| `gps` | opcional | `null` o `{lat,lon}` completos; límites geográficos |
| `acceleration` | obligatorio | ejes `x,y,z`, unidad `g` o `m/s2` → `g` |
| `vibration` | obligatorio | `g` o `m/s2` → `g` |
| `tilt` | obligatorio | `deg` o `rad` → grados |
| `temperature` | obligatorio | `C` o `F` → grados Celsius |
| `speed` | obligatorio | `km/h` o `m/s` → km/h |

Rangos de plausibilidad del **prototipo**: |aceleración por eje| ≤ 50 g; vibración entre 0 y 50 g; inclinación entre −180 y 180°; temperatura entre −60 y 150°C; velocidad entre 0 y 350 km/h. No son umbrales de seguridad ni especificaciones del MPU6050 o del sensor final.

Reglas ilustrativas de alertas: aceleración por eje > 3 g, vibración > 2 g, inclinación |ángulo| > 35°, temperatura > 70°C y velocidad > 120 km/h. Sin histéresis, filtros ni periodos de amortiguación: **no apropiadas para avisos de seguridad vial**.

## Respuestas

```json
{"record_id":"esp32_demo_01:ruta_demo_01:1","status":"accepted","new_alerts":0}
```

`201` para nueva, `200` para reintento idéntico, `409` para misma identidad con contenido distinto, `422` para error de estructura/semántica, `401` sin token, `413` para exceso de tamaño y `415` para tipo incorrecto.

**Idempotencia:** SHA-256 de la representación normalizada (sin `received_at`). Mediciones distintas con el mismo ID se rechazan en lugar de sobrescribirse. Conversiones matemáticamente equivalentes pueden producir pequeñas diferencias de coma flotante, por lo que el ESP32 debe **reenviar el mismo JSON exacto** en cada intento y mantener los números/precisión.

**Almacenamiento de alertas:** `pending` quiere decir **pendiente de entrega**. No hay correo, SMS, dashboard conectado ni push en esta demostración.
