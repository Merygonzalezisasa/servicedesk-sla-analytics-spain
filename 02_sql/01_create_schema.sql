
-- =============================================================================================
-- 01_create_schema.sql — Modelo de datos de Brújula Soporte IT (empresa ficticia)
--
-- Crea el esquema en estrella "servicedesk" y carga los datos previamente importados
-- desde los archivos CSV al esquema "raw".
--
-- El esquema "raw" contiene los datos originales, mientras que "servicedesk"
-- organiza la información en tablas de hechos y dimensiones.
-- Se aplican claves foráneas y restricciones CHECK para garantizar la integridad
-- de los datos y el cumplimiento de las reglas de negocio (Ficha §0.2–§0.4).
--
-- El script puede ejecutarse varias veces, ya que elimina y vuelve a crear
-- el esquema completo.
--
-- Ejecución: psql -U analista -d servicedesk_sla -f 02_sql/01_create_schema.sql
-- =============================================================================================


\set ON_ERROR_STOP on
-- El archivo está en UTF-8. Sin esto, psql en una consola de Windows (WIN1252) lee mal las tildes
-- y los textos de las reglas CHECK ('baja médica', 'Petición') dejan de coincidir con los datos.
\encoding UTF8
BEGIN;

DROP SCHEMA IF EXISTS servicedesk CASCADE;
CREATE SCHEMA servicedesk;
COMMENT ON SCHEMA servicedesk IS 'Modelo dimensional del service desk: dimensiones, hechos y facturación por sprint';
SET search_path TO servicedesk;

-- ---------------------------------------------------------------------------------------------
-- CUÁNDO: sprints, calendario y clima
-- ---------------------------------------------------------------------------------------------
CREATE TABLE dim_sprint (
    sprint_id        text PRIMARY KEY CHECK (sprint_id ~ '^\d{4}-\d{2}$'),
    anio_sprint      smallint NOT NULL,
    numero           smallint NOT NULL CHECK (numero BETWEEN 1 AND 18),
    fecha_inicio     date NOT NULL,
    fecha_fin        date NOT NULL,
    dias_laborables  smallint NOT NULL CHECK (dias_laborables BETWEEN 0 AND 15),
    es_completo      boolean NOT NULL,
    n_sprints_anio   smallint NOT NULL,
    UNIQUE (anio_sprint, numero),
    CHECK (fecha_fin = fecha_inicio + 18),                    -- lunes → viernes de la 3ª semana
    CHECK (extract(isodow FROM fecha_inicio) = 1)             -- siempre empieza en lunes
);
COMMENT ON TABLE dim_sprint IS 'Sprints de 3 semanas (Ficha §0.4). Unidad de medición del SLA y de facturación';
COMMENT ON COLUMN dim_sprint.sprint_id IS 'AAAA-NN por el año en que empieza (2024-18 acaba en enero de 2025)';
COMMENT ON COLUMN dim_sprint.n_sprints_anio IS 'Sprints de ese año: la cuota de un sprint es cuota_anual / n_sprints_anio';

CREATE TABLE dim_tiempo (
    fecha              date PRIMARY KEY,
    anio               smallint NOT NULL,
    trimestre          smallint NOT NULL CHECK (trimestre BETWEEN 1 AND 4),
    mes                smallint NOT NULL CHECK (mes BETWEEN 1 AND 12),
    dia_semana         smallint NOT NULL CHECK (dia_semana BETWEEN 1 AND 7),
    es_fin_semana      boolean NOT NULL,
    nombre_festivo     text,
    es_festivo_madrid  boolean NOT NULL,
    es_laborable       boolean NOT NULL,
    es_post_festivo    boolean NOT NULL,
    es_puente          boolean NOT NULL,
    sprint_id          text NOT NULL REFERENCES dim_sprint,
    CHECK (es_festivo_madrid = (nombre_festivo IS NOT NULL)),
    CHECK (es_laborable = (NOT es_fin_semana AND NOT es_festivo_madrid))
);
COMMENT ON TABLE dim_tiempo IS 'Calendario laboral de la sede (Madrid): festivos reales (Nager.Date + BOCM) y sprint de cada día';
COMMENT ON COLUMN dim_tiempo.sprint_id IS 'El sábado y el domingo tras el cierre de un sprint ya cuentan para el siguiente';
COMMENT ON COLUMN dim_tiempo.es_post_festivo IS 'Primer laborable tras un festivo entre semana (correlación 1)';

