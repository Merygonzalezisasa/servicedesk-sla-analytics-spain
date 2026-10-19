-- =============================================================================================
-- 04_sample_queries.sql — Consultas que responden las 6 preguntas de negocio (Ficha §4)
--
-- Cada consulta lleva arriba la pregunta que responde y debajo cómo leer el resultado. Las cifras
-- de "Lectura" son las de los datos con SEED=42 y corte 2026-01-02 18:00.
-- Las consultas de € leen la facturación oficial: antes hay que haber ejecutado
--   CALL servicedesk.sp_calcular_facturacion_anio(2024);  y  (2025);
--
-- Uso: psql -U analista -h localhost -d servicedesk_sla -P pager=off -f 02_sql/04_sample_queries.sql
--      (o pegar cada consulta por separado en el Query Tool de pgAdmin)
-- =============================================================================================

\encoding UTF8
SET search_path TO servicedesk;

-- ---------------------------------------------------------------------------------------------
-- P1a. ¿Qué % de tickets cumple el SLA de resolución por tipo, prioridad y nivel de contrato?
-- ---------------------------------------------------------------------------------------------
SELECT tipo, prioridad,
       round(100.0 * avg(cumple_resolucion::int) FILTER (WHERE nivel_contrato = 'Gold'), 1)   AS gold,
       round(100.0 * avg(cumple_resolucion::int) FILTER (WHERE nivel_contrato = 'Silver'), 1) AS silver,
       round(100.0 * avg(cumple_resolucion::int) FILTER (WHERE nivel_contrato = 'Bronze'), 1) AS bronze,
       count(*) AS tickets_medidos
FROM v_ticket_enriquecido
WHERE estado_sla IN ('cumplido', 'incumplido')
GROUP BY tipo, prioridad
ORDER BY tipo, prioridad;
-- Lectura: a igual tipo y prioridad, Gold cumple más que Silver y Silver más que Bronze
-- (correlación 5: las colas se ordenan por penalización). P1: Gold 96,5 % · Silver 89,7 % · Bronze 83,3 %.
-- Las tareas no facturan, pero se miden.

-- ---------------------------------------------------------------------------------------------
-- P1b. ¿Qué clientes quedan por debajo de su objetivo contractual en cada año?
--      Objetivo (Ficha §0.3): Gold ≥ 95 %, Silver ≥ 90 %, Bronze ≥ 85 % de tickets computables.
-- ---------------------------------------------------------------------------------------------
SELECT anio_sprint AS anio, nivel_contrato, cliente_id, cliente,
       sum(n_tickets_computables) AS tickets,
       round(100.0 * sum(n_cumplidos) / sum(n_tickets_computables), 1) AS pct_anual,
       CASE nivel_contrato WHEN 'Gold' THEN 95 WHEN 'Silver' THEN 90 ELSE 85 END AS objetivo
FROM v_cumplimiento_sprint
GROUP BY anio_sprint, nivel_contrato, cliente_id, cliente
HAVING 100.0 * sum(n_cumplidos) / sum(n_tickets_computables)
       < CASE nivel_contrato WHEN 'Gold' THEN 95 WHEN 'Silver' THEN 90 ELSE 85 END
ORDER BY anio, pct_anual;
-- Lectura: 34 cliente-año por debajo del objetivo. En 2025, 7 de los 8 Gold no llegan al 95 %:
-- el servicio "medio" de Brújula (~94 %) no alcanza lo que promete el contrato Gold.

-- ---------------------------------------------------------------------------------------------
-- P1c. ¿Cuántas veces un cliente se quedó a menos de 1 punto de caer al tramo de abajo?
--      Son los sprints en los que 1 o 2 tickets más incumplidos habrían costado dinero.
-- ---------------------------------------------------------------------------------------------
SELECT nivel_contrato,
       count(*)                                                        AS cliente_sprints,
       count(*) FILTER (WHERE puntos_sobre_tramo_inferior < 1
                          AND tipo_tramo <> 'deficiente' AND pct_cumplimiento < 100)   AS al_borde,
       round(100.0 * count(*) FILTER (WHERE puntos_sobre_tramo_inferior < 1
                          AND tipo_tramo <> 'deficiente' AND pct_cumplimiento < 100) / count(*), 1) AS pct_al_borde
FROM v_cumplimiento_sprint
GROUP BY nivel_contrato
ORDER BY 1 DESC;
-- Lectura: un Gold queda al borde en el 17,9 % de sus sprints (Silver 12,5 %): ahí un plan de choque
-- antes del cierre del sprint evita dinero. Sobre el sprint en curso, esta consulta da la lista diaria.

