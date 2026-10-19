-- =============================================================================================
-- 02_create_views.sql — Vistas del modelo "servicedesk" (las que leen Power BI y el notebook)
--
-- Una vista es una consulta guardada con nombre: se lee como una tabla, pero siempre calcula sobre
-- los datos actuales. Las 4 canónicas de la plantilla, adaptadas al service desk, más 2 de facturación:
--
--   v_ticket_enriquecido   el hecho unido a todas sus dimensiones + contexto del día   (base)
--   v_kpis_diarios         un día por fila: volumen, backlog, cumplimiento y contexto (P3, P4)
--   v_cumplimiento_sprint  cliente × sprint: %, tramo y € calculados EN VIVO           (P1, P2)
--   v_liquidacion_anual    cliente × año: liquidación OFICIAL (fact_facturacion_sprint) (P2)
--   v_pareto_penalizacion  qué departamento × tipo concentra la penalización (80/20)   (P2)
--   v_perfil_cliente       perfil de tickets de cada cliente, para los clusters        (P6)
--
-- En vivo vs oficial: v_cumplimiento_sprint recalcula con cada consulta (un sprint abierto cambia
-- cada día). fact_facturacion_sprint guarda lo facturado al cerrar el sprint (sp del archivo 03) y
-- no cambia aunque cambien los datos: es lo que se liquida al cliente.
--
-- Uso: psql -U analista -h localhost -d servicedesk_sla -f 02_sql/02_create_views.sql
-- =============================================================================================

\set ON_ERROR_STOP on
\encoding UTF8
SET search_path TO servicedesk;
SET client_min_messages = warning;  -- sin avisos de "la vista no existe" en la primera ejecución

DROP VIEW IF EXISTS v_ticket_enriquecido, v_kpis_diarios, v_cumplimiento_sprint, v_liquidacion_anual,
                    v_pareto_penalizacion, v_perfil_cliente, v_facturacion_sprint CASCADE;

-- ---------------------------------------------------------------------------------------------
-- 1. v_ticket_enriquecido — un ticket por fila con todo su contexto
-- ---------------------------------------------------------------------------------------------
CREATE VIEW v_ticket_enriquecido AS
SELECT t.ticket_id,
       t.fecha_creacion,
       t.fecha_creacion::date                                   AS fecha,
       t.fecha_primera_respuesta, t.fecha_resolucion, t.fecha_cierre, t.fecha_cancelacion,
       t.fecha_incumplimiento,
       -- qué
       s.sla_id, s.tipo, s.prioridad, s.reloj,
       s.objetivo_respuesta_min, s.objetivo_resolucion_min,
       -- quién
       c.cliente_id, c.nombre AS cliente, c.sector, c.comunidad_autonoma, c.nivel_contrato,
       d.departamento_id, d.nombre AS departamento,
       a.agente_id, a.nombre AS agente, a.seniority,
       -- estado y medición
       t.estado_actual, t.estado_sla, t.cumple_respuesta, t.cumple_resolucion, t.computa_facturacion,
       t.n_reasignaciones, t.n_reasignaciones > 0                AS es_escalado,
       t.min_respuesta_sla, t.min_resolucion_sla, t.min_pausa,
       round(t.min_resolucion_sla / 60.0, 1)                     AS horas_sla_resolucion,
       round(100.0 * t.min_resolucion_sla / s.objetivo_resolucion_min, 1) AS pct_sla_consumido,
       t.sprint_apertura, t.sprint_medicion,
       -- día en que se conoce el resultado (regla de las dos fechas): resolución si cumple,
       -- vencimiento si incumple. Su sprint es sprint_medicion. NULL si está en curso o cancelado.
       CASE t.estado_sla WHEN 'cumplido'   THEN t.fecha_resolucion::date
                         WHEN 'incumplido' THEN t.fecha_incumplimiento::date END AS fecha_medicion,
       -- penalización oficial del cliente-sprint repartida a partes iguales entre sus incumplidos
       coalesce(pen.penalizacion_atribuida_eur, 0)               AS penalizacion_atribuida_eur,
       -- cuándo y contexto del día de creación
       ti.anio, ti.trimestre, ti.mes, ti.dia_semana, ti.es_laborable,
       ti.es_festivo_madrid, ti.es_post_festivo, ti.es_puente,
       cl.temp_max, cl.es_dia_caluroso
