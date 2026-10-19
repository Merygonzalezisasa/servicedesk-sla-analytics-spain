"""
verificar_carga.py — Comprueba dentro de PostgreSQL que la carga del esquema `raw` es correcta.

Tres bloques:
    1. Integridad: cada clave ajena apunta a una fila que existe y no hay nulos donde no puede haberlos.
    2. Reglas de negocio: fechas en orden, regla de las dos fechas (Ficha §0.4), dominios de los estados.
    3. Cifras de control: lo que calcula SQL sobre la base tiene que coincidir con lo que calcula pandas
       leyendo los CSV. Son dos caminos independientes: si coinciden, la carga no perdió ni alteró nada.

Cada comprobación de los bloques 1 y 2 es una consulta que cuenta filas problemáticas: 0 = OK.
Termina con código de salida 1 si algo falla (útil si un día se automatiza).

Uso: python 01_etl/verificar_carga.py   (después de load_to_postgres.py)
"""

import sys

import pandas as pd
from sqlalchemy import text

from comun import DIR_RAW, configurar_log
from load_to_postgres import ESQUEMA, TABLAS, motor

log = configurar_log("verificar_carga")
R = ESQUEMA

# (descripción, consulta que cuenta filas problemáticas)
INTEGRIDAD = [
    ("Tickets con cliente inexistente",
     f"SELECT count(*) FROM {R}.fact_ticket t LEFT JOIN {R}.dim_cliente c USING (cliente_id) WHERE c.cliente_id IS NULL"),
    ("Tickets con política de SLA inexistente",
     f"SELECT count(*) FROM {R}.fact_ticket t LEFT JOIN {R}.dim_sla s USING (sla_id) WHERE s.sla_id IS NULL"),
    ("Tickets con departamento inexistente",
     f"SELECT count(*) FROM {R}.fact_ticket t LEFT JOIN {R}.dim_departamento d USING (departamento_id) WHERE d.departamento_id IS NULL"),
    ("Tickets con agente inexistente",
     f"SELECT count(*) FROM {R}.fact_ticket t LEFT JOIN {R}.dim_agente a USING (agente_id) WHERE t.agente_id IS NOT NULL AND a.agente_id IS NULL"),
    ("Tickets con sprint de apertura o de medición inexistente",
     f"""SELECT count(*) FROM {R}.fact_ticket t
         WHERE NOT EXISTS (SELECT 1 FROM {R}.dim_sprint s WHERE s.sprint_id = t.sprint_apertura)
            OR (t.sprint_medicion IS NOT NULL
                AND NOT EXISTS (SELECT 1 FROM {R}.dim_sprint s WHERE s.sprint_id = t.sprint_medicion))"""),
    ("Historial de estados de tickets inexistentes",
     f"SELECT count(*) FROM {R}.fact_ticket_estado e LEFT JOIN {R}.fact_ticket t USING (ticket_id) WHERE t.ticket_id IS NULL"),
    ("Tickets sin historial de estados",
     f"SELECT count(*) FROM {R}.fact_ticket t WHERE NOT EXISTS (SELECT 1 FROM {R}.fact_ticket_estado e WHERE e.ticket_id = t.ticket_id)"),
    ("Historial con agente o departamento inexistente",
     f"""SELECT count(*) FROM {R}.fact_ticket_estado e
         LEFT JOIN {R}.dim_departamento d USING (departamento_id) LEFT JOIN {R}.dim_agente a USING (agente_id)
         WHERE d.departamento_id IS NULL OR (e.agente_id IS NOT NULL AND a.agente_id IS NULL)"""),
    ("Agentes de un departamento inexistente o ausencias de agentes inexistentes",
     f"""SELECT (SELECT count(*) FROM {R}.dim_agente a LEFT JOIN {R}.dim_departamento d USING (departamento_id)
                 WHERE d.departamento_id IS NULL)
              + (SELECT count(*) FROM {R}.agente_ausencia x LEFT JOIN {R}.dim_agente a USING (agente_id)
                 WHERE a.agente_id IS NULL)"""),
    ("Días del calendario sin sprint, o sin clima",
     f"""SELECT count(*) FROM {R}.dim_tiempo t
         WHERE NOT EXISTS (SELECT 1 FROM {R}.dim_sprint s WHERE s.sprint_id = t.sprint_id)
            OR NOT EXISTS (SELECT 1 FROM {R}.clima_madrid c WHERE c.fecha = t.fecha)"""),
    ("Festivos que el calendario no marca como festivo",
     f"""SELECT count(*) FROM {R}.festivos_madrid f LEFT JOIN {R}.dim_tiempo t USING (fecha)
         WHERE t.fecha IS NULL OR NOT t.es_festivo_madrid"""),
    ("Nulos en columnas obligatorias de fact_ticket",
     f"""SELECT count(*) FROM {R}.fact_ticket WHERE fecha_creacion IS NULL OR cliente_id IS NULL
         OR sla_id IS NULL OR estado_actual IS NULL OR estado_sla IS NULL OR sprint_apertura IS NULL
         OR computa_facturacion IS NULL OR n_reasignaciones IS NULL OR min_pausa IS NULL"""),
]

