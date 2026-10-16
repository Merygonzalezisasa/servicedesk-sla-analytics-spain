"""
load_to_postgres.py — Carga los CSV de data/raw en PostgreSQL (esquema `raw`), con upsert.

    · Una tabla por CSV, con las mismas columnas, tipos correctos y clave primaria.
    · Upsert (INSERT … ON CONFLICT … DO UPDATE): correr el script dos veces no duplica nada. Las filas
      nuevas se insertan, las que cambiaron se actualizan y las iguales no se tocan.
    · Todo en una única transacción: o se carga todo, o no se carga nada.
    · El upsert no borra: si una fila ya no está en el CSV, se avisa en el log (no se elimina sola).

El esquema `raw` es la zona de aterrizaje. El modelo dimensional (vistas, facturación por sprint)
se construye encima en la Fase 2, en el esquema DB_SCHEMA.

Uso: python 01_etl/load_to_postgres.py   (antes: extract_*.py y generate_tickets_data.py)
"""

import csv

from sqlalchemy import create_engine
from sqlalchemy.engine import URL

from comun import DIR_RAW, config, configurar_log

log = configurar_log("load_to_postgres")

ESQUEMA = "raw"

# tabla: (clave primaria, columnas con su tipo). El orden de las columnas no importa: se toma del CSV.
TS = "timestamp"
TABLAS = {
    "dim_tiempo": (["fecha"], {
        "fecha": "date", "anio": "smallint", "trimestre": "smallint", "mes": "smallint",
        "dia_semana": "smallint", "es_fin_semana": "boolean", "nombre_festivo": "text",
        "es_festivo_madrid": "boolean", "es_laborable": "boolean", "es_post_festivo": "boolean",
        "es_puente": "boolean", "sprint_id": "text"}),
    "dim_sprint": (["sprint_id"], {
        "sprint_id": "text", "anio_sprint": "smallint", "numero": "smallint", "fecha_inicio": "date",
        "fecha_fin": "date", "dias_laborables": "smallint", "es_completo": "boolean"}),
    "dim_departamento": (["departamento_id"], {
        "departamento_id": "smallint", "nombre": "text", "rol": "text", "n_agentes": "smallint",
        "nivel_soporte": "text"}),
    "dim_agente": (["agente_id"], {
        "agente_id": "text", "nombre": "text", "departamento_id": "smallint", "nivel_soporte": "text",
        "seniority": "text", "fecha_alta": "date"}),
    "agente_ausencia": (["ausencia_id"], {
        "ausencia_id": "integer", "agente_id": "text", "fecha_inicio": "date", "fecha_fin": "date",
        "dias_laborables": "smallint", "motivo": "text"}),
    "dim_cliente": (["cliente_id"], {
        "cliente_id": "text", "nombre": "text", "sector": "text", "comunidad_autonoma": "text",
        "nivel_contrato": "text", "cuota_anual_eur": "numeric(12,2)", "n_usuarios": "integer",
        "fecha_alta": "date"}),
    "dim_sla": (["sla_id"], {
        "sla_id": "text", "tipo": "text", "prioridad": "text", "objetivo_respuesta_min": "integer",
        "objetivo_resolucion_min": "integer", "reloj": "text", "computa_facturacion": "boolean"}),
    "dim_tramo_ajuste": (["tramo_id"], {
        "tramo_id": "smallint", "nivel_contrato": "text", "pct_desde": "numeric(5,2)",
        "pct_hasta": "numeric(5,2)", "tipo": "text", "pct_ajuste": "numeric(5,2)"}),
    "clima_madrid": (["fecha"], {
        "fecha": "date", "temp_max": "numeric(4,1)", "temp_min": "numeric(4,1)",
        "precipitacion_mm": "numeric(5,1)", "es_dia_caluroso": "boolean"}),
    "festivos_madrid": (["fecha"], {
        "fecha": "date", "nombre": "text", "ambito": "text", "fuente": "text", "es_fin_semana": "boolean"}),
    "fact_ticket": (["ticket_id"], {
        "ticket_id": "text", "cliente_id": "text", "sla_id": "text", "departamento_id": "smallint",
        "agente_id": "text", "fecha_creacion": TS, "fecha_primera_respuesta": TS, "fecha_resolucion": TS,
        "fecha_cierre": TS, "fecha_cancelacion": TS, "fecha_incumplimiento": TS, "estado_actual": "text",
        "estado_sla": "text", "n_reasignaciones": "smallint", "min_respuesta_sla": "integer",
        "min_resolucion_sla": "integer", "min_pausa": "integer", "cumple_respuesta": "boolean",
        "cumple_resolucion": "boolean", "computa_facturacion": "boolean", "sprint_apertura": "text",
        "sprint_medicion": "text"}),
    "fact_ticket_estado": (["ticket_id", "secuencia"], {
        "ticket_id": "text", "secuencia": "smallint", "estado": "text", "departamento_id": "smallint",
        "agente_id": "text", "inicio": TS, "fin": TS, "pausa_reloj": "boolean"}),
}