FROM fact_ticket t
JOIN dim_sla s          USING (sla_id)
JOIN dim_cliente c      USING (cliente_id)
JOIN dim_departamento d USING (departamento_id)
LEFT JOIN dim_agente a  USING (agente_id)
JOIN dim_tiempo ti      ON ti.fecha = t.fecha_creacion::date
JOIN dim_clima_madrid cl ON cl.fecha = t.fecha_creacion::date
LEFT JOIN (
    SELECT t2.ticket_id,
           -f.ajuste_eur / count(*) OVER (PARTITION BY t2.cliente_id, t2.sprint_medicion) AS penalizacion_atribuida_eur
    FROM fact_ticket t2
    JOIN fact_facturacion_sprint f ON f.cliente_id = t2.cliente_id AND f.sprint_id = t2.sprint_medicion
    WHERE t2.computa_facturacion AND t2.estado_sla = 'incumplido' AND f.tipo_tramo = 'deficiente'
) pen USING (ticket_id);

COMMENT ON VIEW v_ticket_enriquecido IS 'Un ticket por fila con SLA, cliente, departamento, agente, calendario y clima del día de creación';

-- ---------------------------------------------------------------------------------------------
-- 2. v_kpis_diarios — un día por fila
-- ---------------------------------------------------------------------------------------------
CREATE VIEW v_kpis_diarios AS
WITH creados AS (
    SELECT t.fecha_creacion::date AS fecha,
           count(*)                                                        AS tickets_creados,
           count(*) FILTER (WHERE s.prioridad = 'P1')                       AS p1_creados,
           count(*) FILTER (WHERE s.tipo = 'Incidencia' AND s.prioridad IN ('P1', 'P2')
                              AND t.departamento_id = 3)                   AS infra_p1_p2_creados
    FROM fact_ticket t JOIN dim_sla s USING (sla_id)
    GROUP BY 1
), salidas AS (                     -- tickets que dejan de estar abiertos: resueltos o cancelados
    SELECT coalesce(fecha_resolucion, fecha_cancelacion)::date AS fecha, count(*) AS tickets_salida
    FROM fact_ticket
    WHERE coalesce(fecha_resolucion, fecha_cancelacion) IS NOT NULL
    GROUP BY 1
), medidos AS (                     -- regla de las dos fechas: el día en que se conoce el resultado
    SELECT CASE estado_sla WHEN 'cumplido' THEN fecha_resolucion ELSE fecha_incumplimiento END::date AS fecha,
           count(*) FILTER (WHERE estado_sla = 'cumplido')   AS cumplidos,
           count(*) FILTER (WHERE estado_sla = 'incumplido') AS incumplidos
    FROM fact_ticket
    WHERE estado_sla IN ('cumplido', 'incumplido')
    GROUP BY 1
), ausentes AS (
    SELECT ti.fecha, count(DISTINCT au.agente_id) AS agentes_ausentes
    FROM dim_tiempo ti
    JOIN agente_ausencia au ON ti.fecha BETWEEN au.fecha_inicio AND au.fecha_fin
    WHERE ti.es_laborable
    GROUP BY 1
)
SELECT ti.fecha, ti.anio, ti.mes, ti.dia_semana, ti.sprint_id,
       ti.es_laborable, ti.es_festivo_madrid, ti.nombre_festivo, ti.es_post_festivo, ti.es_puente,
       cl.temp_max, cl.precipitacion_mm, cl.es_dia_caluroso,
       coalesce(cr.tickets_creados, 0)      AS tickets_creados,
       coalesce(cr.p1_creados, 0)           AS p1_creados,
       coalesce(cr.infra_p1_p2_creados, 0)  AS infra_p1_p2_creados,
       coalesce(sa.tickets_salida, 0)       AS tickets_salida,
       -- backlog al final del día = todo lo que entró hasta hoy − todo lo que salió hasta hoy
       sum(coalesce(cr.tickets_creados, 0)) OVER w - sum(coalesce(sa.tickets_salida, 0)) OVER w AS backlog_fin_dia,
       coalesce(me.cumplidos, 0)            AS cumplidos,
       coalesce(me.incumplidos, 0)          AS incumplidos,
       round(100.0 * me.cumplidos / nullif(me.cumplidos + me.incumplidos, 0), 1) AS pct_cumplimiento,
       (SELECT count(*) FROM dim_agente ag WHERE ag.fecha_alta <= ti.fecha)        AS agentes_activos,
       coalesce(au.agentes_ausentes, 0)     AS agentes_ausentes,
       round(100.0 * coalesce(au.agentes_ausentes, 0)
             / (SELECT count(*) FROM dim_agente ag WHERE ag.fecha_alta <= ti.fecha), 1) AS pct_agentes_ausentes
