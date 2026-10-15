# Ficha del Proyecto — Brújula Soporte IT · Service Desk SLA Analytics

> Fuente única de verdad del proyecto. Se completa paso a paso durante la Fase 0.
> Estado: ✅ **APROBADA** el 2026-10-15. Fase 0 cerrada. Siguiente: Fase 0.5 (entorno).

**Requisitos de la fuente interna fijados por el estudiante:** la tabla de hechos tiene que contener
tickets en **distintos estados**, con **distintos tiempos de resolución**, **distintas prioridades**
y **distintos departamentos**.

## 0. País y contexto  ← se llena PRIMERO

| Campo | Valor |
|---|---|
| **País** | España |
| **Código ISO-2** | ES |
| **Moneda** | € EUR (formato `1.234,56 €`) |
| **Mercado al que apunta** | España y otros países (remoto / internacional). Proyecto en español; README con resumen en inglés (Fase 5) |
| **Geografía del modelo** | Comunidades autónomas / provincias *(se define en el Paso 1, según dónde estén clientes y sedes)* |
| **Idioma del proyecto** | Español (código, comentarios y documentación) |

**Implicaciones del país para el resto del proyecto:**

- **Moneda:** el EUR es la moneda base del BCE, así que el tipo de cambio (Frankfurter) se expresaría
  como EUR→USD. Esto solo es útil si la empresa compra licencias o servicios en dólares.
- **Calendario:** en España hay festivos nacionales, autonómicos y locales. Nager.Date devuelve los
  autonómicos con el código de la comunidad (`ES-MD`, `ES-CT`…), por lo que la geografía y el
  calendario quedan ligados.
- **Fuentes nacionales candidatas (Nivel 2):** INE, Eurostat, BCE. Se evalúan en el Paso 3.

### 0.1 Reglas del reloj de SLA (decididas)

| Prioridad | Calendario del reloj |
|---|---|
| **P1 — Crítica** | 24x7: el reloj no se detiene nunca |
| **P2 a P4** | Horario laboral: lunes a viernes, 09:00–18:00, excluyendo festivos |

- **Festivos que detienen el reloj:** los de la **sede de soporte, en Madrid** (nacionales + Comunidad
  de Madrid + locales de Madrid capital).
- **Ejemplo de control:** un P2 abierto el viernes a las 17:30, con el lunes festivo → el martes a las
  10:00 lleva **1 h 30 min** consumidas (30 min del viernes + 1 h del martes).

### 0.2 Catálogo del service desk (decidido)

**Tipos de ticket** — cada uno con su propio SLA; las incidencias son las más exigentes:

| Tipo | Qué es | Prioridades posibles |
|---|---|---|
| **Incidencia** | Algo que funcionaba y dejó de funcionar (caída, error, degradación) | P1–P4 |
| **Petición** | El cliente solicita algo estándar (alta de usuario, acceso, cambio de configuración) | P2–P4 |
| **Tarea** | Trabajo planificado o interno derivado de otro ticket (despliegue, revisión, mantenimiento) | P2–P4 |

> P1 solo existe para incidencias: una petición o una tarea nunca es "servicio caído".

**Matriz de SLA** (1 día laborable = 9 h, L–V 09:00–18:00; P1 corre 24x7):

| Tipo | Prioridad | 1ª respuesta | Resolución | Reloj |
|---|---|---|---|---|
| Incidencia | P1 Crítica | 15 min | 4 h | 24x7 |
| Incidencia | P2 Alta | 30 min | 8 h lab. | Laboral |
| Incidencia | P3 Media | 2 h | 2 días lab. (18 h) | Laboral |
| Incidencia | P4 Baja | 4 h | 4 días lab. (36 h) | Laboral |
| Petición | P2 Alta | 2 h | 2 días lab. (18 h) | Laboral |
| Petición | P3 Media | 4 h | 4 días lab. (36 h) | Laboral |
| Petición | P4 Baja | 8 h | 8 días lab. (72 h) | Laboral |
| Tarea | P2 Alta | 4 h | 3 días lab. (27 h) | Laboral |
| Tarea | P3 Media | 8 h | 6 días lab. (54 h) | Laboral |
| Tarea | P4 Baja | 1 día lab. (9 h) | 10 días lab. (90 h) | Laboral |