CREATE TABLE dim_clima_madrid (
    fecha             date PRIMARY KEY REFERENCES dim_tiempo,
    temp_max          numeric(4,1) NOT NULL,
    temp_min          numeric(4,1) NOT NULL,
    precipitacion_mm  numeric(5,1) NOT NULL CHECK (precipitacion_mm >= 0),
    es_dia_caluroso   boolean NOT NULL,
    CHECK (temp_min <= temp_max),
    CHECK (es_dia_caluroso = (temp_max > 35))
);
COMMENT ON TABLE dim_clima_madrid IS 'Clima diario REAL de Madrid (Open-Meteo). Contexto de la correlación 2 (calor → Infraestructura)';

-- ---------------------------------------------------------------------------------------------
-- QUIÉN: organización y clientes
-- ---------------------------------------------------------------------------------------------
CREATE TABLE dim_departamento (
    departamento_id  smallint PRIMARY KEY,
    nombre           text NOT NULL UNIQUE,
    rol              text NOT NULL,
    n_agentes        smallint NOT NULL CHECK (n_agentes > 0),
    nivel_soporte    text NOT NULL CHECK (nivel_soporte IN ('N1', 'N2', 'N3'))
);
COMMENT ON TABLE dim_departamento IS 'Grupos resolutores. Todo ticket entra por Service Desk N1 (id 1)';

CREATE TABLE dim_agente (
    agente_id        text PRIMARY KEY,
    nombre           text NOT NULL,
    departamento_id  smallint NOT NULL REFERENCES dim_departamento,
    nivel_soporte    text NOT NULL CHECK (nivel_soporte IN ('N1', 'N2', 'N3')),
    seniority        text NOT NULL CHECK (seniority IN ('junior', 'senior')),
    fecha_alta       date NOT NULL
);
COMMENT ON TABLE dim_agente IS 'Agentes ficticios (nombres generados con Faker). En los datos, un senior tarda ~18 % menos que un junior en el mismo trabajo';

CREATE TABLE agente_ausencia (
    ausencia_id      integer PRIMARY KEY,
    agente_id        text NOT NULL REFERENCES dim_agente,
    fecha_inicio     date NOT NULL,
    fecha_fin        date NOT NULL,
    dias_laborables  smallint NOT NULL CHECK (dias_laborables > 0),
    motivo           text NOT NULL CHECK (motivo IN ('vacaciones', 'baja médica')),
    CHECK (fecha_fin >= fecha_inicio)
);
COMMENT ON TABLE agente_ausencia IS 'Vacaciones y bajas: en agosto falta ~32 % de la plantilla (correlación 6)';

CREATE TABLE dim_cliente (
    cliente_id          text PRIMARY KEY,
    nombre              text NOT NULL,
    sector              text NOT NULL,
    comunidad_autonoma  text NOT NULL,
    nivel_contrato      text NOT NULL CHECK (nivel_contrato IN ('Gold', 'Silver', 'Bronze')),
    cuota_anual_eur     numeric(12,2) NOT NULL CHECK (cuota_anual_eur > 0),
    n_usuarios          integer NOT NULL CHECK (n_usuarios > 0),
    fecha_alta          date NOT NULL
);
COMMENT ON TABLE dim_cliente IS 'Empresas cliente ficticias. Nivel de contrato = objetivo de SLA y tramos de bonificación/penalización';
COMMENT ON COLUMN dim_cliente.cuota_anual_eur IS 'Se factura por sprint: cuota_anual / dim_sprint.n_sprints_anio';