-- ---------------------------------------------------------------------------------------------
-- P2a. ¿Cuál es el balance neto bonus − penalización en €, por año y nivel? (facturación oficial)
-- ---------------------------------------------------------------------------------------------
SELECT anio, nivel_contrato,
       sum(cuota_eur)        AS cuota_eur,
       sum(bonus_eur)        AS bonus_eur,
       sum(penalizacion_eur) AS penalizacion_eur,
       sum(balance_eur)      AS balance_eur,
       round(100 * sum(balance_eur) / sum(cuota_eur), 2) AS pct_sobre_cuota
FROM v_liquidacion_anual
GROUP BY ROLLUP (anio, nivel_contrato)
ORDER BY anio NULLS LAST, nivel_contrato NULLS LAST;
-- Lectura: las filas con nivel vacío son el total del año; la última, el de los dos años.
-- Balance −133.003 € (2024) y −154.034 € (2025): −2,59 % de 11,08 M€ de cuota. Gold pierde el 3–3,7 %.

-- ---------------------------------------------------------------------------------------------
-- P2b. ¿Qué departamentos y tipos de ticket concentran el 80 % de la penalización?
-- ---------------------------------------------------------------------------------------------
SELECT ranking, departamento, tipo, tickets_incumplidos, penalizacion_eur, pct, pct_acumulado, clase_abc
FROM v_pareto_penalizacion
ORDER BY ranking;
-- Lectura: Service Desk N1 encabeza el importe aunque es el que mejor cumple → efecto volumen.
-- Tasa (¿quién trabaja peor?) e importe (¿dónde se va el dinero?) llevan a acciones distintas.

-- ---------------------------------------------------------------------------------------------
-- P2c. Punto ciego del % sin ponderar: ¿en cuántos sprints un cliente incumplió P1 y aun así
--      no fue penalizado? (Ficha §0.3)
-- ---------------------------------------------------------------------------------------------
SELECT nivel_contrato,
       count(*) FILTER (WHERE n_p1_incumplidos > 0)                              AS sprints_con_p1_incumplido,
       count(*) FILTER (WHERE n_p1_incumplidos > 0 AND tipo_tramo <> 'deficiente') AS sin_penalizacion,
       sum(n_p1_incumplidos) FILTER (WHERE tipo_tramo <> 'deficiente')          AS p1_incumplidos_sin_coste
FROM v_cumplimiento_sprint
GROUP BY nivel_contrato
ORDER BY 1 DESC;
-- Lectura: el punto ciego existe pero es pequeño en estos datos (los P1 son pocos y Gold los cumple
-- al 96,5 %): 1 de 8 sprints Gold y 2 de 13 Silver con P1 incumplido no costaron nada (Bronze nunca
-- penaliza). Argumento, aun así, para un indicador propio de P1: hoy un P1 pesa lo mismo que un P4.

-- ---------------------------------------------------------------------------------------------
-- P3a. ¿Los festivos cambian el volumen y el cumplimiento? (correlación 1)
-- ---------------------------------------------------------------------------------------------
SELECT CASE WHEN es_post_festivo THEN 'post-festivo'
            WHEN dia_semana = 1   THEN 'lunes normal'
            ELSE 'resto de laborables' END                          AS tipo_dia,
       count(*)                                                     AS dias,
       round(avg(tickets_creados), 1)                               AS tickets_dia,
       round(100.0 * sum(cumplidos) / nullif(sum(cumplidos + incumplidos), 0), 1) AS pct_cumplimiento
FROM v_kpis_diarios
WHERE es_laborable
GROUP BY 1
ORDER BY tickets_dia DESC;
-- Lectura: post-festivo 67,8 tickets/día vs 55,5 un lunes normal (la comparación justa: los lunes ya
-- traen la cola del fin de semana) y 48,1 el resto; el cumplimiento cae a 89,1 % (vs 92 %).

-- ---------------------------------------------------------------------------------------------
-- P3b. ¿El calor sube las incidencias graves de Infraestructura? Comparando DENTRO de julio y
--      agosto, para separar el calor de las vacaciones (confusión deliberada, Ficha §2.3).
-- ---------------------------------------------------------------------------------------------
SELECT CASE WHEN es_dia_caluroso THEN '> 35 °C' ELSE '≤ 35 °C' END AS dia,
       count(*)                                  AS dias,
       round(avg(infra_p1_p2_creados), 2)        AS infra_p1_p2_por_dia,
       round(avg(tickets_creados), 1)            AS tickets_por_dia,
       round(avg(pct_agentes_ausentes), 1)       AS pct_agentes_ausentes
