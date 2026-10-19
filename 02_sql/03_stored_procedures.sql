-- =============================================================================================
-- 03_stored_procedures.sql — Automatización dentro de la base: facturación, reporte y contexto
--
--   sp_calcular_facturacion_sprint(sprint, forzar)  calcula y guarda como OFICIAL un sprint
--   sp_calcular_facturacion_anio(año, forzar)       factura todos los sprints de un año
--   fn_reporte_sprint(sprint)                       resumen ejecutivo del sprint (tabla de indicadores)
--   sp_refrescar_contexto()                         actualiza el clima del modelo desde raw
--
-- Un procedimiento (CALL) hace cambios; una función (SELECT) devuelve un resultado. El reporte es
-- una función porque devuelve filas que se pueden leer, filtrar o pegar en un informe.
--
-- Cada rutina fija su propio search_path: encuentra las tablas de "servicedesk" aunque se llame
-- desde pgAdmin o Power BI (que buscan en "public"), y no puede usar por error una tabla homónima.
--
-- Uso: psql -U analista -h localhost -d servicedesk_sla -f 02_sql/03_stored_procedures.sql
--      y después, por ejemplo:  CALL servicedesk.sp_calcular_facturacion_anio(2024);
-- =============================================================================================

\set ON_ERROR_STOP on
\encoding UTF8
SET search_path TO servicedesk;

-- ---------------------------------------------------------------------------------------------
-- 1. Facturación oficial de un sprint
--    Toma el cálculo en vivo (v_cumplimiento_sprint) y lo congela en fact_facturacion_sprint.
--    Lo facturado no se recalcula por accidente: si el sprint ya está, hace falta p_forzar => true.
-- ---------------------------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sp_calcular_facturacion_sprint(p_sprint text, p_forzar boolean DEFAULT false)
LANGUAGE plpgsql
SET search_path = servicedesk, public
AS $$
DECLARE
    v_sprint      dim_sprint%ROWTYPE;
    v_existentes  integer;
    v_clientes    integer;
    v_bonus       numeric;
    v_penal       numeric;
BEGIN
    SELECT * INTO v_sprint FROM dim_sprint WHERE sprint_id = p_sprint;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'El sprint % no existe en dim_sprint', p_sprint;
    END IF;
    IF NOT v_sprint.es_completo THEN
        RAISE EXCEPTION 'El sprint % no está completo (los datos no cubren hasta su viernes de cierre)', p_sprint;
    END IF;

    SELECT count(*) INTO v_existentes FROM fact_facturacion_sprint WHERE sprint_id = p_sprint;
    IF v_existentes > 0 AND NOT p_forzar THEN
        RAISE NOTICE 'Sprint % ya facturado (% clientes): no se recalcula. Para rehacerlo: p_forzar => true',
                     p_sprint, v_existentes;
        RETURN;
    END IF;

    DELETE FROM fact_facturacion_sprint WHERE sprint_id = p_sprint;

    -- Todos los clientes con contrato en el sprint pagan su cuota. Si no tuvieron tickets
    -- computables, no hay % que medir: tramo neutro y ajuste 0.
    INSERT INTO fact_facturacion_sprint
        (cliente_id, sprint_id, nivel_contrato, cuota_sprint_eur, n_tickets_computables, n_cumplidos,
         pct_cumplimiento, tramo_id, tipo_tramo, pct_ajuste, ajuste_eur)
    SELECT c.cliente_id, p_sprint, c.nivel_contrato,
           round(c.cuota_anual_eur / v_sprint.n_sprints_anio, 2),
           coalesce(v.n_tickets_computables, 0), coalesce(v.n_cumplidos, 0),
           v.pct_cumplimiento, v.tramo_id,
           coalesce(v.tipo_tramo, 'neutro'), coalesce(v.pct_ajuste, 0), coalesce(v.ajuste_eur, 0)
    FROM dim_cliente c
    LEFT JOIN v_cumplimiento_sprint v ON v.cliente_id = c.cliente_id AND v.sprint_id = p_sprint
    WHERE c.fecha_alta <= v_sprint.fecha_fin;

    SELECT count(*), coalesce(sum(ajuste_eur) FILTER (WHERE ajuste_eur > 0), 0),
           coalesce(sum(ajuste_eur) FILTER (WHERE ajuste_eur < 0), 0)
    INTO v_clientes, v_bonus, v_penal
    FROM fact_facturacion_sprint WHERE sprint_id = p_sprint;

    RAISE NOTICE 'Sprint %: % clientes facturados · bonus % € · penalización % € · balance % €',
                 p_sprint, v_clientes, to_char(v_bonus, 'FM999G999G990D00'),
                 to_char(v_penal, 'FM999G999G990D00'), to_char(v_bonus + v_penal, 'FM999G999G990D00');