FROM dim_tiempo ti
JOIN dim_clima_madrid cl USING (fecha)
LEFT JOIN creados cr  USING (fecha)
LEFT JOIN salidas sa  USING (fecha)
LEFT JOIN medidos me  USING (fecha)
LEFT JOIN ausentes au USING (fecha)
WINDOW w AS (ORDER BY ti.fecha);

COMMENT ON VIEW v_kpis_diarios IS 'Un día por fila: entradas, salidas, backlog, cumplimiento (por día de medición), festivos, clima y ausencias';
COMMENT ON COLUMN v_kpis_diarios.backlog_fin_dia IS 'Tickets abiertos al final del día (entradas acumuladas − resueltos/cancelados acumulados)';

-- ---------------------------------------------------------------------------------------------
-- 3. v_cumplimiento_sprint — cliente × sprint, en vivo (Ficha §0.3 y §0.4)
-- ---------------------------------------------------------------------------------------------
CREATE VIEW v_cumplimiento_sprint AS
WITH base AS (
    SELECT t.cliente_id, t.sprint_medicion AS sprint_id,
           count(*)                                                      AS n_tickets_computables,
           count(*) FILTER (WHERE t.cumple_resolucion)                    AS n_cumplidos,
           count(*) FILTER (WHERE s.prioridad = 'P1')                     AS n_p1,
           count(*) FILTER (WHERE s.prioridad = 'P1' AND NOT t.cumple_resolucion) AS n_p1_incumplidos
    FROM fact_ticket t JOIN dim_sla s USING (sla_id)
    WHERE t.computa_facturacion
    GROUP BY 1, 2
)
SELECT b.cliente_id, c.nombre AS cliente, c.nivel_contrato,
       b.sprint_id, sp.anio_sprint, sp.fecha_inicio, sp.fecha_fin,
       round(c.cuota_anual_eur / sp.n_sprints_anio, 2)                    AS cuota_sprint_eur,
       b.n_tickets_computables, b.n_cumplidos,
       b.n_tickets_computables - b.n_cumplidos                            AS n_incumplidos,
       b.n_p1, b.n_p1_incumplidos,
       round(100.0 * b.n_cumplidos / b.n_tickets_computables, 2)          AS pct_cumplimiento,
       tr.tramo_id, tr.tipo AS tipo_tramo, tr.pct_ajuste,
       round(c.cuota_anual_eur / sp.n_sprints_anio * tr.pct_ajuste / 100, 2) AS ajuste_eur,
       -- margen hasta caer al tramo inferior (pregunta 1: clientes a menos de 1 punto)
       round(100.0 * b.n_cumplidos / b.n_tickets_computables - tr.pct_desde, 2) AS puntos_sobre_tramo_inferior
FROM base b
JOIN dim_cliente c       USING (cliente_id)
JOIN dim_sprint sp       USING (sprint_id)
JOIN dim_tramo_ajuste tr ON tr.nivel_contrato = c.nivel_contrato
                        AND 100.0 * b.n_cumplidos / b.n_tickets_computables >= tr.pct_desde
                        AND 100.0 * b.n_cumplidos / b.n_tickets_computables <  tr.pct_hasta;

COMMENT ON VIEW v_cumplimiento_sprint IS 'Cliente × sprint calculado en vivo: % de cumplimiento, tramo y ajuste en €. Lo oficial se guarda en fact_facturacion_sprint';
COMMENT ON COLUMN v_cumplimiento_sprint.puntos_sobre_tramo_inferior IS 'Puntos de % que le sobran al cliente antes de caer al tramo de abajo';

-- ---------------------------------------------------------------------------------------------
-- 4. v_liquidacion_anual — lo que se liquida al cliente al cierre del año (oficial)
-- ---------------------------------------------------------------------------------------------
CREATE VIEW v_liquidacion_anual AS
SELECT f.cliente_id, c.nombre AS cliente, c.nivel_contrato, sp.anio_sprint AS anio,
       count(*)                                                        AS sprints_facturados,
       sum(f.cuota_sprint_eur)                                         AS cuota_eur,
       count(*) FILTER (WHERE f.tipo_tramo = 'bonus')                  AS sprints_bonus,
       count(*) FILTER (WHERE f.tipo_tramo = 'deficiente')             AS sprints_deficientes,
       coalesce(sum(f.ajuste_eur) FILTER (WHERE f.ajuste_eur > 0), 0)  AS bonus_eur,
       coalesce(sum(f.ajuste_eur) FILTER (WHERE f.ajuste_eur < 0), 0)  AS penalizacion_eur,
       sum(f.ajuste_eur)                                               AS balance_eur,
       round(100 * sum(f.ajuste_eur) / sum(f.cuota_sprint_eur), 2)     AS pct_balance_sobre_cuota
