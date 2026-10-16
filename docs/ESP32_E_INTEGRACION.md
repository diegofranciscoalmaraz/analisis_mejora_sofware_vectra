# Integración ESP32 · Guía técnica para siguiente etapa

**No se incluyó firmware funcional para hardware real**: el ZIP original no traía drivers, modelo exacto de sensores, cableado, credenciales ni una pasarela HTTPS para el ESP32. El prototipo en Python **simula las lecturas** y permite integrar esos datos cuando se disponga del hardware.

## Cadena recomendada

1. Inicializar I²C y comprobar `WHO_AM_I`/ID del MPU6050; calibrar offset y orientación de montaje.
2. Leer acelerómetro/giroscopio (registrar si contiene gravedad), GPS con validez de *fix*, temperatura y velocidad con fuente definida.
3. Asociar `device_id`, `trip_id`, `sequence` monotónica estable y tiempo UTC con sincronización confiable. Mantener datos y contador antes de transmitir.
4. Convertir a `CONTRATO_TELEMETRIA.md`: `acceleration`, `vibration`, `tilt`, `temperature`, `speed`, `gps` opcional.
5. Escribir cada mensaje original en una cola **persistente** (flash, wear leveling y límite de tamaño); enviar al gateway HTTPS validando el certificado.
6. Eliminar de cola **solo** tras `201 accepted` o `200 duplicate` con ID correspondiente.
7. Ante timeout/5xx/caída de Wi-Fi, conservar y reintentar con retroceso exponencial + jitter; ante `409/422`, separar y registrar para diagnóstico sin reintentos infinitos.
8. Supervisar pérdida de datos y memoria disponible; evitar que la cola se agote en silencio.

## Prueba del receptor sin ESP32

Primero ejecutar la API local en Ubuntu, y desde otro terminal:

```bash
export VECTRA_API_TOKEN='cambia-esto-por-un-token-largo'
python -m vectra.cli --db data/vectra.sqlite3 serve --port 8081
```

```bash
curl -i -X POST http://127.0.0.1:8081/api/v1/telemetry \
 -H "Authorization: Bearer $VECTRA_API_TOKEN" \
 -H 'Content-Type: application/json' \
 --data-binary @examples/telemetria_ejemplo.json
```

El servidor local deliberadamente **rechaza** direcciones `0.0.0.0`. No hay que cambiarlo para poner el ESP32 en la misma red: primero construir el gateway TLS y un método de autenticación individual por dispositivo.

## Datos que falta confirmar antes del firmware

Modelo exacto de GPS y temperatura, velocidad desde GPS u OBD, frecuencia de muestreo, la fórmula de vibración (p. ej. RMS/intervalo y filtrado), montaje/calibración de la IMU, duración de interrupciones esperadas, batería, control de secuencias y distribución autorizada de credenciales.