FROM v_kpis_diarios
WHERE mes IN (7, 8)
GROUP BY 1;
-- Lectura: con ausencias casi iguales (17,8 % vs 17,0 %), los días > 35 °C tienen 0,91 incidencias
-- P1/P2 de Infraestructura frente a 0,39: el efecto es del calor, no de las vacaciones.

-- ---------------------------------------------------------------------------------------------
-- P4. ¿Cuántos tickets entran por trimestre y cuánta plantilla hay disponible cada mes?
--     Base del forecast (Fase 4) y de la planificación de vacaciones de agosto.
-- ---------------------------------------------------------------------------------------------
SELECT anio, mes,
       sum(tickets_creados)                                        AS tickets,
       round(avg(agentes_activos - agentes_ausentes) FILTER (WHERE es_laborable), 1) AS agentes_disponibles,
       round(sum(tickets_creados)::numeric
             / nullif(sum(agentes_activos - agentes_ausentes) FILTER (WHERE es_laborable), 0), 2)
                                                                   AS tickets_por_agente_dia,
       round(100.0 * sum(cumplidos) / nullif(sum(cumplidos + incumplidos), 0), 1) AS pct_cumplimiento
FROM v_kpis_diarios
WHERE fecha < DATE '2026-01-01'
GROUP BY anio, mes
ORDER BY anio, mes;
-- Lectura: en agosto baja el volumen, pero baja más la plantilla (~22–25 agentes de ~33) → ~2 tickets
-- por agente y día y el cumplimiento cae al 79–83 % (correlación 6). Cifra a vigilar al aprobar vacaciones.

-- ---------------------------------------------------------------------------------------------
-- P5. ¿Qué tickets abiertos al corte tienen más riesgo de incumplir?
--     Regla simple (el modelo de regresión llega en la Fase 4): % del SLA ya consumido, y P1/Gold
--     primero porque son los que más pesan en la cola y en la factura.
-- ---------------------------------------------------------------------------------------------
SELECT ticket_id, cliente, nivel_contrato, tipo, prioridad, departamento, estado_actual,
       n_reasignaciones, pct_sla_consumido
FROM v_ticket_enriquecido
WHERE estado_sla = 'en curso'
ORDER BY pct_sla_consumido DESC, (prioridad = 'P1') DESC, (nivel_contrato = 'Gold') DESC
LIMIT 15;
-- Lectura: los primeros de la lista ya han gastado casi todo su plazo: escalado preventivo hoy.

-- ---------------------------------------------------------------------------------------------
-- P6. ¿Qué perfiles de cliente hay según su patrón de tickets? (anticipo del clustering)
--     Segmentación simple por cuartiles de volumen mensual y de incumplimiento.
-- ---------------------------------------------------------------------------------------------
WITH q AS (
    SELECT *,
           ntile(4) OVER (ORDER BY tickets_mes)        AS q_volumen,
           ntile(4) OVER (ORDER BY pct_incumplimiento) AS q_incumplimiento
    FROM v_perfil_cliente
)
SELECT CASE WHEN q_volumen >= 3 AND q_incumplimiento >= 3 THEN '1. Mucho volumen y mucho incumplimiento'
            WHEN q_volumen >= 3                       THEN '2. Mucho volumen, buen servicio'
            WHEN q_incumplimiento >= 3                THEN '3. Poco volumen, mal servicio'
            ELSE '4. Poco volumen, buen servicio' END  AS perfil,
       count(*)                                         AS clientes,
       string_agg(DISTINCT nivel_contrato, ', ')        AS niveles,
       round(avg(tickets_mes), 1)                       AS tickets_mes,
       round(avg(pct_p1), 2)                            AS pct_p1,
       round(avg(pct_escalados), 1)                     AS pct_escalados,
       round(avg(pct_incumplimiento), 1)                AS pct_incumplimiento,
       round(sum(balance_eur))                          AS balance_eur
FROM q
GROUP BY 1
ORDER BY 1;
-- Lectura: el dinero está en el perfil 2 (−242.925 €): los Gold dan "buen servicio" comparados con el
-- resto, pero su cuota es tan grande y su objetivo (95 %) tan alto que pierden igual. El 3 son
-- Bronze pequeños con % inestable y sin penalización. El clustering de la Fase 4 afinará los grupos.
