#VECTRA — Análisis y mejora del diseño de software

1. Descripción del proyecto

VECTRA es una propuesta de sistema de monitoreo de vehículos mediante sensores y tecnologías de comunicación. Su objetivo es recopilar información del vehículo, como aceleración, vibración, inclinación, temperatura y ubicación GPS, para facilitar el seguimiento de recorridos y la detección de posibles anomalías.

La arquitectura conceptual del proyecto se organiza en cuatro capas:

1. Sensado: obtención de mediciones del vehículo.
2. Comunicación: envío de los datos mediante un ESP32 y Wi-Fi.
3. Datos y análisis: almacenamiento, procesamiento y análisis de las mediciones.
4. Aplicación: visualización de información, gráficas, alertas e históricos.

2. Objetivo de la actividad

Analizar la organización del diseño de VECTRA e identificar oportunidades para distribuir mejor las responsabilidades de sus componentes. A partir de este análisis, se plantea una propuesta que facilite el mantenimiento, las pruebas y la incorporación de nuevas funcionalidades.

3. Propuesta version A

Esta versión propone organizar las responsabilidades mediante clases especializadas. La intención es evitar que un mismo componente tenga que encargarse de demasiadas tareas y facilitar los cambios en cada parte del sistema.

Entre las clases propuestas se encuentran:

* TelemetryRecord: representa una medición del vehículo y sus datos asociados.
* SensorManager: se encarga de obtener las mediciones de los sensores.
* TelemetryValidator: valida las mediciones recibidas.
* CommunicationGateway: gestiona el envío de las mediciones.
* TripService: organiza las mediciones por recorrido.
* TelemetryRepository: se encarga de guardar y consultar los datos.
* AnomalyDetectionService: analiza las mediciones para identificar posibles anomalías.
* AlertService: gestiona las alertas generadas por el análisis.
* DashboardService: prepara información para mostrar recorridos, resúmenes e históricos.

Importante: estas clases forman parte de una propuesta de diseño; no se presentan como clases ya implementadas en el código original.

4. Análisis del diseño

La documentación de VECTRA presenta una arquitectura conceptual dividida en cuatro capas. Sin embargo, con la información revisada no es posible confirmar problemas específicos en clases de código existentes.

Por ello, el análisis se centra en oportunidades de mejora, como definir con mayor claridad las responsabilidades de cada componente, establecer interfaces entre las capas, validar las mediciones y separar el almacenamiento del análisis de anomalías y la gestión de alertas.

5. Beneficios esperados

La propuesta busca:

* Facilitar el mantenimiento del sistema.
* Hacer más sencillas las pruebas de cada componente.
* Reducir la dependencia entre responsabilidades diferentes.
* Permitir modificar el análisis de anomalías sin cambiar directamente el almacenamiento.
* Facilitar la incorporación de nuevos sensores y funcionalidades.
* Mejorar la comprensión y organización del diseño.

Estos beneficios son esperados y deberán comprobarse al implementar y evaluar la propuesta.

6. Diagramas

El análisis contempla dos diagramas:

* Estructura original: representa las cuatro capas descritas en la documentación de VECTRA.
* Estructura propuesta: representa las clases especializadas y las relaciones planteadas para distribuir las responsabilidades.

7. Alcance y limitaciones

Esta entrega corresponde a una propuesta de mejora del diseño de software. Se basa en la arquitectura conceptual descrita en la documentación disponible y no implica que las clases propuestas ya estén implementadas.

Para confirmar problemas concretos de implementación, sería necesario revisar el código fuente de las clases originales.

8. Contribución individual

Integrante: Integrante 1
Versión: Propuesta A — Separación de responsabilidades
Rama de trabajo: feature/propuesta-A

La contribución consiste en analizar la arquitectura conceptual de VECTRA, identificar oportunidades de mejora, proponer clases con responsabilidades específicas y documentar la comparación entre la estructura original y la estructura propuesta.

El avance individual se registra en GitHub mediante la rama de trabajo y sus commits correspondientes.