*(Propuesta aceptada en estructura; los tiempos concretos quedan abiertos a ajuste antes de la Fase 1.)*

**Estados** (flujo tipo Jira Service Management):

```
Abierto → En curso ⇄ Esperando al cliente → Resuelto → Cerrado
   └──────────────┴──────────────→ Cancelado
```

- **Esperando al cliente pausa el reloj** de resolución.
- **Cancelado** no computa en el % de cumplimiento (se reporta aparte).
- La tabla de hechos contendrá tickets **en todos los estados**, incluidos abiertos al corte (backlog).

**Departamentos (grupos resolutores):**

| Departamento | Rol |
|---|---|
| Service Desk N1 | Recepción, triaje y resolución de primer nivel |
| Soporte Aplicaciones N2 | Errores funcionales de las aplicaciones del cliente |
| Infraestructura | Servidores, red, cloud, caídas de servicio |
| Desarrollo | Bugs que requieren cambio de código |
| Seguridad | Accesos, vulnerabilidades, incidentes de seguridad |

### 0.3 Clientes y contratos (decidido: niveles + bonus/malus sobre la facturación)

Los clientes son **empresas** con un contrato de soporte y una **cuota mensual**. Cada mes se mide el
cumplimiento del SLA de resolución del cliente y, según el tramo en que caiga, la factura de ese mes
**se descuenta (malus)** o **se bonifica (bonus)** en un porcentaje de la cuota.

| Nivel | Nº clientes | Cuota mensual | Objetivo contractual |
|---|---|---|---|
| **Gold** | 8 | 25.000–40.000 € | ≥ 95 % |
| **Silver** | 14 | 8.000–20.000 € | ≥ 90 % |
| **Bronze** | 18 | 2.000–6.000 € | ≥ 85 % |

**Tramos de ajuste sobre la factura mensual** *(propuesta, ajustable antes de la Fase 1)*:

| Nivel | Bonus | Neutro | Malus leve | Malus medio | Malus máximo |
|---|---|---|---|---|---|
| **Gold** | ≥ 98 % → **+3 %** | 95–98 % → 0 % | 92–95 % → −5 % | 88–92 % → −10 % | < 88 % → **−15 %** |
| **Silver** | ≥ 95 % → **+2 %** | 90–95 % → 0 % | 85–90 % → −5 % | — | < 85 % → **−10 %** |
| **Bronze** | ≥ 92 % → **+1 %** | < 92 % → 0 % | — | — | **Sin malus** (decidido) |

- **Qué cuenta para el % mensual:** solo los tickets **con impacto en la penalización**, es decir,
  **incidencias y peticiones**, resueltos en el mes y no cancelados. Las tareas son trabajo interno:
  se mide su cumplimiento, pero no entran en la facturación.
- **Cálculo del % mensual: sin ponderar** (decidido; así funciona en la empresa del estudiante).
  `% = tickets computables cumplidos ÷ tickets computables`. Un P1 pesa lo mismo que un P4.
  Alternativas vistas en el mercado (documentadas para la entrevista): un indicador por prioridad con
  objetivo y descuento propios que se suman (habitual en pliegos públicos), o un % ponderado por
  prioridad (menos frecuente).
- **Punto ciego que el análisis debe mostrar:** al no ponderar, un mes puede salir "neutro" aunque
  se hayan incumplido casi todos los P1. El análisis cuantificará cuántos meses × cliente ocurre esto
  y cuánto malus habría supuesto con un indicador por prioridad → recomendación de renegociación.
- **Efecto escalón:** el ajuste no es proporcional. Pasar de 95,1 % a 94,9 % le cuesta a un Gold un 5 %
  de la cuota (1.250–2.000 €). Por eso los **últimos tickets del mes** cerca del umbral valen mucho
  más que la media, y la pregunta 5 (riesgo de incumplimiento) gana peso.