-- ---------------------------------------------------------------------------------------------
-- QUÉ: políticas de SLA y tramos de ajuste
-- ---------------------------------------------------------------------------------------------
CREATE TABLE dim_sla (
    sla_id                   text PRIMARY KEY,
    tipo                     text NOT NULL CHECK (tipo IN ('Incidencia', 'Petición', 'Tarea')),
    prioridad                text NOT NULL CHECK (prioridad IN ('P1', 'P2', 'P3', 'P4')),
    objetivo_respuesta_min   integer NOT NULL CHECK (objetivo_respuesta_min > 0),
    objetivo_resolucion_min  integer NOT NULL CHECK (objetivo_resolucion_min > 0),
    reloj                    text NOT NULL CHECK (reloj IN ('24x7', 'laboral')),
    computa_facturacion      boolean NOT NULL,
    UNIQUE (tipo, prioridad),
    -- Reglas con nombre: si se incumplen, el mensaje de error dice qué regla de negocio se rompió.
    CONSTRAINT p1_solo_incidencias CHECK (prioridad <> 'P1' OR tipo = 'Incidencia'),
    CONSTRAINT p1_reloj_24x7 CHECK ((prioridad = 'P1') = (reloj = '24x7')),
    CONSTRAINT tareas_no_facturan CHECK (computa_facturacion = (tipo <> 'Tarea'))
);
COMMENT ON TABLE dim_sla IS 'Matriz de SLA tipo × prioridad (Ficha §0.2). Minutos de reloj: 24x7 para P1, laboral L–V 9–18 para el resto';

CREATE TABLE dim_tramo_ajuste (
    tramo_id        smallint PRIMARY KEY,
    nivel_contrato  text NOT NULL CHECK (nivel_contrato IN ('Gold', 'Silver', 'Bronze')),
    pct_desde       numeric(5,2) NOT NULL,
    pct_hasta       numeric(5,2) NOT NULL,
    tipo            text NOT NULL CHECK (tipo IN ('bonus', 'neutro', 'deficiente')),
    pct_ajuste      numeric(5,2) NOT NULL,
    CHECK (pct_desde < pct_hasta),
    CHECK ((tipo = 'bonus' AND pct_ajuste > 0) OR (tipo = 'neutro' AND pct_ajuste = 0)
           OR (tipo = 'deficiente' AND pct_ajuste < 0))
);
COMMENT ON TABLE dim_tramo_ajuste IS 'Tramos sobre la cuota del sprint: % de cumplimiento en [pct_desde, pct_hasta) → % de ajuste';

