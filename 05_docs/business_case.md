# Business case · Brújula Soporte IT

> **Empresa ficticia.** Brújula Soporte IT no representa a ninguna organización real. Los tickets,
> clientes, agentes y contratos son sintéticos; el clima y los festivos de Madrid son reales.
> Detalle de todas las decisiones en [`FICHA.md`](../FICHA.md).

## 1. La organización

**Brújula Soporte IT** es un proveedor de **service desk B2B** con sede en Madrid, fundado en 2015.
Atiende a **40 empresas cliente** (banca, seguros, retail, sanidad, energía y administración pública)
con **35 agentes** repartidos en **5 departamentos**:

| Departamento | Papel |
|---|---|
| Service Desk N1 | Recibe todos los tickets, los clasifica y resuelve la mayoría |
| Soporte Aplicaciones N2 | Incidencias de aplicaciones que N1 no puede resolver |
| Infraestructura | Servidores, red y CPD |
| Seguridad | Accesos, permisos y peticiones de seguridad |
| Desarrollo | Correcciones de software (normalmente como segundo salto desde N2) |

Los tickets son de tres tipos (**incidencia, petición y tarea**) y cuatro prioridades (**P1 a P4**).
El P1 solo existe para incidencias y su reloj corre 24x7; el resto se mide en horario laboral
(lunes a viernes de 9 a 18, sin festivos de Madrid).

## 2. El modelo de negocio: el SLA está en la factura

Cada cliente tiene un contrato con un **objetivo de cumplimiento del SLA de resolución** y una cuota
anual que se factura **por sprint** (sprints de 3 semanas):

| Nivel | Clientes | Cuota mensual de referencia | Objetivo | Si cumple de sobra | Si no llega |
|---|---|---|---|---|---|
| **Gold** | 8 | 25.000–40.000 € | ≥ 95 % | +3 % de la cuota del sprint | hasta −15 % |
| **Silver** | 14 | 8.000–20.000 € | ≥ 90 % | +2 % | hasta −10 % |
| **Bronze** | 18 | 2.000–6.000 € | ≥ 85 % | +1 % | sin penalización |

En cada sprint se calcula el % de cumplimiento del cliente (incidencias y peticiones; las tareas son
trabajo interno y no facturan), se aplica el tramo que corresponde y el ajuste se **liquida al cierre
del año**. Desde el 2026-10-20 el contrato tiene un **tope**: el ajuste de un cliente en un sprint nunca
pasa de +3 % ni de −3,5 % de su cuota.

**Por qué importa:** el ajuste no es proporcional, es un **escalón**. Pasar de un 95,1 % a un 94,9 % le
cuesta a un cliente Gold un sprint entero de penalización. Los últimos tickets antes del cierre del sprint
valen mucho más que la media.

## 3. El desafío

La dirección ve que **se pierde dinero por el SLA** y quiere saber cuánto, dónde y por qué, para actuar
antes de que el sprint se cierre y no después de recibir la liquidación.

> **Pregunta central:** ¿cuánta facturación perdemos y ganamos por el cumplimiento del SLA, y qué la
> explica: la carga, los escalados, el verano o el calendario?

## 4. Las preguntas de negocio

| # | Pregunta | Área | Acción que habilita |
|---|---|---|---|
| 1 | ¿Qué % de tickets cumple el SLA por tipo, prioridad y nivel, y qué clientes no llegan a su objetivo o están a menos de 1 punto del tramo deficiente? | Service Delivery | Plan de choque con los clientes en riesgo antes del cierre del sprint |
| 2 | ¿Cuál es el balance neto bonus − penalización y qué departamentos, tipos de ticket y clientes concentran el 80 % de la penalización? | Finanzas | Reforzar o formar donde más facturación se pierde |
| 3 | ¿Los festivos y el calor cambian el volumen de tickets y el cumplimiento? | Planificación | Turnos reforzados tras los puentes; guardia de Infraestructura en olas de calor |
| 4 | ¿Cuántos tickets entrarán el próximo trimestre y cuántos agentes harán falta en agosto? | Workforce management | Planificar las vacaciones sin caer de tramo |
| 5 | ¿Qué tickets abiertos tienen más probabilidad de incumplir y cuánta penalización evitaría resolverlos a tiempo? | Coordinación del Service Desk | Escalado preventivo de los tickets que deciden el tramo |
| 6 | ¿Qué perfiles de cliente hay según su patrón de tickets y quién no encaja en su contrato? | Account management | Renegociar contratos que no se ajustan al uso real |