- **Atributos del cliente:** nombre ficticio, sector (banca, seguros, retail, sanidad, energía,
  administración pública), comunidad autónoma de su sede, nivel de contrato, fecha de alta y cuota.
- **Geografía:** la comunidad del cliente se usa para el mapa del dashboard. El reloj de SLA usa
  siempre los festivos de Madrid (§0.1).
- **KPI estrella que habilita:** el **balance neto bonus − malus en €** y el *% de la facturación
  ajustada*, por cliente, nivel y mes. Para atribuirlo a departamentos, el malus de un mes se reparte
  entre los tickets incumplidos de ese cliente y mes.

**Prueba de la API de festivos (Nager.Date, 2025/ES)**, hecha el 2026-10-15 desde la red corporativa:
responde un array con 32 festivos, **12 aplicables a Madrid** (nacionales + `ES-MD`).

| Fecha | Festivo | Ámbito |
|---|---|---|
| 2025-01-01 | Año Nuevo | Nacional |
| 2025-01-06 | Día de Reyes | Nacional |
| 2025-04-17 | Jueves Santo | Madrid |
| 2025-04-18 | Viernes Santo | Nacional |
| 2025-05-01 | Fiesta del trabajo | Nacional |
| 2025-05-02 | Fiesta de la Comunidad de Madrid | Madrid |
| 2025-08-15 | Asunción | Nacional |
| 2025-10-12 | Fiesta Nacional de España | Nacional |
| 2025-11-01 | Día de todos los Santos | Nacional |
| 2025-12-06 | Día de la Constitución | Nacional |
| 2025-12-08 | Inmaculada Concepción | Nacional |
| 2025-12-25 | Navidad | Nacional |

⚠️ **Limitación detectada:** la API **no incluye los festivos locales** de Madrid capital (San Isidro,
Almudena) y puede no reflejar los cambios autonómicos de cada año (por ejemplo, el 25 de julio está
marcado solo para `ES-GA` y `ES-PV`). **Solución:** se complementa con un CSV pequeño de festivos
locales y correcciones, contrastado con el calendario laboral oficial (BOE / BOCM). En el README se
declara qué viene de la API y qué se añadió a mano.

## 1. Identidad

| Campo | Valor |
|---|---|
| **Estudiante** | Rosmary González |
| **Rubro** | Service desk B2B: empresa tecnológica que atiende a empresas cliente con SLA por contrato |
| **Foco del negocio** | Medir y explicar el **cumplimiento de SLA** (respuesta y resolución) de los tickets |
| **Por qué este rubro** | Trabajo a diario con Jira y Service Desk: conozco desde dentro cómo se abren, escalan y cierran los tickets y por qué se incumple un SLA. Las ofertas de analista en consultoras IT y SaaS piden justamente métricas de soporte (SLA, MTTR, backlog). |
| **Organización ficticia** | **Brújula Soporte IT** — proveedor de service desk B2B con sede en Madrid, fundado en 2015, ~35 agentes en 5 departamentos, ~40 empresas cliente. **Ficticia: no representa a ninguna empresa real.** |
| **Nombre del repositorio** | `servicedesk-sla-analytics-spain` *(en inglés, porque el mercado también es internacional)* |
| **Pregunta central del proyecto** | ¿Cuánta facturación perdemos y ganamos por el cumplimiento de SLA, y qué la explica: la carga, los escalados, el verano o el calendario? |
| **La historia en una línea** | "Soy analista de datos en un service desk. Me pidieron entender por qué perdemos facturación por SLA. Crucé 25.000 tickets con el calendario laboral de Madrid y el clima real, y descubrí que…" *(el final lo escribe el análisis, en la Fase 4)* |

## 2. Fuentes de datos

### 2.1 Fuente externa REAL (obligatoria)
Dos fuentes reales, ambas de **Nivel 1 (globales)**, aprobadas el 2026-10-15 desde la red corporativa.