END $$;

COMMENT ON PROCEDURE sp_calcular_facturacion_sprint(text, boolean) IS
    'Congela en fact_facturacion_sprint la facturación de un sprint (cuota, %, tramo, €). No rehace un sprint ya facturado salvo p_forzar => true';

-- ---------------------------------------------------------------------------------------------
-- 2. Facturar un año entero (carga inicial o re-proceso)
-- ---------------------------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sp_calcular_facturacion_anio(p_anio integer, p_forzar boolean DEFAULT false)
LANGUAGE plpgsql
SET search_path = servicedesk, public
AS $$
DECLARE
    r record;
    v_n integer := 0;
BEGIN
    FOR r IN SELECT sprint_id FROM dim_sprint WHERE anio_sprint = p_anio AND es_completo ORDER BY numero LOOP
        CALL sp_calcular_facturacion_sprint(r.sprint_id, p_forzar);
        v_n := v_n + 1;
    END LOOP;
    IF v_n = 0 THEN
        RAISE EXCEPTION 'No hay sprints completos del año %', p_anio;
    END IF;
    RAISE NOTICE 'Año %: % sprints procesados. Resultado en v_liquidacion_anual', p_anio, v_n;
END $$;

COMMENT ON PROCEDURE sp_calcular_facturacion_anio(integer, boolean) IS
    'Llama a sp_calcular_facturacion_sprint para cada sprint completo del año';

-- ---------------------------------------------------------------------------------------------
-- 3. Reporte ejecutivo de un sprint (para la reunión de cierre)
--    Si el sprint está facturado, los € salen de lo oficial; si no, del cálculo en vivo.
-- ---------------------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_reporte_sprint(p_sprint text)
RETURNS TABLE (orden integer, indicador text, valor text)
LANGUAGE plpgsql STABLE
SET search_path = servicedesk, public
AS $$
DECLARE
    v_sprint   dim_sprint%ROWTYPE;
    v_oficial  boolean;
    f          text := 'FM999G999G990D00';
BEGIN
    SELECT * INTO v_sprint FROM dim_sprint WHERE sprint_id = p_sprint;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'El sprint % no existe en dim_sprint', p_sprint;
    END IF;
    v_oficial := EXISTS (SELECT 1 FROM fact_facturacion_sprint WHERE sprint_id = p_sprint);

    RETURN QUERY
    WITH fac AS (   -- cliente × sprint: oficial si existe, si no en vivo
        SELECT cliente_id, nivel_contrato, n_tickets_computables, n_cumplidos, tipo_tramo, ajuste_eur
        FROM fact_facturacion_sprint WHERE sprint_id = p_sprint AND v_oficial
        UNION ALL
        SELECT cliente_id, nivel_contrato, n_tickets_computables, n_cumplidos, tipo_tramo, ajuste_eur
        FROM v_cumplimiento_sprint WHERE sprint_id = p_sprint AND NOT v_oficial
    ), niveles AS (
        SELECT string_agg(nivel_contrato || ' ' || to_char(100.0 * sum_ok / sum_n, 'FM990D0') || ' %', ' · '
                          ORDER BY CASE nivel_contrato WHEN 'Gold' THEN 1 WHEN 'Silver' THEN 2 ELSE 3 END) AS txt
        FROM (SELECT nivel_contrato, sum(n_cumplidos) AS sum_ok, sum(n_tickets_computables) AS sum_n
              FROM fac GROUP BY 1 HAVING sum(n_tickets_computables) > 0) x
    ), deps AS (
        SELECT departamento, round(100.0 * avg(cumple_resolucion::int), 1) AS pct, count(*) AS n
        FROM v_ticket_enriquecido
        WHERE sprint_medicion = p_sprint AND computa_facturacion
        GROUP BY 1
    )
    SELECT 1, 'Sprint', p_sprint || ' (' || to_char(v_sprint.fecha_inicio, 'DD-MM-YY') || ' → '
                        || to_char(v_sprint.fecha_fin, 'DD-MM-YY') || ', ' || v_sprint.dias_laborables
                        || ' días laborables)'
    UNION ALL
    SELECT 2, 'Tickets que entraron', count(*)::text FROM fact_ticket WHERE sprint_apertura = p_sprint
    UNION ALL
    SELECT 3, 'Tickets medidos para factura', sum(n_tickets_computables)::text
              || ' (' || (sum(n_tickets_computables) - sum(n_cumplidos)) || ' incumplidos)' FROM fac
    UNION ALL
    SELECT 4, '% de cumplimiento global',
              to_char(100.0 * sum(n_cumplidos) / nullif(sum(n_tickets_computables), 0), 'FM990D0') || ' %' FROM fac
    UNION ALL
    SELECT 5, '% de cumplimiento por nivel', txt FROM niveles
    UNION ALL
    SELECT 6, 'Clientes bonus / neutro / deficiente',
              count(*) FILTER (WHERE tipo_tramo = 'bonus') || ' / ' || count(*) FILTER (WHERE tipo_tramo = 'neutro')
              || ' / ' || count(*) FILTER (WHERE tipo_tramo = 'deficiente') FROM fac
    UNION ALL
    SELECT 7, 'Bonus €', to_char(coalesce(sum(ajuste_eur) FILTER (WHERE ajuste_eur > 0), 0), f) FROM fac
    UNION ALL
    SELECT 8, 'Penalización €', to_char(coalesce(sum(ajuste_eur) FILTER (WHERE ajuste_eur < 0), 0), f) FROM fac
    UNION ALL
    SELECT 9, 'Balance €', to_char(coalesce(sum(ajuste_eur), 0), f) FROM fac
    UNION ALL
    SELECT 10, 'P1 incumplidos', count(*)::text FROM v_ticket_enriquecido
               WHERE sprint_medicion = p_sprint AND prioridad = 'P1' AND estado_sla = 'incumplido'
    UNION ALL
    SELECT 11, 'Backlog al cierre (viernes)', backlog_fin_dia::text FROM v_kpis_diarios WHERE fecha = v_sprint.fecha_fin
    UNION ALL
    SELECT 12, 'Departamento con peor cumplimiento',
              (SELECT departamento || ' (' || to_char(pct, 'FM990D0') || ' % de ' || n || ' tickets)'
               FROM deps ORDER BY pct, n DESC LIMIT 1)
    UNION ALL
    SELECT 13, 'Origen de los €', CASE WHEN v_oficial THEN 'OFICIAL (fact_facturacion_sprint)'
                                       ELSE 'PROVISIONAL (cálculo en vivo, sprint sin facturar)' END
    ORDER BY 1;
