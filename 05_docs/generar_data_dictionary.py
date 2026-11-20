"""Genera 05_docs/data_dictionary.md leyendo el esquema de PostgreSQL.

Cada tabla y vista con: descripción, filas, y por columna su tipo, clave, descripción y un ejemplo real.
La descripción sale del COMMENT de la base si existe; si no, del diccionario DESCRIPCIONES de abajo.
Así el documento no puede quedarse desfasado: se regenera con la base.

Uso: python 05_docs/generar_data_dictionary.py
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "01_etl"))
from comun import config  # noqa: E402
import psycopg2  # noqa: E402

SALIDA = RAIZ / "05_docs" / "data_dictionary.md"

DESCRIPCIONES = {
    # Identificadores y nombres
    "ticket_id": "Identificador del ticket (TCK-NNNNNN)",
    "cliente_id": "Identificador del cliente", "cliente": "Nombre (ficticio) del cliente",
    "agente_id": "Identificador del agente", "agente": "Nombre (ficticio) del agente",
    "departamento_id": "Identificador del departamento", "departamento": "Departamento que resuelve el ticket",
    "sla_id": "Política de SLA aplicada (tipo × prioridad)", "sprint_id": "Sprint (AAAA-NN)",
    "tramo_id": "Tramo de ajuste de la factura", "ausencia_id": "Identificador de la ausencia",
    "nombre": "Nombre", "secuencia": "Orden del cambio de estado dentro del ticket",
    # Cliente y contrato
    "sector": "Sector del cliente", "comunidad_autonoma": "Comunidad autónoma de la sede del cliente",
    "nivel_contrato": "Nivel de contrato: Gold, Silver o Bronze", "n_usuarios": "Usuarios del cliente que pueden abrir tickets",
    "fecha_alta": "Fecha de alta del contrato", "cuota_anual_eur": "Cuota anual del contrato (€)",
    "cuota_sprint_eur": "Cuota que corresponde al sprint (cuota anual ÷ nº de sprints del año, €)",
    "cuota_eur": "Cuota facturada en el periodo (€)", "objetivo_contractual": "% de cumplimiento comprometido en el contrato",
    "meses_activo": "Meses con contrato activo en el periodo",
    # Agentes y departamentos
    "seniority": "Antigüedad del agente: senior o junior", "rol": "Rol del agente",
    "nivel_soporte": "Nivel de soporte del departamento (N1, N2…)", "n_agentes": "Agentes del departamento",
    "motivo": "Motivo de la ausencia (vacaciones o baja médica)", "inicio": "Fecha de inicio", "fin": "Fecha de fin",
    # Política de SLA
    "tipo": "Tipo de ticket: Incidencia, Petición o Tarea", "prioridad": "Prioridad P1 (crítica) a P4 (baja)",
    "reloj": "Reloj del SLA: 24x7 o laboral (L–V 09–18 sin festivos de Madrid)",
    "objetivo_respuesta_min": "Minutos de reloj permitidos para la 1ª respuesta",
    "objetivo_resolucion_min": "Minutos de reloj permitidos para la resolución",
    "computa_facturacion": "El ticket cuenta para la factura (no las tareas, ni cancelados ni abiertos)",
    # Fechas y estados del ticket
    "fecha_creacion": "Fecha y hora de apertura", "fecha_primera_respuesta": "Fecha y hora de la 1ª respuesta",
    "fecha_resolucion": "Fecha y hora de resolución", "fecha_cierre": "Cierre automático 3 días laborables tras resolver",
    "fecha_cancelacion": "Fecha y hora de cancelación (si se canceló)",
    "fecha_incumplimiento": "Momento en que venció el SLA de resolución (solo si incumple)",
    "fecha_medicion": "Fecha en la que se mide el ticket (resolución o vencimiento)",
    "sprint_apertura": "Sprint en el que se abrió", "sprint_medicion": "Sprint en el que se mide (regla de las dos fechas)",
    "estado": "Estado del ticket en ese tramo del historial", "estado_actual": "Último estado del ticket",
    "estado_sla": "cumplido, incumplido, en curso o cancelado",
    "pausa_reloj": "El estado pausa el reloj de resolución (Esperando al cliente)",
    "cumple_respuesta": "Cumple el SLA de 1ª respuesta", "cumple_resolucion": "Cumple el SLA de resolución",
    "n_reasignaciones": "Veces que el ticket cambió de departamento", "es_escalado": "Tuvo al menos una reasignación",
    "min_respuesta_sla": "Minutos de reloj hasta la 1ª respuesta", "min_resolucion_sla": "Minutos de reloj consumidos hasta resolver",
    "min_pausa": "Minutos en pausa (esperando al cliente)", "horas_sla_resolucion": "Horas de reloj consumidas hasta resolver",
    "pct_sla_consumido": "% del SLA de resolución consumido (100 % = límite)",
    "penalizacion_atribuida_eur": "Parte de la penalización del cliente × sprint atribuida al ticket (€)",
    # Calendario y contexto
    "fecha": "Fecha del día", "anio": "Año", "anio_sprint": "Año del sprint", "trimestre": "Trimestre", "mes": "Mes (1–12)",
    "numero": "Número del sprint dentro del año", "fecha_inicio": "Primer día del sprint", "fecha_fin": "Último día del sprint",
    "dias_laborables": "Días laborables del sprint", "n_sprints_anio": "Sprints de ese año (18 o 17)",
    "es_completo": "El sprint está completo dentro del periodo de datos",
    "dia_semana": "Día de la semana (1 = lunes … 7 = domingo)", "es_fin_semana": "Sábado o domingo",
    "es_laborable": "Día laborable en Madrid", "es_festivo_madrid": "Festivo nacional, autonómico o local de Madrid",
    "nombre_festivo": "Nombre del festivo", "es_post_festivo": "Primer día laborable tras un festivo o puente",
    "es_puente": "Día de puente", "temp_max": "Temperatura máxima en Madrid (°C, Open-Meteo)",
    "temp_min": "Temperatura mínima en Madrid (°C, Open-Meteo)", "precipitacion_mm": "Lluvia diaria en Madrid (mm)",
    "es_dia_caluroso": "Temperatura máxima por encima de 35 °C",
    # Agregados diarios
    "tickets_creados": "Tickets abiertos ese día", "p1_creados": "Tickets P1 abiertos ese día",
    "infra_p1_p2_creados": "Incidencias P1/P2 de Infraestructura abiertas ese día",
    "tickets_salida": "Tickets resueltos o cancelados ese día", "backlog_fin_dia": "Tickets abiertos al final del día",
    "cumplidos": "Tickets medidos ese día que cumplen", "incumplidos": "Tickets medidos ese día que incumplen",
    "agentes_activos": "Agentes en plantilla ese día", "agentes_ausentes": "Agentes de vacaciones o baja ese día",
    "pct_agentes_ausentes": "% de la plantilla ausente",
    # Facturación y tramos
    "n_tickets_computables": "Tickets que cuentan para la factura", "n_cumplidos": "Tickets computables que cumplen",
    "n_incumplidos": "Tickets computables que incumplen", "n_p1": "Tickets P1", "n_p1_incumplidos": "Tickets P1 incumplidos",
    "pct_cumplimiento": "% de cumplimiento del SLA de resolución", "pct_incumplimiento": "% de incumplimiento",
    "tipo_tramo": "Tramo del sprint: bonus, neutro o deficiente",
    "pct_desde": "Límite inferior del tramo (% de cumplimiento)", "pct_hasta": "Límite superior del tramo (% de cumplimiento)",
    "pct_ajuste": "% de ajuste aplicado sobre la cuota (con el tope −3,5 % / +3 %)",
    "pct_ajuste_tramo": "% de ajuste que marca el tramo, antes del tope",
    "ajuste_eur": "Ajuste en la factura: positivo = bonus, negativo = penalización (€)",
    "puntos_sobre_tramo_inferior": "Puntos de % que le sobran al cliente antes de caer al tramo de abajo",
    "calculado_en": "Momento en que se congeló la facturación del sprint",
    "bonus_eur": "Bonificación (€)", "penalizacion_eur": "Penalización (€)", "balance_eur": "Bonus − penalización (€)",
    "pct_balance_sobre_cuota": "Balance sobre la cuota (%)", "sprints_facturados": "Sprints facturados",
    "sprints_bonus": "Sprints en tramo bonus", "sprints_deficientes": "Sprints en tramo deficiente",
    "sprints_medidos": "Sprints con tickets medidos",
    # Pareto y perfiles
    "ranking": "Posición en el Pareto", "tickets_incumplidos": "Tickets incumplidos", "pct": "% sobre el total",
    "pct_acumulado": "% acumulado", "clase_abc": "Clase ABC (A = hasta el 80 %, B = hasta el 95 %, C = resto)",
    "tickets": "Tickets", "tickets_mes": "Tickets por mes activo", "tickets_por_100_usuarios": "Tickets por cada 100 usuarios",
    "pct_p1": "% de tickets P1", "pct_escalados": "% de tickets escalados",
}


# Columnas con el mismo nombre que significan otra cosa según la tabla
POR_TABLA = {
    ("agente_ausencia", "fecha_inicio"): "Primer día de la ausencia",
    ("agente_ausencia", "fecha_fin"): "Último día de la ausencia",
    ("agente_ausencia", "dias_laborables"): "Días laborables de ausencia",
    ("dim_agente", "nombre"): "Nombre (ficticio) del agente",
    ("dim_agente", "fecha_alta"): "Fecha de incorporación del agente",
    ("dim_cliente", "nombre"): "Nombre (ficticio) del cliente",
    ("dim_departamento", "nombre"): "Nombre del departamento",
    ("dim_departamento", "rol"): "Qué hace el departamento",
    ("dim_tramo_ajuste", "tipo"): "Tipo de tramo: bonus, neutro o deficiente",
    ("fact_ticket_estado", "inicio"): "Momento en que el ticket entra en este estado",
    ("v_kpis_diarios", "cumplidos"): "Tickets medidos ese día que cumplen",
    ("v_liquidacion_anual", "anio"): "Año de liquidación (el sprint cuenta en el año de su nombre)",
    ("v_pareto_penalizacion", "pct"): "% de la penalización total",
}


def main():
    conn = psycopg2.connect(host=config("DB_HOST"), port=config("DB_PORT"), dbname=config("DB_NAME"),
                            user=config("DB_USER"), password=config("DB_PASSWORD"))
    cur = conn.cursor()
    esquema = config("DB_SCHEMA")
    cur.execute("""
        SELECT c.relname, c.relkind, obj_description(c.oid, 'pg_class')
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %s AND c.relkind IN ('r', 'v')
        ORDER BY c.relkind, c.relname""", (esquema,))
    objetos = cur.fetchall()

    # Claves primarias y ajenas
    cur.execute("""
        SELECT cl.relname, a.attname, co.contype, rf.relname
        FROM pg_constraint co
        JOIN pg_class cl ON cl.oid = co.conrelid
        JOIN pg_namespace n ON n.oid = cl.relnamespace
        JOIN LATERAL unnest(co.conkey) k(attnum) ON true
        JOIN pg_attribute a ON a.attrelid = cl.oid AND a.attnum = k.attnum
        LEFT JOIN pg_class rf ON rf.oid = co.confrelid
        WHERE n.nspname = %s AND co.contype IN ('p', 'f')""", (esquema,))
    claves = {}
    for tabla, col, tipo, ref in cur.fetchall():
        claves.setdefault((tabla, col), []).append("PK" if tipo == "p" else f"FK → {ref}")

    sin_desc = set()
    lineas = [
        "# Diccionario de datos · Brújula Soporte IT",
        "",
        f"Esquema `{esquema}` de PostgreSQL. Generado con `python 05_docs/generar_data_dictionary.py` "
        "(no editar a mano). Los **ejemplos** son valores reales de la base; los datos de negocio son "
        "sintéticos y el clima y los festivos, reales.",
        "",
        "- **Tablas** (`dim_*`, `fact_*`): el modelo en estrella, con claves y restricciones de negocio.",
        "- **Vistas** (`v_*`): la definición única de cada cifra; las usan Power BI y el análisis en Python.",
        "",
        "## Índice",
        "",
    ]
    for nombre, tipo, _ in objetos:
        lineas.append(f"- [{nombre}](#{nombre.replace('_', '_')}) · {'tabla' if tipo == 'r' else 'vista'}")
    for nombre, tipo, comentario in objetos:
        cur.execute(f'SELECT count(*) FROM {esquema}."{nombre}"')
        filas = cur.fetchone()[0]
        cur.execute("""
            SELECT a.attname, format_type(a.atttypid, a.atttypmod), col_description(a.attrelid, a.attnum)
            FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s AND c.relname = %s AND a.attnum > 0 AND NOT a.attisdropped
            ORDER BY a.attnum""", (esquema, nombre))
        columnas = cur.fetchall()
        lineas += ["", f"## {nombre}", "",
                   f"*{'Tabla' if tipo == 'r' else 'Vista'} · {filas:,} filas*".replace(",", "."), ""]
        if comentario:
            lineas += [comentario, ""]
        lineas += ["| Columna | Tipo | Clave | Descripción | Ejemplo |", "|---|---|---|---|---|"]
        for col, tipo_dato, desc in columnas:
            cur.execute(f'SELECT "{col}"::text FROM {esquema}."{nombre}" WHERE "{col}" IS NOT NULL LIMIT 1')
            ej = cur.fetchone()
            ejemplo = (ej[0] if ej else "—")
            ejemplo = ejemplo if len(ejemplo) <= 30 else ejemplo[:27] + "…"
            descripcion = desc or POR_TABLA.get((nombre, col)) or DESCRIPCIONES.get(col)
            if not descripcion:
                sin_desc.add(col)
                descripcion = "—"
            clave = ", ".join(claves.get((nombre, col), []))
            lineas.append(f"| `{col}` | {tipo_dato} | {clave} | {descripcion.replace('|', '/')} | `{ejemplo}` |")
    SALIDA.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"Escrito {SALIDA.relative_to(RAIZ)}: {len(objetos)} objetos")
    if sin_desc:
        print("Columnas sin descripción:", ", ".join(sorted(sin_desc)))


if __name__ == "__main__":
    main()