| Campo | Open-Meteo (clima) | Nager.Date (festivos) |
|---|---|---|
| Endpoint base | `https://archive-api.open-meteo.com/v1/archive` | `https://date.nager.at/api/v3/PublicHolidays/{año}/ES` |
| Variables | temperature_2m_max, temperature_2m_min, precipitation_sum | fecha, nombre, ámbito (`counties`: nacional o `ES-MD`) |
| Punto / ámbito | Madrid (lat 40.4168, lon −3.7038) | España, filtrado a nacional + Comunidad de Madrid |
| Frecuencia | **Diaria** | Por fecha |
| Período | 2024-01-01 → 2025-12-31 | 2024 y 2025 |
| Uso en el análisis | `dim_clima_madrid` → correlación 2 (calor) | `dim_tiempo` → reloj de SLA + correlación 1 (post-festivo) |
| ¿Key? | No | No |

**Los 4 chequeos:**

| Chequeo | Open-Meteo | Nager.Date |
|---|---|---|
| 1. ¿Responde? | ✅ | ✅ |
| 2. ¿Cubre el período? | ✅ 2024-01-01 → 2025-12-31 | ✅ 12 festivos de Madrid en 2024 y 12 en 2025 |
| 3. ¿Granularidad? | ✅ Diaria: 731 días, 0 nulos en Tmax | ✅ Por fecha |
| 4. ¿Requiere key? | ✅ No | ✅ No |

**Dato para el diseño:** 84 días con Tmax > 35 °C en los dos años (~42 por año, concentrados en
junio–agosto). Es una muestra suficiente para la correlación 2.

**Detalle encontrado:** la API devuelve `latitude: 40.386642, longitude: -3.6760864`, no el punto
pedido. Open-Meteo trabaja con una rejilla y entrega la **celda más cercana** (~4 km). Para el
análisis es irrelevante, pero se documenta.

**Respuesta cruda — Open-Meteo:**
```json
{"latitude":40.386642,"longitude":-3.6760864,"generationtime_ms":77.19,"utc_offset_seconds":7200,
"timezone":"Europe/Madrid","timezone_abbreviation":"GMT+2","elevation":666.0,"daily_units":{"time":
"iso8601","temperature_2m_max":"°C","temperature_2m_min":"°C","precipitation_sum":"mm"},"daily":
{"time":["2024-01-01","2024-01-02","2024-01-03", ...
```

**Respuesta cruda — Nager.Date:**
```json
[{"date":"2024-01-01","localName":"Año Nuevo","name":"New Year's Day","countryCode":"ES","fixed":false,
"global":true,"counties":null,"launchYear":null,"types":["Public"]},{"date":"2024-01-06","localName":
"Día de Reyes / Epifanía del Señor","name":"Epiphany","countryCode":"ES","fixed":false,"global": ...
```

Formatos de fecha: ambas en `YYYY-MM-DD`. No hay que normalizar nada en la Fase 1.

### 2.2 Fuente interna (sintética o dataset público)
| Campo | Valor |
|---|---|
| Origen | **Sintética** (Faker + NumPy, semilla fija), con las correlaciones de §2.3 |
| Período | **2024-01-01 → 2025-12-31** (2 años completos, permite YoY) |
| Volumen de hechos | ~**25.000 tickets** (~50 por día laborable) + su historial de estados |
| Volumen de entidades | ~**40 clientes** (8 Gold · 14 Silver · 18 Bronze) |
| Agentes | ~**35 agentes** repartidos en los 5 departamentos, con calendario de vacaciones propio |
| Volumen de ítems | 3 tipos × 4 prioridades → **10 políticas de SLA** (§0.2) |
| Geografía | Comunidad autónoma de la sede del cliente |

### 2.3 Correlaciones intencionales
Lo que el generador va a inyectar y el análisis va a "descubrir". Son señales **conocidas de
antemano**: el análisis demuestra que el pipeline las detecta y las cuantifica bien.