FROM fact_facturacion_sprint f
JOIN dim_cliente c USING (cliente_id)
JOIN dim_sprint sp USING (sprint_id)
GROUP BY f.cliente_id, c.nombre, c.nivel_contrato, sp.anio_sprint;

COMMENT ON VIEW v_liquidacion_anual IS 'Liquidación anual oficial por cliente: suma de los ajustes guardados en fact_facturacion_sprint (vacía hasta ejecutar el sp del archivo 03)';

-- ---------------------------------------------------------------------------------------------
-- 5. v_pareto_penalizacion — ¿qué departamento × tipo concentra el 80 % de la penalización?
--    La penalización de un cliente en un sprint se reparte a partes iguales entre sus tickets
--    incumplidos de ese sprint (Ficha §0.3), y cada ticket la lleva a su departamento y tipo.
-- ---------------------------------------------------------------------------------------------
CREATE VIEW v_pareto_penalizacion AS
WITH reparto AS (
    SELECT t.departamento_id, s.tipo,
           -cs.ajuste_eur / count(*) OVER (PARTITION BY t.cliente_id, t.sprint_medicion) AS penalizacion_eur
    FROM fact_ticket t
    JOIN dim_sla s USING (sla_id)
    JOIN v_cumplimiento_sprint cs ON cs.cliente_id = t.cliente_id AND cs.sprint_id = t.sprint_medicion
    WHERE t.computa_facturacion AND t.estado_sla = 'incumplido' AND cs.tipo_tramo = 'deficiente'
), grupos AS (
    SELECT d.nombre AS departamento, r.tipo,
           count(*)                          AS tickets_incumplidos,
           round(sum(r.penalizacion_eur), 2) AS penalizacion_eur
    FROM reparto r JOIN dim_departamento d USING (departamento_id)
    GROUP BY 1, 2
)
SELECT row_number() OVER (ORDER BY penalizacion_eur DESC)                            AS ranking,
       departamento, tipo, tickets_incumplidos, penalizacion_eur,
       round(100 * penalizacion_eur / sum(penalizacion_eur) OVER (), 1)              AS pct,
       round(100 * sum(penalizacion_eur) OVER (ORDER BY penalizacion_eur DESC)
                 / sum(penalizacion_eur) OVER (), 1)                                 AS pct_acumulado,
       CASE WHEN sum(penalizacion_eur) OVER (ORDER BY penalizacion_eur DESC) - penalizacion_eur
                 < 0.80 * sum(penalizacion_eur) OVER () THEN 'A'
            WHEN sum(penalizacion_eur) OVER (ORDER BY penalizacion_eur DESC) - penalizacion_eur
                 < 0.95 * sum(penalizacion_eur) OVER () THEN 'B'
            ELSE 'C' END                                                             AS clase_abc
FROM grupos;

COMMENT ON VIEW v_pareto_penalizacion IS 'Pareto de la penalización (€) por departamento que resuelve × tipo de ticket, con % acumulado y clase ABC (A = el 80 %)';

-- ---------------------------------------------------------------------------------------------
-- 5b. v_facturacion_sprint — la facturación oficial con el margen sobre el tramo inferior
--     (Power BI: "ingresos en riesgo" = cuota de los cliente-sprints con < 1 punto de margen)
-- ---------------------------------------------------------------------------------------------
CREATE VIEW v_facturacion_sprint AS
SELECT f.cliente_id, f.sprint_id, f.nivel_contrato, f.cuota_sprint_eur,
       f.n_tickets_computables, f.n_cumplidos, f.pct_cumplimiento,
       f.tipo_tramo, f.pct_ajuste, f.ajuste_eur,
       round(f.pct_cumplimiento - tr.pct_desde, 2)                   AS puntos_sobre_tramo_inferior,
       CASE f.nivel_contrato WHEN 'Gold' THEN 95 WHEN 'Silver' THEN 90 ELSE 85 END AS objetivo_contractual
