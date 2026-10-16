# Auditoría técnica y plan de mejora — VECTRA

**Alcance del material recibido:** dos notebooks (`01_...A.ipynb` y `03_...C.ipynb`), README y `.gitignore`. No se recibió firmware ESP32, fuente del backend original ni dashboard operativo. Por tanto, las observaciones del diseño original son **riesgos documentales y arquitectónicos**, no fallos de producción demostrados.

## Hallazgos y acciones

| ID | Prioridad | Hallazgo en el archivo original | Mejora aplicada | Estado / verificación |
|---|---|---|---|---|
| H01 | Alta | No había implementación evaluable de C | Prototipo estándar Python 3.11+ en `vectra/` | Implementado; pruebas automáticas |
| H02 | Alta | Sin contrato de mensajes ni unidades | Contrato JSON v1 explícito y conversión de unidades | Implementado; pruebas de conversión |
| H03 | Alta | Sin esquema de idempotencia | ID `device_id:trip_id:sequence`, SHA-256 semántico y respuesta a duplicados/conflictos | Implementado; pruebas de reintentos |
| H04 | Alta | Alertas y persistencia sin semántica transaccional | Detección antes de guardar; persistencia de telemetría + alertas en una transacción SQLite | Implementado en demo; pruebas de integración |
| H05 | Alta | Contratos no cubrían payloads inválidos | Validación profunda de claves, tipos, rangos, GPS, zona horaria, unidades y JSON | Implementado; pruebas negativas |
| H06 | Alta | No había seguridad de entrada documentada | API HTTP solo loopback, token Bearer local, tamaño máximo 16 KiB, errores controlados | Prototipo local; **no apto para internet** |
| H07 | Media | No se distinguían problemas reales de hipótesis | Sección de evidencia, limitaciones y trazabilidad en notebook renovado | Documentado |
| H08 | Media | Los diagramas no estaban disponibles como imágenes visibles | DOT + SVG + PNG para visión original, pipeline y secuencia | Archivos generados |
| H09 | Media | Faltaban pruebas reproducibles | `unittest` para validación, conversiones, duplicados, alertas y HTTP | Ejecutables y verificadas localmente |
| H10 | Media | Faltaba guía de ESP32 y fallos de conectividad | Contrato + guía de reintentos y propuesta de cola persistente | Especificado, **no implementado en hardware** |
| H11 | Media | `README` centrado casi exclusivamente en A | README general, guía de instalación, estructura y limitaciones | Actualizado |
| H12 | Baja | Notebook C incluía celda vacía y comparaba B sin evidencia | Reconstrucción del notebook C; A intacta; B declarada no revisada | Actualizado |
| H13 | Media | No había interfaz para ver resultados del prototipo | Dashboard HTML local con métricas, tendencias sintéticas y tabla de alertas | Implementado sobre API local |

## Puntos pendientes explícitos

1. Integración y calibración real de MPU6050, GPS y sensor de temperatura en ESP32.
2. Pruebas de campo: vibración real vs gravedad, inclinación del soporte, ruido, latencia y consumo eléctrico.
3. Conexión segura: HTTPS con certificados validados o canal privado, credenciales por dispositivo y rotación.
4. Cola persistente en ESP32 con límites y confirmación de recepción (reintentos con retroceso exponencial y jitter).
5. Rechazo o anotación de relojes desincronizados y política de datos antiguos/futuros.
6. Autorización por dispositivo, tasas de mensajes, auditoría de acceso, cifrado en reposo y retención/borrado de GPS.
7. Canal de entrega de alertas con estado, reintento y trazabilidad; ahora solo se almacenan **pendientes**.
8. Migraciones SQL, monitorización/observabilidad y despliegue productivo.
9. Umbrales calibrados con datos reales y evaluación de falsos positivos/negativos.

## Criterios de aceptación verificables

- JSON inválido, incompleto o ambiguo ⇒ rechazo sin persistir.
- Una lectura correcta ⇒ un registro; reenvío idéntico ⇒ no duplica datos ni alertas.
- Reenvío con misma identidad y datos distintos ⇒ conflicto explícito; no sobrescritura.
- Temperatura °F, velocidad m/s, aceleración m/s² e inclinación rad ⇒ unidades canónicas.
- Alerta y lectura ⇒ se guardan juntas en SQLite si se acepta el evento.
- Cambios de umbrales no requieren reescribir la persistencia.
- API solo escucha localhost y exige token para datos sensibles.

## Interpretación del resultado

Las pruebas comprueban **comportamientos del prototipo** bajo entradas sintéticas. No confirman que la arquitectura mejore la latencia, el costo, la exactitud de detección, la seguridad operacional o la fiabilidad de VECTRA en un vehículo real. Esas propiedades requieren instrumentación y ensayos posteriores.