| # | Correlación | Fuente | Por qué es plausible |
|---|---|---|---|
| 1 | **Efecto post-festivo:** el primer día laborable tras un festivo o puente entra ~+40 % de tickets; el incumplimiento sube ese día y el siguiente | 🌐 Festivos reales (Nager.Date + CSV local) | La cola se acumula mientras no se atiende |
| 2 | **Calor e infraestructura:** con Tmax > 35 °C en Madrid suben las incidencias P1/P2 de Infraestructura (efecto **moderado**) | 🌐 Clima real (Open-Meteo) | Refrigeración de CPD, cortes eléctricos |
| 3 | **Saturación:** si el backlog abierto de un departamento supera un umbral, el tiempo de resolución crece de forma no lineal | Interna | Colas saturadas |
| 4 | **Coste del escalado:** los tickets que pasan por más de un departamento incumplen ~3 veces más; Desarrollo es el peor departamento | Interna | Cada reasignación vuelve a poner el ticket en cola |
| 5 | **Gold se prioriza:** a igual tipo y prioridad, Gold cumple mejor que Bronze | Interna | Las colas se ordenan por penalización |
| 6 | **Vacaciones de verano:** en julio y agosto la plantilla disponible baja (~30 % en agosto) y los tiempos de 1ª respuesta y resolución se alargan | Interna (calendario de vacaciones) | Aportado por el estudiante desde su experiencia en el service desk |

⚠️ **Confusión deliberada entre la 2 y la 6:** el calor y las vacaciones caen en los mismos meses. Si
solo se compara verano con invierno, no se puede saber cuál de las dos causa los incumplimientos.
Por diseño, el calor actúa **por día** (picos puntuales de incidencias de Infraestructura) y las
vacaciones actúan **por mes** (menos capacidad en todos los departamentos). El notebook (Fase 4) debe
separarlas comparando **días calurosos y no calurosos dentro de julio y agosto**.

## 3. Modelo dimensional

| Rol | Tabla | Columnas clave |
|---|---|---|
| HECHO | `fact_ticket` | ticket_id, cliente_id, agente_id, sla_id, departamento_id, fecha_creacion, fecha_primera_respuesta, fecha_resolucion, fecha_cierre, estado_actual, n_reasignaciones, min_respuesta_sla, min_resolucion_sla, cumple_respuesta, cumple_resolucion, computa_facturacion |
| HECHO (mensual) | `fact_facturacion_mensual` | cliente_id, mes, cuota_eur, n_tickets_computables, n_cumplidos, pct_cumplimiento, tramo, pct_ajuste, ajuste_eur, importe_facturado_eur — **otro grano: cliente × mes** |
| HECHO (detalle) | `fact_ticket_estado` | ticket_id, secuencia, estado, departamento_id, agente_id, inicio, fin, pausa_reloj — **el historial que permite calcular las pausas** |
| QUIÉN (cliente) | `dim_cliente` | cliente_id, nombre, sector, comunidad_autonoma, nivel_contrato, cuota_mensual_eur, fecha_alta |
| QUIÉN (resolutor) | `dim_agente` | agente_id, nombre, departamento_id, nivel (N1/N2/N3), fecha_alta |
| — | `agente_ausencia` | agente_id, fecha_inicio, fecha_fin, motivo — **alimenta la correlación 6** |
| QUÉ | `dim_sla` | sla_id, tipo, prioridad, objetivo_respuesta_min, objetivo_resolucion_min, reloj (24x7 / laboral) |
| — | `dim_tramo_ajuste` | nivel_contrato, pct_desde, pct_hasta, tipo (bonus/neutro/malus), pct_ajuste |
| DÓNDE / QUIÉN | `dim_departamento` | departamento_id, nombre, rol |
| CUÁNDO | `dim_tiempo` | fecha, año, trimestre, mes, dia_semana, es_laborable, es_festivo_madrid, nombre_festivo, es_post_festivo, es_puente |
| CONTEXTO | `dim_clima_madrid` | fecha, temp_max, temp_min, precipitacion, es_dia_caluroso (Tmax > 35 °C) |

*(Esbozo: los nombres finales se fijan en la Fase 2.)*

## 4. Preguntas de negocio (5–6)