-- ---------------------------------------------------------------------------------------------
-- HECHOS
-- ---------------------------------------------------------------------------------------------
CREATE TABLE fact_ticket (
    ticket_id                text PRIMARY KEY,
    cliente_id               text NOT NULL REFERENCES dim_cliente,
    sla_id                   text NOT NULL REFERENCES dim_sla,
    departamento_id          smallint NOT NULL REFERENCES dim_departamento,
    agente_id                text REFERENCES dim_agente,
    fecha_creacion           timestamp NOT NULL,
    fecha_primera_respuesta  timestamp,
    fecha_resolucion         timestamp,
    fecha_cierre             timestamp,
    fecha_cancelacion        timestamp,
    fecha_incumplimiento     timestamp,
    estado_actual            text NOT NULL CHECK (estado_actual IN
                                 ('Abierto', 'En curso', 'Esperando al cliente', 'Resuelto', 'Cerrado', 'Cancelado')),
    estado_sla               text NOT NULL CHECK (estado_sla IN ('cumplido', 'incumplido', 'en curso', 'cancelado')),
    n_reasignaciones         smallint NOT NULL CHECK (n_reasignaciones >= 0),
    min_respuesta_sla        integer CHECK (min_respuesta_sla > 0),
    min_resolucion_sla       integer CHECK (min_resolucion_sla > 0),
    min_pausa                integer NOT NULL CHECK (min_pausa >= 0),
    cumple_respuesta         boolean,
    cumple_resolucion        boolean,
    computa_facturacion      boolean NOT NULL,
    sprint_apertura          text NOT NULL REFERENCES dim_sprint,
    sprint_medicion          text REFERENCES dim_sprint,
    CHECK (fecha_primera_respuesta >= fecha_creacion),
    CHECK (fecha_resolucion >= fecha_primera_respuesta),
    CHECK (fecha_cierre >= fecha_resolucion),
    -- Regla de las dos fechas (Ficha §0.4): solo lo cumplido o incumplido se mide en un sprint.
    CHECK ((sprint_medicion IS NOT NULL) = (estado_sla IN ('cumplido', 'incumplido'))),
    CHECK ((estado_sla = 'incumplido') = (fecha_incumplimiento IS NOT NULL)),
    CHECK (cumple_resolucion IS NOT DISTINCT FROM CASE estado_sla WHEN 'cumplido' THEN true
                                                                   WHEN 'incumplido' THEN false END),
    CHECK (NOT computa_facturacion OR estado_sla IN ('cumplido', 'incumplido'))
);
COMMENT ON TABLE fact_ticket IS 'Un ticket por fila (sintético, SEED=42), con su SLA ya medido. Corte: 2026-01-02 18:00';
COMMENT ON COLUMN fact_ticket.departamento_id IS 'Departamento que resuelve (o donde está el ticket al corte)';
COMMENT ON COLUMN fact_ticket.fecha_incumplimiento IS 'Momento en que se agotó el SLA de resolución (solo incumplidos)';
COMMENT ON COLUMN fact_ticket.min_resolucion_sla IS 'Minutos de reloj consumidos sin contar las pausas; si sigue abierto, hasta el corte';
COMMENT ON COLUMN fact_ticket.sprint_apertura IS 'Sprint en que entra el ticket: carga de trabajo';
COMMENT ON COLUMN fact_ticket.sprint_medicion IS 'Sprint en que se conoce el resultado: resolución si cumple, vencimiento si incumple';
COMMENT ON COLUMN fact_ticket.computa_facturacion IS 'Incidencia o petición, medida (no cancelada ni en curso): entra en el % del sprint';

CREATE TABLE fact_ticket_estado (
    ticket_id        text NOT NULL REFERENCES fact_ticket ON DELETE CASCADE,
    secuencia        smallint NOT NULL CHECK (secuencia > 0),
    estado           text NOT NULL CHECK (estado IN
                         ('Abierto', 'En curso', 'Esperando al cliente', 'Resuelto', 'Cerrado', 'Cancelado')),
    departamento_id  smallint NOT NULL REFERENCES dim_departamento,
    agente_id        text REFERENCES dim_agente,
    inicio           timestamp NOT NULL,
    fin              timestamp,
    pausa_reloj      boolean NOT NULL,
    PRIMARY KEY (ticket_id, secuencia),
    CHECK (fin >= inicio),
    CHECK (pausa_reloj = (estado = 'Esperando al cliente'))
);
COMMENT ON TABLE fact_ticket_estado IS 'Historial de estados: por qué departamentos pasó cada ticket y cuánto tiempo estuvo en cada uno';
COMMENT ON COLUMN fact_ticket_estado.fin IS 'NULL = estado actual al corte (o estado final: Cerrado / Cancelado)';

CREATE TABLE fact_facturacion_sprint (
    cliente_id           text NOT NULL REFERENCES dim_cliente,
    sprint_id            text NOT NULL REFERENCES dim_sprint,
    nivel_contrato       text NOT NULL,
    cuota_sprint_eur     numeric(12,2) NOT NULL,
    n_tickets_computables integer NOT NULL CHECK (n_tickets_computables >= 0),
    n_cumplidos          integer NOT NULL CHECK (n_cumplidos >= 0),
    pct_cumplimiento     numeric(5,2),
    tramo_id             smallint REFERENCES dim_tramo_ajuste,
    tipo_tramo           text NOT NULL CHECK (tipo_tramo IN ('bonus', 'neutro', 'deficiente')),
    pct_ajuste           numeric(5,2) NOT NULL,
    ajuste_eur           numeric(12,2) NOT NULL,
    calculado_en         timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (cliente_id, sprint_id),
    CHECK (n_cumplidos <= n_tickets_computables)
);
COMMENT ON TABLE fact_facturacion_sprint IS 'Bonificación/penalización por cliente y sprint. La llena sp_calcular_facturacion_sprint (03_stored_procedures.sql)';
COMMENT ON COLUMN fact_facturacion_sprint.pct_cumplimiento IS 'NULL si el cliente no tuvo tickets computables en el sprint (tramo neutro, sin ajuste)';

