# Diccionario de datos · Brújula Soporte IT

Esquema `servicedesk` de PostgreSQL. Generado con `python 05_docs/generar_data_dictionary.py` (no editar a mano). Los **ejemplos** son valores reales de la base; los datos de negocio son sintéticos y el clima y los festivos, reales.

- **Tablas** (`dim_*`, `fact_*`): el modelo en estrella, con claves y restricciones de negocio.
- **Vistas** (`v_*`): la definición única de cada cifra; las usan Power BI y el análisis en Python.

## Índice

- [agente_ausencia](#agente_ausencia) · tabla
- [dim_agente](#dim_agente) · tabla
- [dim_cliente](#dim_cliente) · tabla
- [dim_clima_madrid](#dim_clima_madrid) · tabla
- [dim_departamento](#dim_departamento) · tabla
- [dim_sla](#dim_sla) · tabla
- [dim_sprint](#dim_sprint) · tabla
- [dim_tiempo](#dim_tiempo) · tabla
- [dim_tramo_ajuste](#dim_tramo_ajuste) · tabla
- [fact_facturacion_sprint](#fact_facturacion_sprint) · tabla
- [fact_ticket](#fact_ticket) · tabla
- [fact_ticket_estado](#fact_ticket_estado) · tabla
- [v_cumplimiento_sprint](#v_cumplimiento_sprint) · vista
- [v_facturacion_sprint](#v_facturacion_sprint) · vista
- [v_kpis_diarios](#v_kpis_diarios) · vista
- [v_liquidacion_anual](#v_liquidacion_anual) · vista
- [v_pareto_penalizacion](#v_pareto_penalizacion) · vista
- [v_perfil_cliente](#v_perfil_cliente) · vista
- [v_ticket_enriquecido](#v_ticket_enriquecido) · vista

## agente_ausencia

*Tabla · 405 filas*

Vacaciones y bajas: en agosto falta ~32 % de la plantilla (correlación 6)

| Columna | Tipo | Clave | Descripción | Ejemplo |
|---|---|---|---|---|
| `ausencia_id` | integer | PK | Identificador de la ausencia | `1` |
| `agente_id` | text | FK → dim_agente | Identificador del agente | `AGT-001` |
| `fecha_inicio` | date |  | Primer día de la ausencia | `2024-01-22` |
| `fecha_fin` | date |  | Último día de la ausencia | `2024-01-24` |
| `dias_laborables` | smallint |  | Días laborables de ausencia | `3` |
| `motivo` | text |  | Motivo de la ausencia (vacaciones o baja médica) | `vacaciones` |

## dim_agente

*Tabla · 35 filas*

Agentes ficticios (nombres generados con Faker). En los datos, un senior tarda ~18 % menos que un junior en el mismo trabajo

| Columna | Tipo | Clave | Descripción | Ejemplo |
|---|---|---|---|---|
| `agente_id` | text | PK | Identificador del agente | `AGT-001` |
| `nombre` | text |  | Nombre (ficticio) del agente | `Dani Amaya` |
| `departamento_id` | smallint | FK → dim_departamento | Identificador del departamento | `1` |
| `nivel_soporte` | text |  | Nivel de soporte del departamento (N1, N2…) | `N1` |
| `seniority` | text |  | Antigüedad del agente: senior o junior | `junior` |
| `fecha_alta` | date |  | Fecha de incorporación del agente | `2021-06-09` |

## dim_cliente

*Tabla · 40 filas*

Empresas cliente ficticias. Nivel de contrato = objetivo de SLA y tramos de bonificación/penalización

| Columna | Tipo | Clave | Descripción | Ejemplo |
|---|---|---|---|---|
| `cliente_id` | text | PK | Identificador del cliente | `CLI-001` |
| `nombre` | text |  | Nombre (ficticio) del cliente | `Energía Moles S.L.` |
| `sector` | text |  | Sector del cliente | `Energía` |
| `comunidad_autonoma` | text |  | Comunidad autónoma de la sede del cliente | `País Vasco` |
| `nivel_contrato` | text |  | Nivel de contrato: Gold, Silver o Bronze | `Gold` |
| `cuota_anual_eur` | numeric(12,2) |  | Se factura por sprint: cuota_anual / dim_sprint.n_sprints_anio | `462000.00` |
| `n_usuarios` | integer |  | Usuarios del cliente que pueden abrir tickets | `1387` |
| `fecha_alta` | date |  | Fecha de alta del contrato | `2021-11-06` |

## dim_clima_madrid

*Tabla · 733 filas*

Clima diario REAL de Madrid (Open-Meteo). Contexto de la correlación 2 (calor → Infraestructura)

| Columna | Tipo | Clave | Descripción | Ejemplo |
|---|---|---|---|---|
| `fecha` | date | PK, FK → dim_tiempo | Fecha del día | `2024-01-01` |
| `temp_max` | numeric(4,1) |  | Temperatura máxima en Madrid (°C, Open-Meteo) | `9.4` |
| `temp_min` | numeric(4,1) |  | Temperatura mínima en Madrid (°C, Open-Meteo) | `3.1` |
| `precipitacion_mm` | numeric(5,1) |  | Lluvia diaria en Madrid (mm) | `0.0` |
| `es_dia_caluroso` | boolean |  | Temperatura máxima por encima de 35 °C | `false` |

## dim_departamento

*Tabla · 5 filas*

Grupos resolutores. Todo ticket entra por Service Desk N1 (id 1)

| Columna | Tipo | Clave | Descripción | Ejemplo |
|---|---|---|---|---|
| `departamento_id` | smallint | PK | Identificador del departamento | `1` |
| `nombre` | text |  | Nombre del departamento | `Service Desk N1` |
| `rol` | text |  | Qué hace el departamento | `Recepción, triaje y resoluc…` |
| `n_agentes` | smallint |  | Agentes del departamento | `12` |
| `nivel_soporte` | text |  | Nivel de soporte del departamento (N1, N2…) | `N1` |

## dim_sla

*Tabla · 10 filas*

Matriz de SLA tipo × prioridad (Ficha §0.2). Minutos de reloj: 24x7 para P1, laboral L–V 9–18 para el resto

| Columna | Tipo | Clave | Descripción | Ejemplo |
|---|---|---|---|---|
| `sla_id` | text | PK | Política de SLA aplicada (tipo × prioridad) | `INC-P1` |
| `tipo` | text |  | Tipo de ticket: Incidencia, Petición o Tarea | `Incidencia` |
| `prioridad` | text |  | Prioridad P1 (crítica) a P4 (baja) | `P1` |
| `objetivo_respuesta_min` | integer |  | Minutos de reloj permitidos para la 1ª respuesta | `15` |
| `objetivo_resolucion_min` | integer |  | Minutos de reloj permitidos para la resolución | `240` |
| `reloj` | text |  | Reloj del SLA: 24x7 o laboral (L–V 09–18 sin festivos de Madrid) | `24x7` |
| `computa_facturacion` | boolean |  | El ticket cuenta para la factura (no las tareas, ni cancelados ni abiertos) | `true` |

## dim_sprint

*Tabla · 35 filas*

Sprints de 3 semanas (Ficha §0.4). Unidad de medición del SLA y de facturación

| Columna | Tipo | Clave | Descripción | Ejemplo |
|---|---|---|---|---|
| `sprint_id` | text | PK | AAAA-NN por el año en que empieza (2024-18 acaba en enero de 2025) | `2024-01` |
| `anio_sprint` | smallint |  | Año del sprint | `2024` |
| `numero` | smallint |  | Número del sprint dentro del año | `1` |
| `fecha_inicio` | date |  | Primer día del sprint | `2024-01-01` |
| `fecha_fin` | date |  | Último día del sprint | `2024-01-19` |
| `dias_laborables` | smallint |  | Días laborables del sprint | `14` |
| `es_completo` | boolean |  | El sprint está completo dentro del periodo de datos | `true` |
| `n_sprints_anio` | smallint |  | Sprints de ese año: la cuota de un sprint es cuota_anual / n_sprints_anio | `18` |

## dim_tiempo

*Tabla · 733 filas*

Calendario laboral de la sede (Madrid): festivos reales (Nager.Date + BOCM) y sprint de cada día

| Columna | Tipo | Clave | Descripción | Ejemplo |
|---|---|---|---|---|
| `fecha` | date | PK | Fecha del día | `2024-01-01` |
| `anio` | smallint |  | Año | `2024` |
| `trimestre` | smallint |  | Trimestre | `1` |
| `mes` | smallint |  | Mes (1–12) | `1` |
| `dia_semana` | smallint |  | Día de la semana (1 = lunes … 7 = domingo) | `1` |
| `es_fin_semana` | boolean |  | Sábado o domingo | `false` |
| `nombre_festivo` | text |  | Nombre del festivo | `Año Nuevo` |
| `es_festivo_madrid` | boolean |  | Festivo nacional, autonómico o local de Madrid | `true` |
| `es_laborable` | boolean |  | Día laborable en Madrid | `false` |
| `es_post_festivo` | boolean |  | Primer laborable tras un festivo entre semana (correlación 1) | `false` |
| `es_puente` | boolean |  | Día de puente | `false` |
| `sprint_id` | text | FK → dim_sprint | El sábado y el domingo tras el cierre de un sprint ya cuentan para el siguiente | `2024-01` |

## dim_tramo_ajuste

*Tabla · 11 filas*

Tramos sobre la cuota del sprint: % de cumplimiento en [pct_desde, pct_hasta) → % de ajuste

| Columna | Tipo | Clave | Descripción | Ejemplo |
|---|---|---|---|---|
| `tramo_id` | smallint | PK | Tramo de ajuste de la factura | `1` |
| `nivel_contrato` | text |  | Nivel de contrato: Gold, Silver o Bronze | `Gold` |
| `pct_desde` | numeric(5,2) |  | Límite inferior del tramo (% de cumplimiento) | `98.00` |
| `pct_hasta` | numeric(5,2) |  | Límite superior del tramo (% de cumplimiento) | `100.01` |
| `tipo` | text |  | Tipo de tramo: bonus, neutro o deficiente | `bonus` |
| `pct_ajuste` | numeric(5,2) |  | % de ajuste aplicado sobre la cuota (con el tope −3,5 % / +3 %) | `3.00` |

## fact_facturacion_sprint

*Tabla · 1.288 filas*

Bonificación/penalización por cliente y sprint. La llena sp_calcular_facturacion_sprint (03_stored_procedures.sql)

| Columna | Tipo | Clave | Descripción | Ejemplo |
|---|---|---|---|---|
| `cliente_id` | text | PK, FK → dim_cliente | Identificador del cliente | `CLI-001` |
| `sprint_id` | text | PK, FK → dim_sprint | Sprint (AAAA-NN) | `2024-01` |
| `nivel_contrato` | text |  | Nivel de contrato: Gold, Silver o Bronze | `Gold` |
| `cuota_sprint_eur` | numeric(12,2) |  | Cuota que corresponde al sprint (cuota anual ÷ nº de sprints del año, €) | `25666.67` |
| `n_tickets_computables` | integer |  | Tickets que cuentan para la factura | `31` |
| `n_cumplidos` | integer |  | Tickets computables que cumplen | `31` |
| `pct_cumplimiento` | numeric(5,2) |  | NULL si el cliente no tuvo tickets computables en el sprint (tramo neutro, sin ajuste) | `100.00` |
| `tramo_id` | smallint | FK → dim_tramo_ajuste | Tramo de ajuste de la factura | `1` |
| `tipo_tramo` | text |  | Tramo del sprint: bonus, neutro o deficiente | `bonus` |
| `pct_ajuste` | numeric(5,2) |  | % de ajuste aplicado sobre la cuota (con el tope −3,5 % / +3 %) | `3.00` |
| `ajuste_eur` | numeric(12,2) |  | Ajuste en la factura: positivo = bonus, negativo = penalización (€) | `770.00` |
| `calculado_en` | timestamp with time zone |  | Momento en que se congeló la facturación del sprint | `2026-10-20 16:36:17.750407+02` |

## fact_ticket

*Tabla · 25.300 filas*

Un ticket por fila (sintético, SEED=42), con su SLA ya medido. Corte: 2026-01-02 18:00

| Columna | Tipo | Clave | Descripción | Ejemplo |
|---|---|---|---|---|
| `ticket_id` | text | PK | Identificador del ticket (TCK-NNNNNN) | `TCK-000001` |
| `cliente_id` | text | FK → dim_cliente | Identificador del cliente | `CLI-005` |
| `sla_id` | text | FK → dim_sla | Política de SLA aplicada (tipo × prioridad) | `PET-P3` |
| `departamento_id` | smallint | FK → dim_departamento | Departamento que resuelve (o donde está el ticket al corte) | `1` |
| `agente_id` | text | FK → dim_agente | Identificador del agente | `AGT-005` |
| `fecha_creacion` | timestamp without time zone |  | Fecha y hora de apertura | `2024-01-02 08:12:00` |
| `fecha_primera_respuesta` | timestamp without time zone |  | Fecha y hora de la 1ª respuesta | `2024-01-02 10:02:00` |
| `fecha_resolucion` | timestamp without time zone |  | Fecha y hora de resolución | `2024-01-04 09:18:00` |
| `fecha_cierre` | timestamp without time zone |  | Cierre automático 3 días laborables tras resolver | `2024-01-09 09:18:00` |
| `fecha_cancelacion` | timestamp without time zone |  | Fecha y hora de cancelación (si se canceló) | `2024-01-08 11:54:00` |
| `fecha_incumplimiento` | timestamp without time zone |  | Momento en que se agotó el SLA de resolución (solo incumplidos) | `2024-01-05 18:00:00` |
| `estado_actual` | text |  | Último estado del ticket | `Cerrado` |
| `estado_sla` | text |  | cumplido, incumplido, en curso o cancelado | `cumplido` |
| `n_reasignaciones` | smallint |  | Veces que el ticket cambió de departamento | `0` |
| `min_respuesta_sla` | integer |  | Minutos de reloj hasta la 1ª respuesta | `62` |
| `min_resolucion_sla` | integer |  | Minutos de reloj consumidos sin contar las pausas; si sigue abierto, hasta el corte | `1098` |
| `min_pausa` | integer |  | Minutos en pausa (esperando al cliente) | `0` |
| `cumple_respuesta` | boolean |  | Cumple el SLA de 1ª respuesta | `true` |
| `cumple_resolucion` | boolean |  | Cumple el SLA de resolución | `true` |
| `computa_facturacion` | boolean |  | Incidencia o petición, medida (no cancelada ni en curso): entra en el % del sprint | `true` |
| `sprint_apertura` | text | FK → dim_sprint | Sprint en que entra el ticket: carga de trabajo | `2024-01` |
| `sprint_medicion` | text | FK → dim_sprint | Sprint en que se conoce el resultado: resolución si cumple, vencimiento si incumple | `2024-01` |

## fact_ticket_estado

*Tabla · 140.602 filas*

Historial de estados: por qué departamentos pasó cada ticket y cuánto tiempo estuvo en cada uno

| Columna | Tipo | Clave | Descripción | Ejemplo |
|---|---|---|---|---|
| `ticket_id` | text | PK, FK → fact_ticket | Identificador del ticket (TCK-NNNNNN) | `TCK-000001` |
| `secuencia` | smallint | PK | Orden del cambio de estado dentro del ticket | `1` |
| `estado` | text |  | Estado del ticket en ese tramo del historial | `Abierto` |
| `departamento_id` | smallint | FK → dim_departamento | Identificador del departamento | `1` |
| `agente_id` | text | FK → dim_agente | Identificador del agente | `AGT-005` |
| `inicio` | timestamp without time zone |  | Momento en que el ticket entra en este estado | `2024-01-02 08:12:00` |
| `fin` | timestamp without time zone |  | NULL = estado actual al corte (o estado final: Cerrado / Cancelado) | `2024-01-02 10:02:00` |
| `pausa_reloj` | boolean |  | El estado pausa el reloj de resolución (Esperando al cliente) | `false` |

## v_cumplimiento_sprint

*Vista · 1.235 filas*

Cliente × sprint calculado en vivo: % de cumplimiento, tramo y ajuste en €. Lo oficial se guarda en fact_facturacion_sprint

| Columna | Tipo | Clave | Descripción | Ejemplo |
|---|---|---|---|---|
| `cliente_id` | text |  | Identificador del cliente | `CLI-013` |
| `cliente` | text |  | Nombre (ficticio) del cliente | `Transportes Arévalo S.A.` |
| `nivel_contrato` | text |  | Nivel de contrato: Gold, Silver o Bronze | `Silver` |
| `sprint_id` | text |  | Sprint (AAAA-NN) | `2024-05` |
| `anio_sprint` | smallint |  | Año del sprint | `2024` |
| `fecha_inicio` | date |  | Primer día del sprint | `2024-03-25` |
| `fecha_fin` | date |  | Último día del sprint | `2024-04-12` |
| `cuota_sprint_eur` | numeric |  | Cuota que corresponde al sprint (cuota anual ÷ nº de sprints del año, €) | `7000.00` |
| `n_tickets_computables` | bigint |  | Tickets que cuentan para la factura | `12` |
| `n_cumplidos` | bigint |  | Tickets computables que cumplen | `11` |
| `n_incumplidos` | bigint |  | Tickets computables que incumplen | `1` |
| `n_p1` | bigint |  | Tickets P1 | `1` |
| `n_p1_incumplidos` | bigint |  | Tickets P1 incumplidos | `0` |
| `pct_cumplimiento` | numeric |  | % de cumplimiento del SLA de resolución | `91.67` |
| `tramo_id` | smallint |  | Tramo de ajuste de la factura | `7` |
| `tipo_tramo` | text |  | Tramo del sprint: bonus, neutro o deficiente | `neutro` |
| `pct_ajuste` | numeric |  | % de ajuste aplicado sobre la cuota del sprint, con el tope del contrato (entre -3,5 y +3) | `0.00` |
| `ajuste_eur` | numeric |  | Ajuste en la factura: positivo = bonus, negativo = penalización (€) | `0.00` |
| `puntos_sobre_tramo_inferior` | numeric |  | Puntos de % que le sobran al cliente antes de caer al tramo de abajo | `1.67` |
| `pct_ajuste_tramo` | numeric(5,2) |  | % de ajuste que marca el tramo, antes de aplicar el tope | `0.00` |

## v_facturacion_sprint

*Vista · 1.288 filas*

fact_facturacion_sprint + margen sobre el tramo inferior y objetivo contractual (vacía hasta ejecutar el sp del archivo 03)

| Columna | Tipo | Clave | Descripción | Ejemplo |
|---|---|---|---|---|
| `cliente_id` | text |  | Identificador del cliente | `CLI-001` |
| `sprint_id` | text |  | Sprint (AAAA-NN) | `2024-01` |
| `nivel_contrato` | text |  | Nivel de contrato: Gold, Silver o Bronze | `Gold` |
| `cuota_sprint_eur` | numeric(12,2) |  | Cuota que corresponde al sprint (cuota anual ÷ nº de sprints del año, €) | `25666.67` |
| `n_tickets_computables` | integer |  | Tickets que cuentan para la factura | `31` |
| `n_cumplidos` | integer |  | Tickets computables que cumplen | `31` |
| `pct_cumplimiento` | numeric(5,2) |  | % de cumplimiento del SLA de resolución | `100.00` |
| `tipo_tramo` | text |  | Tramo del sprint: bonus, neutro o deficiente | `bonus` |
| `pct_ajuste` | numeric(5,2) |  | % de ajuste aplicado sobre la cuota (con el tope −3,5 % / +3 %) | `3.00` |
| `ajuste_eur` | numeric(12,2) |  | Ajuste en la factura: positivo = bonus, negativo = penalización (€) | `770.00` |
| `puntos_sobre_tramo_inferior` | numeric |  | Puntos de % que le sobran al cliente antes de caer al tramo de abajo | `2.00` |
| `objetivo_contractual` | integer |  | % de cumplimiento comprometido en el contrato | `95` |

## v_kpis_diarios

*Vista · 733 filas*

Un día por fila: entradas, salidas, backlog, cumplimiento (por día de medición), festivos, clima y ausencias

| Columna | Tipo | Clave | Descripción | Ejemplo |
|---|---|---|---|---|
| `fecha` | date |  | Fecha del día | `2024-01-01` |
| `anio` | smallint |  | Año | `2024` |
| `mes` | smallint |  | Mes (1–12) | `1` |
| `dia_semana` | smallint |  | Día de la semana (1 = lunes … 7 = domingo) | `1` |
| `sprint_id` | text |  | Sprint (AAAA-NN) | `2024-01` |
| `es_laborable` | boolean |  | Día laborable en Madrid | `false` |
| `es_festivo_madrid` | boolean |  | Festivo nacional, autonómico o local de Madrid | `true` |
| `nombre_festivo` | text |  | Nombre del festivo | `Año Nuevo` |
| `es_post_festivo` | boolean |  | Primer día laborable tras un festivo o puente | `false` |
| `es_puente` | boolean |  | Día de puente | `false` |
| `temp_max` | numeric(4,1) |  | Temperatura máxima en Madrid (°C, Open-Meteo) | `9.4` |
| `precipitacion_mm` | numeric(5,1) |  | Lluvia diaria en Madrid (mm) | `0.0` |
| `es_dia_caluroso` | boolean |  | Temperatura máxima por encima de 35 °C | `false` |
| `tickets_creados` | bigint |  | Tickets abiertos ese día | `0` |
| `p1_creados` | bigint |  | Tickets P1 abiertos ese día | `0` |
| `infra_p1_p2_creados` | bigint |  | Incidencias P1/P2 de Infraestructura abiertas ese día | `0` |
| `tickets_salida` | bigint |  | Tickets resueltos o cancelados ese día | `0` |
| `backlog_fin_dia` | numeric |  | Tickets abiertos al final del día (entradas acumuladas − resueltos/cancelados acumulados) | `0` |
| `cumplidos` | bigint |  | Tickets medidos ese día que cumplen | `0` |
| `incumplidos` | bigint |  | Tickets medidos ese día que incumplen | `0` |
| `pct_cumplimiento` | numeric |  | % de cumplimiento del SLA de resolución | `100.0` |
| `agentes_activos` | bigint |  | Agentes en plantilla ese día | `34` |
| `agentes_ausentes` | bigint |  | Agentes de vacaciones o baja ese día | `0` |
| `pct_agentes_ausentes` | numeric |  | % de la plantilla ausente | `0.0` |

## v_liquidacion_anual

*Vista · 77 filas*

Liquidación anual oficial por cliente: suma de los ajustes guardados en fact_facturacion_sprint (vacía hasta ejecutar el sp del archivo 03)

| Columna | Tipo | Clave | Descripción | Ejemplo |
|---|---|---|---|---|
| `cliente_id` | text |  | Identificador del cliente | `CLI-001` |
| `cliente` | text |  | Nombre (ficticio) del cliente | `Energía Moles S.L.` |
| `nivel_contrato` | text |  | Nivel de contrato: Gold, Silver o Bronze | `Gold` |
| `anio` | smallint |  | Año de liquidación (el sprint cuenta en el año de su nombre) | `2024` |
| `sprints_facturados` | bigint |  | Sprints facturados | `18` |
| `cuota_eur` | numeric |  | Cuota facturada en el periodo (€) | `462000.06` |
| `sprints_bonus` | bigint |  | Sprints en tramo bonus | `3` |
| `sprints_deficientes` | bigint |  | Sprints en tramo deficiente | `7` |
| `bonus_eur` | numeric |  | Bonificación (€) | `2310.00` |
| `penalizacion_eur` | numeric |  | Penalización (€) | `-6288.31` |
| `balance_eur` | numeric |  | Bonus − penalización (€) | `-3978.31` |
| `pct_balance_sobre_cuota` | numeric |  | Balance sobre la cuota (%) | `-0.86` |

## v_pareto_penalizacion

*Vista · 10 filas*

Pareto de la penalización (€) por departamento que resuelve × tipo de ticket, con % acumulado y clase ABC (A = el 80 %)

| Columna | Tipo | Clave | Descripción | Ejemplo |
|---|---|---|---|---|
| `ranking` | bigint |  | Posición en el Pareto | `1` |
| `departamento` | text |  | Departamento que resuelve el ticket | `Desarrollo` |
| `tipo` | text |  | Tipo de ticket: Incidencia, Petición o Tarea | `Incidencia` |
| `tickets_incumplidos` | bigint |  | Tickets incumplidos | `114` |
| `penalizacion_eur` | numeric |  | Penalización (€) | `14752.21` |
| `pct` | numeric |  | % de la penalización total | `10.4` |
| `pct_acumulado` | numeric |  | % acumulado | `20.1` |
| `clase_abc` | text |  | Clase ABC (A = hasta el 80 %, B = hasta el 95 %, C = resto) | `A` |

## v_perfil_cliente

*Vista · 40 filas*

Un cliente por fila: volumen, % P1, % escalados, incumplimiento y € (en vivo). Entrada del clustering (pregunta 6)

| Columna | Tipo | Clave | Descripción | Ejemplo |
|---|---|---|---|---|
| `cliente_id` | text |  | Identificador del cliente | `CLI-001` |
| `cliente` | text |  | Nombre (ficticio) del cliente | `Energía Moles S.L.` |
| `sector` | text |  | Sector del cliente | `Energía` |
| `comunidad_autonoma` | text |  | Comunidad autónoma de la sede del cliente | `País Vasco` |
| `nivel_contrato` | text |  | Nivel de contrato: Gold, Silver o Bronze | `Gold` |
| `n_usuarios` | integer |  | Usuarios del cliente que pueden abrir tickets | `1387` |
| `cuota_anual_eur` | numeric(12,2) |  | Cuota anual del contrato (€) | `462000.00` |
| `fecha_alta` | date |  | Fecha de alta del contrato | `2021-11-06` |
| `meses_activo` | numeric |  | Meses con contrato activo en el periodo | `24.0` |
| `tickets` | bigint |  | Tickets | `1356` |
| `tickets_mes` | numeric |  | Tickets por mes activo | `56.4` |
| `tickets_por_100_usuarios` | numeric |  | Tickets por cada 100 usuarios | `97.8` |
| `pct_p1` | numeric |  | % de tickets P1 | `1.40` |
| `pct_escalados` | numeric |  | % de tickets escalados | `33.6` |
| `pct_incumplimiento` | numeric |  | % de incumplimiento | `5.5` |
| `sprints_medidos` | bigint |  | Sprints con tickets medidos | `35` |
| `sprints_deficientes` | bigint |  | Sprints en tramo deficiente | `12` |
| `bonus_eur` | numeric |  | Bonificación (€) | `4755.87` |
| `penalizacion_eur` | numeric |  | Penalización (€) | `-11044.21` |
| `balance_eur` | numeric |  | Bonus − penalización (€) | `-6288.34` |

## v_ticket_enriquecido

*Vista · 25.300 filas*

Un ticket por fila con SLA, cliente, departamento, agente, calendario y clima del día de creación

| Columna | Tipo | Clave | Descripción | Ejemplo |
|---|---|---|---|---|
| `ticket_id` | text |  | Identificador del ticket (TCK-NNNNNN) | `TCK-000001` |
| `fecha_creacion` | timestamp without time zone |  | Fecha y hora de apertura | `2024-01-02 08:12:00` |
| `fecha` | date |  | Fecha del día | `2024-01-02` |
| `fecha_primera_respuesta` | timestamp without time zone |  | Fecha y hora de la 1ª respuesta | `2024-01-02 10:02:00` |
| `fecha_resolucion` | timestamp without time zone |  | Fecha y hora de resolución | `2024-01-04 09:18:00` |
| `fecha_cierre` | timestamp without time zone |  | Cierre automático 3 días laborables tras resolver | `2024-01-09 09:18:00` |
| `fecha_cancelacion` | timestamp without time zone |  | Fecha y hora de cancelación (si se canceló) | `2024-01-08 11:54:00` |
| `fecha_incumplimiento` | timestamp without time zone |  | Momento en que venció el SLA de resolución (solo si incumple) | `2024-01-05 18:00:00` |
| `sla_id` | text |  | Política de SLA aplicada (tipo × prioridad) | `PET-P3` |
| `tipo` | text |  | Tipo de ticket: Incidencia, Petición o Tarea | `Petición` |
| `prioridad` | text |  | Prioridad P1 (crítica) a P4 (baja) | `P3` |
| `reloj` | text |  | Reloj del SLA: 24x7 o laboral (L–V 09–18 sin festivos de Madrid) | `laboral` |
| `objetivo_respuesta_min` | integer |  | Minutos de reloj permitidos para la 1ª respuesta | `240` |
| `objetivo_resolucion_min` | integer |  | Minutos de reloj permitidos para la resolución | `2160` |
| `cliente_id` | text |  | Identificador del cliente | `CLI-005` |
| `cliente` | text |  | Nombre (ficticio) del cliente | `Comercial Valera S.A.` |
| `sector` | text |  | Sector del cliente | `Retail` |
| `comunidad_autonoma` | text |  | Comunidad autónoma de la sede del cliente | `Comunidad de Madrid` |
| `nivel_contrato` | text |  | Nivel de contrato: Gold, Silver o Bronze | `Gold` |
| `departamento_id` | smallint |  | Identificador del departamento | `1` |
| `departamento` | text |  | Departamento que resuelve el ticket | `Service Desk N1` |
| `agente_id` | text |  | Identificador del agente | `AGT-005` |
| `agente` | text |  | Nombre (ficticio) del agente | `Telmo Antón` |
| `seniority` | text |  | Antigüedad del agente: senior o junior | `junior` |
| `estado_actual` | text |  | Último estado del ticket | `Cerrado` |
| `estado_sla` | text |  | cumplido, incumplido, en curso o cancelado | `cumplido` |
| `cumple_respuesta` | boolean |  | Cumple el SLA de 1ª respuesta | `true` |
| `cumple_resolucion` | boolean |  | Cumple el SLA de resolución | `true` |
| `computa_facturacion` | boolean |  | El ticket cuenta para la factura (no las tareas, ni cancelados ni abiertos) | `true` |
| `n_reasignaciones` | smallint |  | Veces que el ticket cambió de departamento | `0` |
| `es_escalado` | boolean |  | Tuvo al menos una reasignación | `false` |
| `min_respuesta_sla` | integer |  | Minutos de reloj hasta la 1ª respuesta | `62` |
| `min_resolucion_sla` | integer |  | Minutos de reloj consumidos hasta resolver | `1098` |
| `min_pausa` | integer |  | Minutos en pausa (esperando al cliente) | `0` |
| `horas_sla_resolucion` | numeric |  | Horas de reloj consumidas hasta resolver | `18.3` |
| `pct_sla_consumido` | numeric |  | % del SLA de resolución consumido (100 % = límite) | `65.4` |
| `sprint_apertura` | text |  | Sprint en el que se abrió | `2024-01` |
| `sprint_medicion` | text |  | Sprint en el que se mide (regla de las dos fechas) | `2024-01` |
| `fecha_medicion` | date |  | Fecha en la que se mide el ticket (resolución o vencimiento) | `2024-01-04` |
| `penalizacion_atribuida_eur` | numeric |  | Parte de la penalización del cliente × sprint atribuida al ticket (€) | `0` |
| `anio` | smallint |  | Año | `2024` |
| `trimestre` | smallint |  | Trimestre | `1` |
| `mes` | smallint |  | Mes (1–12) | `1` |
| `dia_semana` | smallint |  | Día de la semana (1 = lunes … 7 = domingo) | `2` |
| `es_laborable` | boolean |  | Día laborable en Madrid | `true` |
| `es_festivo_madrid` | boolean |  | Festivo nacional, autonómico o local de Madrid | `false` |
| `es_post_festivo` | boolean |  | Primer día laborable tras un festivo o puente | `true` |
| `es_puente` | boolean |  | Día de puente | `false` |
| `temp_max` | numeric(4,1) |  | Temperatura máxima en Madrid (°C, Open-Meteo) | `9.1` |
| `es_dia_caluroso` | boolean |  | Temperatura máxima por encima de 35 °C | `false` |