def motor():
    url = URL.create("postgresql+psycopg2", username=config("DB_USER"), password=config("DB_PASSWORD"),
                     host=config("DB_HOST"), port=int(config("DB_PORT")), database=config("DB_NAME"))
    return create_engine(url)


def cabecera(ruta) -> list[str]:
    with open(ruta, encoding="utf-8", newline="") as f:
        return next(csv.reader(f))


def cargar_tabla(cur, tabla: str, pk: list[str], tipos: dict[str, str]) -> dict:
    ruta = DIR_RAW / f"{tabla}.csv"
    if not ruta.exists():
        raise FileNotFoundError(f"Falta {ruta.name}: ejecuta antes los scripts de extracción y generación")
    columnas = cabecera(ruta)
    if set(columnas) != set(tipos):
        raise ValueError(f"{ruta.name}: las columnas del CSV no coinciden con la tabla. "
                         f"Sobran {set(columnas) - set(tipos) or '—'}; faltan {set(tipos) - set(columnas) or '—'}")

    destino = f"{ESQUEMA}.{tabla}"
    definicion = ", ".join(f"{c} {t}" for c, t in tipos.items())
    cur.execute(f"CREATE TABLE IF NOT EXISTS {destino} ({definicion}, PRIMARY KEY ({', '.join(pk)}))")

    # 1. El CSV entra tal cual en una tabla temporal (COPY es la vía rápida de PostgreSQL).
    cur.execute(f"CREATE TEMP TABLE tmp (LIKE {destino}) ON COMMIT DROP")
    lista = ", ".join(columnas)
    with open(ruta, encoding="utf-8", newline="") as f:
        cur.copy_expert(f"COPY tmp ({lista}) FROM STDIN WITH (FORMAT csv, HEADER true)", f)
    leidas = cur.rowcount

    # 2. Upsert desde la temporal. Solo se actualiza si algo cambió; xmax = 0 distingue inserción.
    no_pk = [c for c in tipos if c not in pk]
    cur.execute(f"""
        INSERT INTO {destino} AS d ({lista}) SELECT {lista} FROM tmp
        ON CONFLICT ({', '.join(pk)}) DO UPDATE SET {', '.join(f'{c} = EXCLUDED.{c}' for c in no_pk)}
        WHERE ({', '.join(f'd.{c}' for c in no_pk)}) IS DISTINCT FROM ({', '.join(f'EXCLUDED.{c}' for c in no_pk)})
        RETURNING (xmax = 0) AS insertada""")
    resultado = [fila[0] for fila in cur.fetchall()]
    insertadas = sum(resultado)
    actualizadas = len(resultado) - insertadas

    # 3. Filas de la tabla que ya no vienen en el CSV: el upsert no las borra, se avisa.
    union = " AND ".join(f"t.{c} = d.{c}" for c in pk)
    cur.execute(f"SELECT count(*) FROM {destino} d WHERE NOT EXISTS (SELECT 1 FROM tmp t WHERE {union})")
    huerfanas = cur.fetchone()[0]
    cur.execute(f"SELECT count(*) FROM {destino}")
    en_tabla = cur.fetchone()[0]
    cur.execute("DROP TABLE tmp")
    return {"tabla": tabla, "leidas": leidas, "insertadas": insertadas, "actualizadas": actualizadas,
            "sin_cambios": leidas - insertadas - actualizadas, "en_tabla": en_tabla, "huerfanas": huerfanas}


def main() -> None:
    log.info(f"Cargando {len(TABLAS)} CSV de {DIR_RAW.name}/ en el esquema '{ESQUEMA}' de {config('DB_NAME')}")
    conexion = motor().raw_connection()
    try:
        with conexion.cursor() as cur:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {ESQUEMA}")
            resumen = [cargar_tabla(cur, t, pk, tipos) for t, (pk, tipos) in TABLAS.items()]
        conexion.commit()
    except Exception:
        conexion.rollback()
        log.exception("La carga falló: no se ha guardado nada (rollback)")
        raise
    finally:
        conexion.close()

    for r in resumen:
        aviso = f" · ⚠ {r['huerfanas']} filas en la tabla que ya no están en el CSV" if r["huerfanas"] else ""
        log.info(f"  {r['tabla']:<20} leídas {r['leidas']:>7,} · nuevas {r['insertadas']:>7,} · "
                 f"actualizadas {r['actualizadas']:>6,} · sin cambios {r['sin_cambios']:>7,} · "
                 f"en la tabla {r['en_tabla']:>7,}{aviso}".replace(",", "."))
    descuadre = [r["tabla"] for r in resumen if r["en_tabla"] != r["leidas"] + r["huerfanas"]]
    if descuadre:
        raise RuntimeError(f"Las cuentas no cuadran en: {descuadre}")
    total = f"{sum(r['leidas'] for r in resumen):,}".replace(",", ".")
    log.info(f"Carga terminada: {total} filas leídas, todas en la base.")


if __name__ == "__main__":
    main()