NEGOCIO = [
    ("Estados fuera del catálogo (6 estados) o estado del SLA desconocido",
     f"""SELECT (SELECT count(*) FROM {R}.fact_ticket_estado WHERE estado NOT IN
                 ('Abierto', 'En curso', 'Esperando al cliente', 'Resuelto', 'Cerrado', 'Cancelado'))
              + (SELECT count(*) FROM {R}.fact_ticket WHERE estado_sla NOT IN
                 ('cumplido', 'incumplido', 'en curso', 'cancelado'))"""),
    ("P1 que no es una incidencia (Ficha §0.2)",
     f"SELECT count(*) FROM {R}.dim_sla WHERE prioridad = 'P1' AND tipo <> 'Incidencia'"),
    ("Fechas fuera de orden (creación ≤ 1ª respuesta ≤ resolución ≤ cierre)",
     f"""SELECT count(*) FROM {R}.fact_ticket
         WHERE fecha_primera_respuesta < fecha_creacion OR fecha_resolucion < fecha_primera_respuesta
            OR fecha_cierre < fecha_resolucion"""),
    ("Tickets creados fuera del período o después del corte",
     f"""SELECT count(*) FROM {R}.fact_ticket
         WHERE fecha_creacion < (SELECT min(fecha) FROM {R}.dim_tiempo)
            OR fecha_creacion >= (SELECT max(fecha) FROM {R}.dim_tiempo) + time '18:00'"""),
    ("Historial: estados que no empiezan donde acaba el anterior",
     f"""SELECT count(*) FROM (SELECT fin, lead(inicio) OVER (PARTITION BY ticket_id ORDER BY secuencia) AS sig
                               FROM {R}.fact_ticket_estado) x
         WHERE x.sig IS NOT NULL AND x.sig <> x.fin"""),
    ("Cumplido/incumplido que no cuadra con los minutos y el objetivo del SLA",
     f"""SELECT count(*) FROM {R}.fact_ticket t JOIN {R}.dim_sla s USING (sla_id)
         WHERE t.fecha_resolucion IS NOT NULL AND t.estado_sla IN ('cumplido', 'incumplido')
           AND (t.estado_sla = 'cumplido') <> (t.min_resolucion_sla <= s.objetivo_resolucion_min)"""),
    ("Regla de las dos fechas: sprint de medición mal asignado",
     f"""SELECT count(*) FROM {R}.fact_ticket t
         LEFT JOIN {R}.dim_tiempo r ON r.fecha = t.fecha_resolucion::date
         LEFT JOIN {R}.dim_tiempo v ON v.fecha = t.fecha_incumplimiento::date
         WHERE (t.estado_sla = 'cumplido' AND t.sprint_medicion IS DISTINCT FROM r.sprint_id)
            OR (t.estado_sla = 'incumplido' AND t.sprint_medicion IS DISTINCT FROM v.sprint_id)
            OR (t.estado_sla IN ('en curso', 'cancelado') AND t.sprint_medicion IS NOT NULL)"""),
    ("Cancelados o en curso que computan en la factura; tareas que computan",
     f"""SELECT count(*) FROM {R}.fact_ticket t JOIN {R}.dim_sla s USING (sla_id)
         WHERE t.computa_facturacion AND (t.estado_sla IN ('cancelado', 'en curso') OR NOT s.computa_facturacion)"""),
]