Respuestas, con cifras y acciones, en [`insights_findings.md`](insights_findings.md).

## 5. La solución

```
Open-Meteo · Nager.Date · CSV manual (BOCM)        datos reales de contexto
            │
   ETL en Python ── generador sintético con semilla fija (tickets, clientes, agentes, vacaciones)
            │        reloj de SLA laboral y 24x7 · carga con upsert · verificador de integridad
            ▼
   PostgreSQL ── esquema en estrella, vistas de negocio y procedimientos de facturación por sprint
            │
     ┌──────┴──────────────┐
     ▼                     ▼
  Power BI             Jupyter (Python)
  8 páginas: KPI,      calidad, estacionalidad, Pareto, calor vs vacaciones,
  economía, riesgo     perfiles (K-Means), previsión (Prophet), riesgo (logística)
     └──────┬──────────────┘
            ▼
   Hallazgos accionables (dato → interpretación → acción)
```

| Capa | Herramientas |
|---|---|
| Extracción y generación | Python (requests, pandas, numpy) |
| Modelo de datos | PostgreSQL 16 |
| Visualización | Power BI Desktop (PBIP: TMDL + PBIR), DAX, Power Query |
| Análisis | Jupyter, SciPy, statsmodels, scikit-learn, Prophet |
| Versionado | Git y GitHub |

## 6. Resultado en una línea

En 2024–2025 Brújula facturó **10,97 M€** y perdió **68.066 €** netos por el SLA (−0,62 %). La pérdida la
explican sobre todo **las vacaciones de verano, las reasignaciones entre departamentos y los días
después de un festivo**, no el calor ni un mal servicio general, y se concentra en los clientes **Gold y
Silver**, cuyo objetivo es el más exigente.

## 7. Alcance y limitaciones

**Dentro del alcance:**
- Ciclo de vida completo del ticket (estados, reasignaciones y pausas) y cálculo del SLA de respuesta y
  resolución con el calendario laboral de Madrid.
- Bonus y penalización por cliente y sprint según su contrato, liquidados al cierre del año.
- Cruce con el clima y los festivos reales, y las 6 preguntas de negocio.
- Proceso reproducible de principio a fin: ETL → PostgreSQL → Power BI y Jupyter → documentación.

**Fuera del alcance:**
- Satisfacción del cliente (CSAT), coste por agente y nóminas.
- Integración real con Jira o ServiceNow.
- Tiempo real: la actualización es por lotes.

**Qué no se puede concluir:**
- **Los datos de negocio son sintéticos.** El generador inyecta 6 relaciones conocidas de antemano;
  el análisis demuestra que se detectan y se miden bien, **no** descubre nada sobre una empresa real.
- **El efecto senior/junior está inyectado** (los senior tardan un ~18 % menos): que salga en el modelo
  no es un hallazgo sobre el equipo.
- **La penalización por ticket es una regla de atribución** (reparto a partes iguales entre los
  incumplidos de cada cliente × sprint), no una medida directa de la responsabilidad de cada departamento.
- **Las relaciones son correlaciones**, no experimentos: por ejemplo, la carga por agente y el
  cumplimiento se relacionan en 24 meses de datos.
- **Límites de las fuentes reales:** Nager.Date no incluye los festivos locales (se completan a mano
  desde el BOCM); Open-Meteo da la celda de rejilla más cercana, no una estación; y se usa un único punto
  de clima (Madrid, donde está el CPD) para todos los clientes.
- **La previsión** tiene solo 2 años de historia y no incluye los festivos de 2026.