| # | Pregunta | Área | Módulo de análisis | Acción esperada |
|---|---|---|---|---|
| 1 | ¿Qué % de tickets cumple el SLA por tipo, prioridad y nivel de contrato, y qué clientes caen por debajo de su objetivo o quedan a menos de 1 punto del siguiente tramo de malus? | Service Delivery | Calidad (#8) + descriptivo | Plan de choque con los clientes en riesgo **antes** del cierre de mes |
| 2 | ¿Cuál es el balance neto bonus − malus en €, y qué departamentos y tipos de ticket concentran el 80 % del malus? | Finanzas | Pareto (#1) | Reforzar o formar donde más facturación se pierde |
| 3 | ¿Los festivos y el calor cambian el volumen de tickets y el cumplimiento? | Planificación | Correlación con contexto (#6) | Turnos reforzados tras los puentes; guardia de Infraestructura en olas de calor |
| 4 | ¿Cuántos tickets entrarán el próximo trimestre y cuántos agentes harán falta en agosto? | Workforce management | Forecast (#5) | Planificar las vacaciones sin caer de tramo |
| 5 | ¿Qué tickets abiertos tienen más probabilidad de incumplir y cuánto malus evitaría resolverlos a tiempo? | Coordinación del Service Desk | Riesgo (#7, regresión logística) | Escalado preventivo, priorizando los tickets que deciden el tramo del mes |
| 6 | ¿Qué perfiles de cliente hay según su patrón de tickets (volumen, % P1, escalados, malus)? | Account management | Clustering (#2) | Renegociar contratos cuyo nivel no se ajusta al uso real |

## 5. Módulos de análisis elegidos
- [x] Calidad y outliers *(obligatorio)*
- [x] Pareto / ABC
- [x] RFM + Clustering *(adaptado: perfil de tickets del cliente en lugar de RFM)*
- [ ] Cohortes
- [ ] Market Basket
- [x] Forecast
- [x] Correlación con contexto externo *(muy recomendado)*
- [x] Churn / riesgo *(adaptado: riesgo de incumplir el SLA)*

## 6. Arquitectura (dibujo del flujo)

```
 FUENTES                                                                       
 ┌─────────────────────┐  ┌──────────────────────┐  ┌─────────────────────┐
 │ 🌐 Open-Meteo        │  │ 🌐 Nager.Date         │  │ ✍️ CSV manual        │
 │ clima diario Madrid │  │ festivos ES + ES-MD  │  │ festivos locales    │
 │ 2024–2025 (REAL)    │  │ 2024–2025 (REAL)     │  │ (BOCM)              │
 └──────────┬──────────┘  └──────────┬───────────┘  └──────────┬──────────┘
            └────────────────────────┼─────────────────────────┘
                                     ▼
 CAPA 1 — ETL (Python)    ① extract_clima.py · extract_festivos.py
                                     │   → data/raw/clima.csv, festivos.csv
                                     ▼
                          ② generate_tickets_data.py   (🧪 SINTÉTICO, SEED fija)
                             · lee clima + festivos → calendario laboral Madrid
                             · clientes, agentes, vacaciones, tickets, estados
                             · inyecta las 6 correlaciones de §2.3
                             · calcula minutos de SLA consumidos (con pausas)
                                     │   → data/raw/*.csv
                                     ▼
                          ③ load_to_postgres.py  (upsert, dims → hechos)
                          ④ verificar_carga.py   (filas, nulos, FKs huérfanas)
                                     ▼
 CAPA 2 — SQL (PostgreSQL)
   dims:   dim_tiempo · dim_clima_madrid · dim_cliente · dim_agente
           agente_ausencia · dim_departamento · dim_sla · dim_tramo_ajuste
   hechos: fact_ticket · fact_ticket_estado
   SP:     sp_calcular_facturacion_mensual(mes) → fact_facturacion_mensual
   vistas: v_ticket_enriquecido · v_kpis_diarios · v_cumplimiento_mensual
           v_pareto_malus
                                     │
                  ┌──────────────────┴──────────────────┐
                  ▼                                     ▼
 CAPA 3 — POWER BI (el "qué")            CAPA 4 — PYTHON (el "por qué")
   P1 · ¿Cómo vamos? cumplimiento,          calidad · Pareto del malus
        bonus/malus €, clientes en riesgo   correlación calor/festivos
   P2 · ¿Por qué? calor, festivos,          forecast de volumen y agosto
        escalados, punto ciego de P1        riesgo de incumplir · clusters
                  └──────────────────┬──────────────────┘
                                     ▼
 CAPA 5 — NARRATIVA   README · business_case · insights_findings · LinkedIn
```

**Decisiones de diseño que muestra el dibujo:**

1. **Las APIs se extraen antes de generar los datos.** El generador necesita el clima y los festivos
   reales para inyectar las correlaciones 1 y 2, y para saber qué horas cuentan en el reloj de SLA.
2. **Los minutos de SLA se calculan en Python** (ETL), recorriendo el historial de estados con el
   calendario laboral. La aritmética de horas laborables con pausas es mucho más clara en Python que
   en SQL.
3. **La facturación mensual se calcula en SQL** con un procedimiento almacenado: es la regla de
   negocio que se recalcula cada mes, la prueba de "sé automatizar".

## 7. Stack y entorno

| Capa | Herramienta | Por qué |
|---|---|---|
| Generación | Python · Faker (`es_ES`) · NumPy | Datos sintéticos realistas, en español y reproducibles con semilla |
| Extracción | Python · requests | Consumo de APIs con reintentos, timeout y log |
| Base | PostgreSQL 16 | La más pedida en ofertas junto a SQL Server; gratis |
| Transformación | SQL (vistas + procedimientos) · pandas | Lógica de negocio junto a los datos |
| Visualización | Power BI Desktop | Windows; la herramienta de BI que más piden las ofertas |
| Análisis | Jupyter · pandas · scipy · scikit-learn · statsmodels/Prophet | Correlación, clustering, regresión logística, forecast |

| Campo | Valor |
|---|---|
| **Sistema operativo del estudiante** | Windows |
| **Herramienta de BI elegida** | Power BI Desktop |
| **PostgreSQL** | Docker o instalación nativa *(se decide en la Fase 0.5, según lo que permita el equipo corporativo)* |

## 8. Alcance y limitaciones

**Dentro:**
- Ciclo de vida completo del ticket (estados, reasignaciones y pausas) y cálculo del SLA de respuesta
  y resolución con el calendario laboral de Madrid.
- Bonus/malus mensual por cliente según los tramos de su contrato.
- Cruce con clima y festivos reales; las 6 preguntas de §4.
- Pipeline reproducible: ETL → PostgreSQL → Power BI + notebook → documentación.

**Fuera:**
- Satisfacción del cliente (CSAT/encuestas), coste por agente y nóminas.
- Integración real con Jira o ServiceNow: los datos son sintéticos y no se conectan a ninguna herramienta.
- Tiempo real o streaming: la actualización es por lotes (diaria o mensual).

**Limitaciones de los datos:**
- Tickets, clientes, agentes y vacaciones son **sintéticos**; las correlaciones están inyectadas a
  propósito y su magnitud se conoce de antemano.
- Clima y festivos son **reales**, pero Nager.Date no incluye los festivos locales (se completan a
  mano) y Open-Meteo da la celda de rejilla más cercana, no una estación concreta.
- Un único punto de clima (Madrid) para todos los clientes: el calor afecta al CPD de la sede, no a
  la comunidad de cada cliente.

## 9. Aprobación
- [x] **País, moneda y mercado objetivo definidos.**
- [x] La fuente externa pasó los **4 chequeos** del Paso 3, y la respuesta cruda está pegada arriba.
- [x] La serie externa es **diaria o mensual** (no anual).
- [x] El período cubre al menos 2 años.
- [x] Las correlaciones intencionales están escritas.
- [x] La herramienta de BI es compatible con el sistema operativo del estudiante.
- [x] Cada pregunta termina en una acción concreta.