# Cifras de control: misma cuenta por SQL (base) y por pandas (CSV).
SQL_CUMPLIMIENTO = f"""
    SELECT c.nivel_contrato, round(avg(t.cumple_resolucion::int) * 100, 1) AS pct
    FROM {R}.fact_ticket t JOIN {R}.dim_cliente c USING (cliente_id)
    WHERE t.computa_facturacion GROUP BY 1 ORDER BY 1"""
SQL_ESTADOS = f"SELECT estado_sla, count(*) FROM {R}.fact_ticket GROUP BY 1 ORDER BY 1"
SQL_MINUTOS = f"SELECT sum(min_resolucion_sla), sum(min_pausa) FROM {R}.fact_ticket"


def comprobar(con, bloque: str, lista: list) -> int:
    log.info(bloque)
    fallos = 0
    for descripcion, consulta in lista:
        n = con.execute(text(consulta)).scalar()
        fallos += n > 0
        log.info(f"  {'✅' if n == 0 else '❌'} {descripcion}" + (f" → {n:,} filas".replace(",", ".") if n else ""))
    return fallos


def cifras_de_control(con) -> int:
    log.info("3. Cifras de control (SQL sobre la base vs pandas sobre los CSV)")
    tk = pd.read_csv(DIR_RAW / "fact_ticket.csv")
    cli = pd.read_csv(DIR_RAW / "dim_cliente.csv")
    fallos = 0

    def comparar(nombre, sql, csv):
        nonlocal fallos
        ok = sql == csv
        fallos += not ok
        log.info(f"  {'✅' if ok else '❌'} {nombre}: SQL {sql}" + ("" if ok else f" ≠ CSV {csv}"))

    filas_sql, filas_csv = {}, {}
    for tabla in TABLAS:
        filas_sql[tabla] = con.execute(text(f"SELECT count(*) FROM {R}.{tabla}")).scalar()
        with open(DIR_RAW / f"{tabla}.csv", encoding="utf-8") as f:
            filas_csv[tabla] = sum(1 for _ in f) - 1
    comparar(f"filas de las {len(TABLAS)} tablas (total)", sum(filas_sql.values()), sum(filas_csv.values()))
    distintas = {t: (filas_sql[t], filas_csv[t]) for t in TABLAS if filas_sql[t] != filas_csv[t]}
    if distintas:
        log.info(f"     tablas con distinto nº de filas (base, CSV): {distintas}")

    comp = tk[tk["computa_facturacion"]].merge(cli, on="cliente_id")
    csv_pct = (comp.groupby("nivel_contrato")["cumple_resolucion"].mean() * 100).round(1).to_dict()
    sql_pct = {n: float(p) for n, p in con.execute(text(SQL_CUMPLIMIENTO))}
    comparar("cumplimiento de resolución por nivel (%)", sql_pct, csv_pct)

    comparar("tickets por estado del SLA", {e: n for e, n in con.execute(text(SQL_ESTADOS))},
             tk["estado_sla"].value_counts().sort_index().to_dict())
    sql_min = tuple(int(x) for x in con.execute(text(SQL_MINUTOS)).one())
    comparar("minutos de SLA y de pausa (suma)", sql_min,
             (int(tk["min_resolucion_sla"].sum()), int(tk["min_pausa"].sum())))
    return fallos


def main() -> None:
    log.info(f"Verificando el esquema '{R}'")
    with motor().connect() as con:
        fallos = comprobar(con, "1. Integridad", INTEGRIDAD)
        fallos += comprobar(con, "2. Reglas de negocio", NEGOCIO)
        fallos += cifras_de_control(con)
    total = len(INTEGRIDAD) + len(NEGOCIO)
    if fallos:
        log.error(f"{fallos} comprobaciones fallidas. Revisar antes de pasar a la Fase 2.")
        sys.exit(1)
    log.info(f"Todo en verde ({total} comprobaciones + cifras de control). CARGA VERIFICADA.")


if __name__ == "__main__":
    main()