END $$;

COMMENT ON FUNCTION fn_reporte_sprint(text) IS
    'Resumen ejecutivo de un sprint: volumen, cumplimiento, tramos, €, P1, backlog y peor departamento';

-- ---------------------------------------------------------------------------------------------
-- 4. Refrescar el contexto externo (clima) tras una nueva extracción
--    Flujo: python 01_etl/extract_clima.py → python 01_etl/load_to_postgres.py → CALL esto.
-- ---------------------------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sp_refrescar_contexto()
LANGUAGE plpgsql
SET search_path = servicedesk, public
AS $$
DECLARE
    v_filas integer;
BEGIN
    INSERT INTO dim_clima_madrid AS d (fecha, temp_max, temp_min, precipitacion_mm, es_dia_caluroso)
    SELECT r.fecha, r.temp_max, r.temp_min, r.precipitacion_mm, r.es_dia_caluroso
    FROM raw.clima_madrid r
    WHERE EXISTS (SELECT 1 FROM dim_tiempo t WHERE t.fecha = r.fecha)   -- solo días del calendario
    ON CONFLICT (fecha) DO UPDATE
        SET temp_max = EXCLUDED.temp_max, temp_min = EXCLUDED.temp_min,
            precipitacion_mm = EXCLUDED.precipitacion_mm, es_dia_caluroso = EXCLUDED.es_dia_caluroso
        WHERE (d.temp_max, d.temp_min, d.precipitacion_mm, d.es_dia_caluroso)
              IS DISTINCT FROM (EXCLUDED.temp_max, EXCLUDED.temp_min, EXCLUDED.precipitacion_mm, EXCLUDED.es_dia_caluroso);
    GET DIAGNOSTICS v_filas = ROW_COUNT;
    RAISE NOTICE 'Clima: % días nuevos o corregidos', v_filas;
END $$;

COMMENT ON PROCEDURE sp_refrescar_contexto() IS
    'Upsert de dim_clima_madrid desde raw.clima_madrid (solo cambia lo nuevo o corregido)';

-- Comprobación: rutinas creadas en el esquema
SELECT p.proname AS rutina, CASE p.prokind WHEN 'p' THEN 'procedimiento' ELSE 'función' END AS tipo
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'servicedesk' ORDER BY 1;