FROM fact_facturacion_sprint f
LEFT JOIN dim_tramo_ajuste tr USING (tramo_id);

COMMENT ON VIEW v_facturacion_sprint IS 'fact_facturacion_sprint + margen sobre el tramo inferior y objetivo contractual (vacía hasta ejecutar el sp del archivo 03)';

-- ---------------------------------------------------------------------------------------------
-- 6. v_perfil_cliente — patrón de tickets de cada cliente (para el clustering de la Fase 4)
-- ---------------------------------------------------------------------------------------------
CREATE VIEW v_perfil_cliente AS
WITH tickets AS (
    SELECT t.cliente_id,
           count(*)                                                          AS tickets,
           count(*) FILTER (WHERE s.prioridad = 'P1')                         AS tickets_p1,
           count(*) FILTER (WHERE t.n_reasignaciones > 0)                     AS tickets_escalados,
           count(*) FILTER (WHERE t.estado_sla = 'incumplido')                AS incumplidos,
           count(*) FILTER (WHERE t.estado_sla IN ('cumplido', 'incumplido')) AS medidos
    FROM fact_ticket t JOIN dim_sla s USING (sla_id)
    GROUP BY 1
), dinero AS (
    SELECT cliente_id,
           coalesce(sum(ajuste_eur) FILTER (WHERE ajuste_eur < 0), 0) AS penalizacion_eur,
           coalesce(sum(ajuste_eur) FILTER (WHERE ajuste_eur > 0), 0) AS bonus_eur,
           count(*) FILTER (WHERE tipo_tramo = 'deficiente')           AS sprints_deficientes,
           count(*)                                                    AS sprints_medidos
    FROM v_cumplimiento_sprint
    GROUP BY 1
)
SELECT c.cliente_id, c.nombre AS cliente, c.sector, c.comunidad_autonoma, c.nivel_contrato,
       c.n_usuarios, c.cuota_anual_eur, c.fecha_alta,
       -- meses con contrato dentro del período (los clientes nuevos llevan menos tiempo)
       round((DATE '2026-01-02' - greatest(c.fecha_alta, DATE '2024-01-01')) / 30.44, 1) AS meses_activo,
       tk.tickets,
       round(tk.tickets / ((DATE '2026-01-02' - greatest(c.fecha_alta, DATE '2024-01-01')) / 30.44), 1)
                                                                    AS tickets_mes,
       round(100.0 * tk.tickets / c.n_usuarios, 1)                  AS tickets_por_100_usuarios,
       round(100.0 * tk.tickets_p1 / tk.tickets, 2)                 AS pct_p1,
       round(100.0 * tk.tickets_escalados / tk.tickets, 1)          AS pct_escalados,
       round(100.0 * tk.incumplidos / nullif(tk.medidos, 0), 1)     AS pct_incumplimiento,
       coalesce(di.sprints_medidos, 0)                              AS sprints_medidos,
       coalesce(di.sprints_deficientes, 0)                          AS sprints_deficientes,
       coalesce(di.bonus_eur, 0)                                    AS bonus_eur,
       coalesce(di.penalizacion_eur, 0)                             AS penalizacion_eur,
       coalesce(di.bonus_eur, 0) + coalesce(di.penalizacion_eur, 0) AS balance_eur
FROM dim_cliente c
JOIN tickets tk    USING (cliente_id)
LEFT JOIN dinero di USING (cliente_id);

COMMENT ON VIEW v_perfil_cliente IS 'Un cliente por fila: volumen, % P1, % escalados, incumplimiento y € (en vivo). Entrada del clustering (pregunta 6)';

-- ---------------------------------------------------------------------------------------------
-- Comprobación rápida: filas de cada vista
-- ---------------------------------------------------------------------------------------------
SELECT 'v_ticket_enriquecido' AS vista, count(*) AS filas FROM v_ticket_enriquecido
UNION ALL SELECT 'v_kpis_diarios',        count(*) FROM v_kpis_diarios
UNION ALL SELECT 'v_cumplimiento_sprint', count(*) FROM v_cumplimiento_sprint
UNION ALL SELECT 'v_liquidacion_anual',   count(*) FROM v_liquidacion_anual
UNION ALL SELECT 'v_pareto_penalizacion', count(*) FROM v_pareto_penalizacion
UNION ALL SELECT 'v_perfil_cliente',      count(*) FROM v_perfil_cliente
UNION ALL SELECT 'v_facturacion_sprint',  count(*) FROM v_facturacion_sprint;