-- ---------------------------------------------------------------------------------------------
-- Índices: en las columnas por las que se filtra y se une (las PK ya tienen el suyo)
-- ---------------------------------------------------------------------------------------------
CREATE INDEX ix_tiempo_sprint        ON dim_tiempo (sprint_id);
CREATE INDEX ix_agente_departamento  ON dim_agente (departamento_id);
CREATE INDEX ix_ausencia_agente      ON agente_ausencia (agente_id, fecha_inicio);
CREATE INDEX ix_ticket_creacion      ON fact_ticket (fecha_creacion);
CREATE INDEX ix_ticket_cliente       ON fact_ticket (cliente_id);
CREATE INDEX ix_ticket_sla           ON fact_ticket (sla_id);
CREATE INDEX ix_ticket_departamento  ON fact_ticket (departamento_id);
CREATE INDEX ix_ticket_agente        ON fact_ticket (agente_id);
CREATE INDEX ix_ticket_medicion      ON fact_ticket (sprint_medicion, cliente_id) WHERE computa_facturacion;
CREATE INDEX ix_ticket_apertura      ON fact_ticket (sprint_apertura);
CREATE INDEX ix_ticket_estado_sla    ON fact_ticket (estado_sla);
CREATE INDEX ix_estado_departamento  ON fact_ticket_estado (departamento_id);
CREATE INDEX ix_estado_agente        ON fact_ticket_estado (agente_id);
CREATE INDEX ix_estado_inicio        ON fact_ticket_estado (inicio);
CREATE INDEX ix_facturacion_sprint   ON fact_facturacion_sprint (sprint_id);

-- ---------------------------------------------------------------------------------------------
-- Carga inicial desde "raw" (en orden: primero lo que otras tablas referencian)
-- ---------------------------------------------------------------------------------------------
INSERT INTO dim_sprint
SELECT sprint_id, anio_sprint, numero, fecha_inicio, fecha_fin, dias_laborables, es_completo,
       count(*) OVER (PARTITION BY anio_sprint)
FROM raw.dim_sprint;

INSERT INTO dim_tiempo SELECT * FROM raw.dim_tiempo;
INSERT INTO dim_clima_madrid
SELECT fecha, temp_max, temp_min, precipitacion_mm, es_dia_caluroso FROM raw.clima_madrid;
INSERT INTO dim_departamento SELECT * FROM raw.dim_departamento;
INSERT INTO dim_agente SELECT * FROM raw.dim_agente;
INSERT INTO agente_ausencia SELECT * FROM raw.agente_ausencia;
INSERT INTO dim_cliente SELECT * FROM raw.dim_cliente;
INSERT INTO dim_sla SELECT * FROM raw.dim_sla;
INSERT INTO dim_tramo_ajuste SELECT * FROM raw.dim_tramo_ajuste;
INSERT INTO fact_ticket SELECT * FROM raw.fact_ticket;
INSERT INTO fact_ticket_estado SELECT * FROM raw.fact_ticket_estado;

COMMIT;
-- Estadísticas para el planificador de consultas (solo las tablas de este esquema).
ANALYZE dim_sprint, dim_tiempo, dim_clima_madrid, dim_departamento, dim_agente, agente_ausencia,
        dim_cliente, dim_sla, dim_tramo_ajuste, fact_ticket, fact_ticket_estado, fact_facturacion_sprint;

-- Resumen: filas por tabla del modelo
SELECT relname AS tabla, n_live_tup AS filas
FROM pg_stat_user_tables WHERE schemaname = 'servicedesk' ORDER BY relname;
