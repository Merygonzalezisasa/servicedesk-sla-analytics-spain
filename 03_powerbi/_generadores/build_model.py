"""Genera el modelo semántico (TMDL) de Brujula SLA. Indentación con tabuladores."""
import json, os, sys, textwrap

ROOT = sys.argv[1]
SM = os.path.join(ROOT, "Brujula SLA.SemanticModel")
DEF = os.path.join(SM, "definition")
os.makedirs(os.path.join(DEF, "tables"), exist_ok=True)

def w(path, text):
    text = textwrap.dedent(text).lstrip("\n").replace("    ", "\t")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)

json.dump({"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
           "version": "4.2", "settings": {"qnaEnabled": False}},
          open(os.path.join(SM, "definition.pbism"), "w", encoding="utf-8"), indent=2)

w(os.path.join(DEF, "database.tmdl"), """
    database 'Brujula SLA'
        compatibilityLevel: 1702
        compatibilityMode: powerBI
        language: 3082
""")

TABLES = ["Tickets", "Facturación", "Calendario", "Sprint", "Cliente", "Departamento", "Política SLA", "Objetivos KPI"]
w(os.path.join(DEF, "model.tmdl"), """
    model Model
        culture: es-ES
        defaultPowerBIDataSourceVersion: powerBI_V3
        sourceQueryCulture: es-ES
        discourageImplicitMeasures

        annotation __PBI_TimeIntelligenceEnabled = 0

""" + "".join(f"    ref table '{t}'\n" for t in TABLES))

w(os.path.join(DEF, "expressions.tmdl"), """
    /// Servidor PostgreSQL (host:puerto)
    expression Servidor = "localhost:5432" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]

    /// Base de datos del proyecto
    expression 'Base de datos' = "servicedesk_sla" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
""")

w(os.path.join(DEF, "relationships.tmdl"), """
    /// El sprint de cada día del calendario
    relationship 'Calendario a Sprint'
        fromColumn: Calendario.'Sprint id'
        toColumn: Sprint.Sprint

    /// Relación principal: un ticket cuenta en el día (y sprint) en que se conoce su resultado
    relationship 'Tickets a Calendario (medición)'
        fromColumn: Tickets.'Fecha medición'
        toColumn: Calendario.Fecha

    /// Inactiva: la usan las medidas de entrada de tickets con USERELATIONSHIP
    relationship 'Tickets a Calendario (creación)'
        isActive: false
        fromColumn: Tickets.'Fecha creación'
        toColumn: Calendario.Fecha

    /// Inactiva: la usan las medidas de salida (resueltos o cancelados) y el backlog
    relationship 'Tickets a Calendario (salida)'
        isActive: false
        fromColumn: Tickets.'Fecha salida'
        toColumn: Calendario.Fecha

    relationship 'Tickets a Cliente'
        fromColumn: Tickets.'Cliente id'
        toColumn: Cliente.'Cliente id'

    relationship 'Tickets a Política SLA'
        fromColumn: Tickets.'SLA id'
        toColumn: 'Política SLA'.'SLA id'

    relationship 'Tickets a Departamento'
        fromColumn: Tickets.'Departamento id'
        toColumn: Departamento.'Departamento id'

    relationship 'Facturación a Cliente'
        fromColumn: 'Facturación'.'Cliente id'
        toColumn: Cliente.'Cliente id'

    relationship 'Facturación a Sprint'
        fromColumn: 'Facturación'.'Sprint id'
        toColumn: Sprint.Sprint
""")

def col(name, dtype, src, hidden=False, fmt=None, summarize="none", extra=(), desc=None):
    lines = []
    if desc:
        lines.append(f"    /// {desc}")
    lines.append(f"    column {name}")
    lines.append(f"        dataType: {dtype}")
    if fmt:
        lines.append(f"        formatString: {fmt}")
    if hidden:
        lines.append("        isHidden")
    lines.append(f"        summarizeBy: {summarize}")
    lines.append(f"        sourceColumn: {src}")
    for e in extra:
        lines.append(f"        {e}")
    return "\n".join(lines) + "\n"

def partition(name, m):
    m = textwrap.dedent(m).strip("\n").replace("    ", "\t")
    body = "\n".join("\t\t\t\t" + l for l in m.split("\n"))
    return f"\tpartition '{name}' = m\n\t\tmode: import\n\t\tsource =\n{body}\n"

def measure(name, dax, fmt=None, folder=None, desc=None, fmt_def=None):
    out = []
    if desc:
        out.append(f"\t/// {desc}")
    dax = textwrap.dedent(dax).strip("\n")
    if "\n" in dax:
        body = "\n".join("\t\t\t" + l for l in dax.replace("    ", "\t").split("\n"))
        out.append(f"\tmeasure '{name}' = ```\n{body}\n\t\t\t```")
    else:
        out.append(f"\tmeasure '{name}' = {dax}")
    if fmt:
        out.append(f"\t\tformatString: {fmt}")
    if fmt_def:
        out.append(f"\t\tformatStringDefinition = {fmt_def}")
    if folder:
        out.append(f"\t\tdisplayFolder: {folder}")
    return "\n".join(out) + "\n\n"

def table(fname, header, measures, columns, part):
    cols = "".join(columns).replace("    ", "\t")
    text = header + "\n" + "".join(measures) + cols + "\n" + part
    with open(os.path.join(DEF, "tables", fname + ".tmdl"), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)

PCT, INT, EUR, DEC1 = "0.0%", "#,##0", "#,##0 €", "#,##0.0"
DATE = "dd/mm/yyyy"
SRC = 'Origen = PostgreSQL.Database(Servidor, #"Base de datos"),'

# ------------------------------------------------------------------------------------------
# Tickets
# ------------------------------------------------------------------------------------------
tk_measures = [
    measure("Tickets creados", """
        CALCULATE(
            COUNTROWS(Tickets),
            USERELATIONSHIP(Tickets[Fecha creación], Calendario[Fecha])
        )""", INT, "Volumen", "Tickets que entran en el periodo (por fecha de creación)."),
    measure("Tickets salida", """
        CALCULATE(
            COUNTROWS(Tickets),
            USERELATIONSHIP(Tickets[Fecha salida], Calendario[Fecha])
        )""", INT, "Volumen", "Tickets que dejan de estar abiertos en el periodo: resueltos o cancelados."),
    measure("Ritmo de cierre", "DIVIDE([Tickets salida], [Tickets creados])", PCT, "Volumen",
            "Tickets que salen ÷ tickets que entran. Por encima del 100 % el backlog baja."),
    measure("Backlog al cierre", """
        VAR _fin = MAX(Calendario[Fecha])
        RETURN
            CALCULATE(
                COUNTROWS(Tickets),
                REMOVEFILTERS(Calendario),
                REMOVEFILTERS(Sprint),
                Tickets[Fecha creación] <= _fin,
                ISBLANK(Tickets[Fecha salida]) || Tickets[Fecha salida] > _fin
            )""", INT, "Volumen", "Tickets abiertos al final del último día del periodo (respeta cliente, departamento y SLA)."),
    measure("Tickets computables", "CALCULATE(COUNTROWS(Tickets), Tickets[Computa facturación] = TRUE())", INT, "SLA",
            "Incidencias y peticiones medidas (cumplidas o incumplidas) en el periodo: la base del % que se factura."),
    measure("Tickets cumplidos", "CALCULATE([Tickets computables], Tickets[Cumple resolución] = TRUE())", INT, "SLA",
            "Tickets computables resueltos dentro del SLA."),
    measure("Tickets incumplidos", "[Tickets computables] - [Tickets cumplidos]", INT, "SLA",
            "Tickets computables que agotaron su SLA de resolución."),
    measure("% Cumplimiento SLA", "DIVIDE([Tickets cumplidos], [Tickets computables])", PCT, "SLA",
            "Tickets computables cumplidos ÷ computables (sin ponderar, como en el contrato)."),
    measure("% Incumplimiento", "DIVIDE([Tickets incumplidos], [Tickets computables])", PCT, "SLA",
            "Complemento del % de cumplimiento."),
    measure("SLA 1ª respuesta", "DIVIDE(CALCULATE([Tickets computables], Tickets[Cumple respuesta] = TRUE()), [Tickets computables])",
            PCT, "SLA", "% de tickets computables con la primera respuesta dentro de plazo."),
    measure("SLA P1", "CALCULATE([% Cumplimiento SLA], 'Política SLA'[Prioridad] = \"P1\")", PCT, "SLA",
            "% de cumplimiento de las incidencias críticas (P1). En blanco si no hubo P1 en el periodo."),
    measure("Resolución en primer nivel", """
        DIVIDE(
            CALCULATE(COUNTROWS(Tickets), Tickets[Resuelto] = TRUE(), Tickets[Departamento id] = 1, Tickets[Reasignaciones] = 0),
            CALCULATE(COUNTROWS(Tickets), Tickets[Resuelto] = TRUE())
        )""", PCT, "Operación", "First Level Resolution (HDI): % de tickets resueltos por Service Desk N1 sin escalar."),
    measure("% Escalados", "DIVIDE(CALCULATE(COUNTROWS(Tickets), Tickets[Reasignaciones] > 0), COUNTROWS(Tickets))", PCT, "Operación",
            "% de tickets medidos que pasaron por al menos una reasignación."),
    measure("MTTR (h)", """
        DIVIDE(
            CALCULATE(SUM(Tickets[Minutos resolución]), Tickets[Resuelto] = TRUE()),
            CALCULATE(COUNTROWS(Tickets), Tickets[Resuelto] = TRUE())
        ) / 60""", '0.0" h"', "Operación", "Mean Time To Resolve: horas de reloj de SLA (sin pausas) de los tickets resueltos."),
    measure("1ª respuesta media (min)", "AVERAGE(Tickets[Minutos respuesta])", '0" min"', "Operación",
            "Minutos de reloj de SLA hasta la primera respuesta."),
    measure("Penalización atribuida €", "SUM(Tickets[Penalización atribuida])", EUR, "Facturación",
            "Penalización oficial del cliente-sprint repartida a partes iguales entre sus tickets incumplidos."),
    measure("% Acumulado Pareto", """
        VAR _actual = [Penalización atribuida €]
        VAR _total = CALCULATE([Penalización atribuida €], REMOVEFILTERS(Tickets[Departamento · tipo]))
        VAR _acumulado =
            SUMX(
                FILTER(ALLSELECTED(Tickets[Departamento · tipo]), [Penalización atribuida €] >= _actual),
                [Penalización atribuida €]
            )
        RETURN IF(NOT ISBLANK(_actual), DIVIDE(_acumulado, _total))""", PCT, "Facturación",
            "% acumulado de la penalización, de la categoría que más penaliza a la que menos (curva de Pareto)."),
]
tk_cols = [
    col("Ticket", "string", "ticket_id", hidden=True, desc="Identificador del ticket (TCK-000001)"),
    col("'Fecha creación'", "dateTime", "fecha", hidden=True, fmt=DATE),
    col("'Fecha medición'", "dateTime", "fecha_medicion", hidden=True, fmt=DATE,
        desc="Día en que se conoce el resultado: resolución si cumple, vencimiento si incumple"),
    col("'Fecha salida'", "dateTime", "fecha_salida", hidden=True, fmt=DATE, desc="Día de resolución o cancelación"),
    col("'Cliente id'", "string", "cliente_id", hidden=True),
    col("'SLA id'", "string", "sla_id", hidden=True),
    col("'Departamento id'", "int64", "departamento_id", hidden=True),
    col("'Departamento · tipo'", "string", "departamento_tipo", desc="Departamento que resuelve · tipo de ticket (categoría del Pareto)"),
    col("'Estado SLA'", "string", "estado_sla", desc="cumplido, incumplido, en curso o cancelado"),
    col("'Cumple respuesta'", "boolean", "cumple_respuesta", hidden=True),
    col("'Cumple resolución'", "boolean", "cumple_resolucion", hidden=True),
    col("'Computa facturación'", "boolean", "computa_facturacion", hidden=True),
    col("Resuelto", "boolean", "resuelto", hidden=True),
    col("Reasignaciones", "int64", "n_reasignaciones", desc="Número de veces que el ticket cambió de departamento"),
    col("'Minutos respuesta'", "int64", "min_respuesta_sla", hidden=True),
    col("'Minutos resolución'", "int64", "min_resolucion_sla", hidden=True),
    col("'Penalización atribuida'", "decimal", "penalizacion_atribuida_eur", hidden=True, fmt=EUR),
]
table("Tickets", "/// Un ticket por fila (sintético, SEED=42). Grano: ticket. Corte 2026-01-02 18:00.\ntable Tickets\n",
      tk_measures, tk_cols, partition("Tickets", """
        let
            """ + SRC + """
            Vista = Origen{[Schema = "servicedesk", Item = "v_ticket_enriquecido"]}[Data],
            #"Seleccionadas columnas" = Table.SelectColumns(Vista, {"ticket_id", "fecha", "fecha_medicion", "fecha_resolucion",
                "fecha_cancelacion", "cliente_id", "sla_id", "departamento_id", "departamento", "tipo", "estado_sla",
                "cumple_respuesta", "cumple_resolucion", "computa_facturacion", "n_reasignaciones", "min_respuesta_sla",
                "min_resolucion_sla", "penalizacion_atribuida_eur"}),
            // El ticket deja de estar abierto al resolverse o cancelarse
            #"Añadida fecha de salida" = Table.AddColumn(#"Seleccionadas columnas", "fecha_salida",
                each if [fecha_resolucion] <> null then DateTime.Date([fecha_resolucion])
                     else if [fecha_cancelacion] <> null then DateTime.Date([fecha_cancelacion]) else null, type date),
            #"Añadido indicador de resuelto" = Table.AddColumn(#"Añadida fecha de salida", "resuelto", each [fecha_resolucion] <> null, type logical),
            // Categoría del Pareto: departamento que resuelve y tipo de ticket
            #"Añadida categoría Pareto" = Table.AddColumn(#"Añadido indicador de resuelto", "departamento_tipo",
                each [departamento] & " · " & [tipo], type text),
            #"Quitadas columnas auxiliares" = Table.RemoveColumns(#"Añadida categoría Pareto",
                {"fecha_resolucion", "fecha_cancelacion", "departamento", "tipo"}),
            #"Cambiados tipos" = Table.TransformColumnTypes(#"Quitadas columnas auxiliares", {
                {"fecha", type date}, {"fecha_medicion", type date}, {"departamento_id", Int64.Type},
                {"n_reasignaciones", Int64.Type}, {"min_respuesta_sla", Int64.Type}, {"min_resolucion_sla", Int64.Type},
                {"penalizacion_atribuida_eur", Currency.Type}, {"cumple_respuesta", type logical},
                {"cumple_resolucion", type logical}, {"computa_facturacion", type logical}})
        in
            #"Cambiados tipos"
    """))

# ------------------------------------------------------------------------------------------
# Facturación
# ------------------------------------------------------------------------------------------
fa_measures = [
    measure("Cuota facturada €", "SUM(Facturación[Cuota sprint])", EUR, "Facturación",
            "Cuota de los sprints facturados (cuota anual ÷ nº de sprints del año)."),
    measure("Bonus €", "COALESCE(CALCULATE(SUM(Facturación[Ajuste]), Facturación[Ajuste] > 0), 0)", EUR, "Facturación",
            "Bonificaciones ganadas por superar el tramo de bonus."),
    measure("Penalización €", "COALESCE(-CALCULATE(SUM(Facturación[Ajuste]), Facturación[Ajuste] < 0), 0)", EUR, "Facturación",
            "Penalizaciones (en positivo) por caer en tramo deficiente."),
    measure("Balance €", "COALESCE(SUM(Facturación[Ajuste]), 0)", EUR, "Facturación", "Bonus − penalización."),
    measure("Balance medio por sprint €", "DIVIDE([Balance €], DISTINCTCOUNT(Facturación[Sprint id]))", EUR, "Facturación",
            "Balance ÷ nº de sprints del periodo: comparable entre un sprint y varios."),
    measure("% Penalización sobre cuota", "DIVIDE([Penalización €], [Cuota facturada €])", "0.00%", "Facturación",
            "Parte de la cuota que se pierde en penalizaciones (créditos de servicio)."),
    measure("Cliente-sprints deficientes", "COALESCE(CALCULATE(COUNTROWS(Facturación), Facturación[Tramo] = \"deficiente\"), 0)",
            INT, "Facturación", "Nº de combinaciones cliente × sprint en tramo deficiente."),
    measure("Clientes en tramo deficiente", "DIVIDE([Cliente-sprints deficientes], DISTINCTCOUNT(Facturación[Sprint id]))",
            DEC1, "Facturación", "Clientes en tramo deficiente por sprint (media si hay varios sprints)."),
    measure("% Ingresos en riesgo", """
        DIVIDE(
            CALCULATE(
                [Cuota facturada €],
                Facturación[Puntos sobre tramo inferior] < 1,
                Facturación[Tramo] <> "deficiente",
                NOT ISBLANK(Facturación[% cumplimiento]),
                Facturación[% cumplimiento] < 100
            ),
            [Cuota facturada €]
        ) + 0""", PCT, "Facturación",
            "Cuota de los cliente-sprints que quedaron a menos de 1 punto de caer al tramo inferior ÷ cuota total."),
]
fa_cols = [
    col("'Cliente id'", "string", "cliente_id", hidden=True),
    col("'Sprint id'", "string", "sprint_id", hidden=True),
    col("'Cuota sprint'", "decimal", "cuota_sprint_eur", hidden=True, fmt=EUR),
    col("'Tickets computables'", "int64", "n_tickets_computables", hidden=True),
    col("'Tickets cumplidos'", "int64", "n_cumplidos", hidden=True),
    col("'% cumplimiento'", "decimal", "pct_cumplimiento", hidden=True),
    col("Tramo", "string", "tipo_tramo", desc="bonus, neutro o deficiente"),
    col("Ajuste", "decimal", "ajuste_eur", hidden=True, fmt=EUR),
    col("'Puntos sobre tramo inferior'", "decimal", "puntos_sobre_tramo_inferior", hidden=True),
]
table("Facturación", "/// Facturación OFICIAL por cliente y sprint (la congela sp_calcular_facturacion_sprint). Grano: cliente × sprint.\ntable 'Facturación'\n",
      fa_measures, fa_cols, partition("Facturación", """
        let
            """ + SRC + """
            Vista = Origen{[Schema = "servicedesk", Item = "v_facturacion_sprint"]}[Data],
            #"Seleccionadas columnas" = Table.SelectColumns(Vista, {"cliente_id", "sprint_id", "cuota_sprint_eur",
                "n_tickets_computables", "n_cumplidos", "pct_cumplimiento", "tipo_tramo", "ajuste_eur", "puntos_sobre_tramo_inferior"}),
            #"Cambiados tipos" = Table.TransformColumnTypes(#"Seleccionadas columnas", {
                {"cuota_sprint_eur", Currency.Type}, {"ajuste_eur", Currency.Type}, {"pct_cumplimiento", type number},
                {"puntos_sobre_tramo_inferior", type number}, {"n_tickets_computables", Int64.Type}, {"n_cumplidos", Int64.Type}})
        in
            #"Cambiados tipos"
    """))

# ------------------------------------------------------------------------------------------
# Calendario
# ------------------------------------------------------------------------------------------
ca_measures = [
    measure("% Agentes ausentes", """
        CALCULATE(
            DIVIDE(SUM(Calendario[Agentes ausentes]), SUM(Calendario[Agentes activos])),
            Calendario[Laborable] = TRUE()
        )""", PCT, "Contexto", "Agentes ausentes (vacaciones o baja) ÷ agentes en plantilla, en días laborables."),
    measure("Tickets por agente y día", """
        DIVIDE(
            [Tickets creados],
            CALCULATE(SUM(Calendario[Agentes activos]) - SUM(Calendario[Agentes ausentes]), Calendario[Laborable] = TRUE())
        )""", "0.00", "Contexto", "Tickets que entran ÷ agentes disponibles-día laborable (aproximación a la carga/utilización)."),
]
ca_cols = [
    col("Fecha", "dateTime", "fecha", fmt=DATE, extra=("isKey",)),
    col("'Año natural'", "int64", "anio"),
    col("'Mes número'", "int64", "mes", hidden=True),
    col("Mes", "string", "mes_nombre", extra=("sortByColumn: 'Mes número'",)),
    col("'Año-Mes número'", "int64", "anio_mes_num", hidden=True),
    col("'Año-Mes'", "string", "anio_mes", extra=("sortByColumn: 'Año-Mes número'",)),
    col("'Día de la semana'", "int64", "dia_semana", hidden=True),
    col("'Sprint id'", "string", "sprint_id", hidden=True),
    col("Laborable", "boolean", "es_laborable"),
    col("'Festivo Madrid'", "boolean", "es_festivo_madrid"),
    col("Festivo", "string", "nombre_festivo"),
    col("'Tipo de día'", "string", "tipo_dia", desc="Post-festivo, Lunes, Resto de laborables o No laborable"),
    col("'Temperatura máxima'", "decimal", "temp_max", fmt='0.0" °C"'),
    col("'Día caluroso'", "string", "dia_caluroso", desc="> 35 °C o ≤ 35 °C (Open-Meteo, Madrid)"),
    col("'Incidencias Infra P1/P2'", "int64", "infra_p1_p2_creados", hidden=True),
    col("'Agentes activos'", "int64", "agentes_activos", hidden=True),
    col("'Agentes ausentes'", "int64", "agentes_ausentes", hidden=True),
]
table("Calendario", "/// Un día por fila (2024-01-01 → 2026-01-02): calendario laboral de Madrid, sprint, clima real y ausencias.\ntable Calendario\n\tdataCategory: Time\n",
      ca_measures, ca_cols, partition("Calendario", """
        let
            """ + SRC + """
            Vista = Origen{[Schema = "servicedesk", Item = "v_kpis_diarios"]}[Data],
            #"Seleccionadas columnas" = Table.SelectColumns(Vista, {"fecha", "anio", "mes", "dia_semana", "sprint_id",
                "es_laborable", "es_festivo_madrid", "nombre_festivo", "es_post_festivo", "temp_max", "es_dia_caluroso",
                "infra_p1_p2_creados", "agentes_activos", "agentes_ausentes"}),
            #"Añadido nombre del mes" = Table.AddColumn(#"Seleccionadas columnas", "mes_nombre",
                each {"ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"}{[mes] - 1}, type text),
            #"Añadido año-mes" = Table.AddColumn(#"Añadido nombre del mes", "anio_mes",
                each Text.From([anio]) & "-" & Text.PadStart(Text.From([mes]), 2, "0"), type text),
            #"Añadido año-mes número" = Table.AddColumn(#"Añadido año-mes", "anio_mes_num", each [anio] * 100 + [mes], Int64.Type),
            // Tipo de día para el efecto post-festivo (comparación justa: lunes frente a post-festivo)
            #"Añadido tipo de día" = Table.AddColumn(#"Añadido año-mes número", "tipo_dia",
                each if not [es_laborable] then "No laborable" else if [es_post_festivo] then "Post-festivo"
                     else if [dia_semana] = 1 then "Lunes" else "Resto de laborables", type text),
            #"Añadido día caluroso" = Table.AddColumn(#"Añadido tipo de día", "dia_caluroso",
                each if [es_dia_caluroso] then "> 35 °C" else "≤ 35 °C", type text),
            #"Quitadas columnas auxiliares" = Table.RemoveColumns(#"Añadido día caluroso", {"es_post_festivo", "es_dia_caluroso"}),
            #"Cambiados tipos" = Table.TransformColumnTypes(#"Quitadas columnas auxiliares", {
                {"fecha", type date}, {"anio", Int64.Type}, {"mes", Int64.Type}, {"dia_semana", Int64.Type},
                {"temp_max", type number}, {"infra_p1_p2_creados", Int64.Type}, {"agentes_activos", Int64.Type},
                {"agentes_ausentes", Int64.Type}, {"es_laborable", type logical}, {"es_festivo_madrid", type logical}})
        in
            #"Cambiados tipos"
    """))

# ------------------------------------------------------------------------------------------
# Sprint
# ------------------------------------------------------------------------------------------
sp_cols = [
    col("Sprint", "string", "sprint_id", extra=("isKey", "sortByColumn: Orden"), desc="AAAA-NN por el año en que empieza"),
    col("Año", "int64", "anio_sprint", desc="Año del sprint (2024-18 acaba en enero de 2025 pero es de 2024)"),
    col("Número", "int64", "numero"),
    col("Periodo", "string", "periodo", extra=("sortByColumn: Orden",), desc="Sprint con sus fechas, p. ej. 2024-11 · 29/07–16/08"),
    col("Inicio", "dateTime", "fecha_inicio", fmt=DATE),
    col("Fin", "dateTime", "fecha_fin", fmt=DATE),
    col("'Días laborables'", "int64", "dias_laborables"),
    col("Orden", "int64", "orden", hidden=True, desc="Posición del sprint (1 = 2024-01): sirve para encontrar el sprint anterior"),
]
table("Sprint", "/// Sprints de 3 semanas (lunes → viernes de la 3ª). Unidad de medición del SLA y de facturación.\ntable Sprint\n",
      [measure("Periodo seleccionado", """
        IF(
            HASONEVALUE(Sprint[Sprint]),
            "Sprint " & SELECTEDVALUE(Sprint[Periodo]),
            "Varios sprints (" & COUNTROWS(VALUES(Sprint[Sprint])) & ")"
        )""", None, "Sprint", "Sprint elegido en los filtros, con sus fechas.")],
      sp_cols, partition("Sprint", """
        let
            """ + SRC + """
            Tabla = Origen{[Schema = "servicedesk", Item = "dim_sprint"]}[Data],
            #"Seleccionadas columnas" = Table.SelectColumns(Tabla, {"sprint_id", "anio_sprint", "numero", "fecha_inicio", "fecha_fin", "dias_laborables"}),
            #"Ordenadas filas" = Table.Sort(#"Seleccionadas columnas", {{"fecha_inicio", Order.Ascending}}),
            #"Añadido orden" = Table.AddIndexColumn(#"Ordenadas filas", "orden", 1, 1, Int64.Type),
            #"Añadido periodo" = Table.AddColumn(#"Añadido orden", "periodo",
                each [sprint_id] & " · " & Date.ToText([fecha_inicio], "dd/MM") & "–" & Date.ToText([fecha_fin], "dd/MM"), type text),
            #"Cambiados tipos" = Table.TransformColumnTypes(#"Añadido periodo", {
                {"anio_sprint", Int64.Type}, {"numero", Int64.Type}, {"dias_laborables", Int64.Type},
                {"fecha_inicio", type date}, {"fecha_fin", type date}})
        in
            #"Cambiados tipos"
    """))

# ------------------------------------------------------------------------------------------
# Cliente
# ------------------------------------------------------------------------------------------
cl_cols = [
    col("'Cliente id'", "string", "cliente_id", hidden=True, extra=("isKey",)),
    col("Cliente", "string", "cliente", desc="Nombre ficticio de la empresa cliente"),
    col("Sector", "string", "sector"),
    col("'Comunidad autónoma'", "string", "comunidad_autonoma", extra=("dataCategory: StateOrProvince",)),
    col("'Orden nivel'", "int64", "orden_nivel", hidden=True),
    col("'Nivel de contrato'", "string", "nivel_contrato", extra=("sortByColumn: 'Orden nivel'",), desc="Gold, Silver o Bronze"),
    col("'Objetivo contractual'", "decimal", "objetivo_contractual", fmt="0%", desc="Gold 95 %, Silver 90 %, Bronze 85 %"),
    col("'Contrato y objetivo'", "string", "contrato_objetivo"),
    col("'Cuota anual'", "decimal", "cuota_anual_eur", hidden=True, fmt=EUR),
    col("'Fecha de alta'", "dateTime", "fecha_alta", fmt=DATE),
]
table("Cliente", "/// Empresas cliente ficticias (40) con su nivel de contrato.\ntable Cliente\n",
      [], cl_cols, partition("Cliente", """
        let
            """ + SRC + """
            Vista = Origen{[Schema = "servicedesk", Item = "v_perfil_cliente"]}[Data],
            #"Seleccionadas columnas" = Table.SelectColumns(Vista, {"cliente_id", "cliente", "sector", "comunidad_autonoma",
                "nivel_contrato", "cuota_anual_eur", "fecha_alta"}),
            #"Añadido orden del nivel" = Table.AddColumn(#"Seleccionadas columnas", "orden_nivel",
                each if [nivel_contrato] = "Gold" then 1 else if [nivel_contrato] = "Silver" then 2 else 3, Int64.Type),
            #"Añadido objetivo contractual" = Table.AddColumn(#"Añadido orden del nivel", "objetivo_contractual",
                each if [nivel_contrato] = "Gold" then 0.95 else if [nivel_contrato] = "Silver" then 0.90 else 0.85, type number),
            #"Añadido contrato y objetivo" = Table.AddColumn(#"Añadido objetivo contractual", "contrato_objetivo",
                each [nivel_contrato] & " · objetivo " & Text.From(Number.Round([objetivo_contractual] * 100)) & " %", type text),
            #"Cambiados tipos" = Table.TransformColumnTypes(#"Añadido contrato y objetivo", {
                {"cuota_anual_eur", Currency.Type}, {"fecha_alta", type date}})
        in
            #"Cambiados tipos"
    """))

# ------------------------------------------------------------------------------------------
# Departamento y Política SLA
# ------------------------------------------------------------------------------------------
table("Departamento", "/// Grupos resolutores. Todo ticket entra por Service Desk N1.\ntable Departamento\n", [], [
    col("'Departamento id'", "int64", "departamento_id", hidden=True, extra=("isKey",)),
    col("Departamento", "string", "nombre"),
    col("'Nivel de soporte'", "string", "nivel_soporte"),
], partition("Departamento", """
        let
            """ + SRC + """
            Tabla = Origen{[Schema = "servicedesk", Item = "dim_departamento"]}[Data],
            #"Seleccionadas columnas" = Table.SelectColumns(Tabla, {"departamento_id", "nombre", "nivel_soporte"}),
            #"Cambiados tipos" = Table.TransformColumnTypes(#"Seleccionadas columnas", {{"departamento_id", Int64.Type}})
        in
            #"Cambiados tipos"
    """))

table("Política SLA", "/// Matriz de SLA tipo × prioridad (Ficha §0.2).\ntable 'Política SLA'\n", [], [
    col("'SLA id'", "string", "sla_id", hidden=True, extra=("isKey",)),
    col("Tipo", "string", "tipo", desc="Incidencia, Petición o Tarea"),
    col("Prioridad", "string", "prioridad", desc="P1 (crítica) a P4 (baja)"),
    col("Reloj", "string", "reloj", desc="24x7 (P1) o laboral L–V 9–18 sin festivos de Madrid"),
], partition("Política SLA", """
        let
            """ + SRC + """
            Tabla = Origen{[Schema = "servicedesk", Item = "dim_sla"]}[Data],
            #"Seleccionadas columnas" = Table.SelectColumns(Tabla, {"sla_id", "tipo", "prioridad", "reloj"})
        in
            #"Seleccionadas columnas"
    """))

# ------------------------------------------------------------------------------------------
# Objetivos KPI (tabla de configuración del cuadro de objetivos)
# ------------------------------------------------------------------------------------------
OBJ = [  # id, bloque, orden_bloque, kpi, sentido, objetivo, formato  (dos estados: Cumplido / Incumplido)
    (1, "KPI TICKETS", 1, "Ritmo de cierre", "Mayor es mejor", 1.00, "pct"),
    (2, "KPI TICKETS", 1, "Backlog al cierre", "Menor es mejor", 110, "num"),
    (3, "KPI TICKETS", 1, "Resolución en primer nivel", "Mayor es mejor", 0.65, "pct"),
    (4, "KPI TICKETS", 1, "% Escalados", "Menor es mejor", 0.35, "pct"),
    (5, "SLA", 2, "SLA 1ª respuesta", "Mayor es mejor", 0.95, "pct"),
    (6, "SLA", 2, "SLA resolución", "Mayor es mejor", 0.92, "pct"),
    (7, "SLA", 2, "SLA de los P1", "Mayor es mejor", 0.95, "pct"),
    (8, "NEGOCIO", 3, "Balance medio por sprint", "Mayor es mejor", -5000, "eur"),
    (9, "NEGOCIO", 3, "Penalización sobre la cuota", "Menor es mejor", 0.02, "pct"),
    (10, "NEGOCIO", 3, "Clientes en tramo deficiente", "Menor es mejor", 6, "dec"),
    (11, "NEGOCIO", 3, "Ingresos en riesgo", "Menor es mejor", 0.10, "pct"),
    (12, "OPERACIÓN", 4, "MTTR (horas de SLA)", "Menor es mejor", 17, "h"),
    (13, "OPERACIÓN", 4, "1ª respuesta media", "Menor es mejor", 90, "min"),
    (14, "OPERACIÓN", 4, "Tickets por agente y día", "Menor es mejor", 1.65, "dec2"),
    (15, "OPERACIÓN", 4, "% Agentes ausentes", "Menor es mejor", 0.10, "pct"),
]
def mnum(x):
    return repr(float(x)) if isinstance(x, float) else str(x)
rows = ",\n".join(
    f'                    {{{i}, "{b}", {ob}, "KPI {i}", "{k}", "{s}", {mnum(o)}, "{f}"}}' for i, b, ob, k, s, o, f in OBJ)

VAL = "\n".join(f"    {i}, [{m}]," for i, m in [
    (1, "Ritmo de cierre"), (2, "Backlog al cierre"), (3, "Resolución en primer nivel"), (4, "% Escalados"),
    (5, "SLA 1ª respuesta"), (6, "% Cumplimiento SLA"), (7, "SLA P1"), (8, "Balance medio por sprint €"),
    (9, "% Penalización sobre cuota"), (10, "Clientes en tramo deficiente"), (11, "% Ingresos en riesgo"),
    (12, "MTTR (h)"), (13, "1ª respuesta media (min)"), (14, "Tickets por agente y día"), (15, "% Agentes ausentes")])

FMT = ('SWITCH(SELECTEDVALUE(\'Objetivos KPI\'[Formato]), "pct", "0.0%", "eur", "#,##0 €", "num", "#,##0", '
       '"dec", "0.0", "dec2", "0.00", "h", "0.0"" h""", "min", "0"" min""", "0.0")')

def estado(valor):
    return f"""
        VAR _v = {valor}
        VAR _mayor = SELECTEDVALUE('Objetivos KPI'[Sentido]) = "Mayor es mejor"
        VAR _obj = SELECTEDVALUE('Objetivos KPI'[Objetivo])
        RETURN
            SWITCH(
                TRUE(),
                ISBLANK(_v) || ISBLANK(_obj), BLANK(),
                _mayor && _v >= _obj, "Cumplido",
                NOT _mayor && _v <= _obj, "Cumplido",
                "Incumplido"
            )"""

def contar(estado_txt, medida):
    return f'COUNTROWS(FILTER(ALL(\'Objetivos KPI\'[Id]), [{medida}] = "{estado_txt}")) + 0'

ob_measures = [
    measure("Valor KPI", "SWITCH(\n    SELECTEDVALUE('Objetivos KPI'[Id]),\n" + VAL + "\n    BLANK()\n)", None, "Cuadro de objetivos",
            "Valor del KPI de la fila de Objetivos KPI en contexto (una sola medida para las 15 tarjetas).", fmt_def=FMT),
    measure("Valor KPI sprint anterior", """
        VAR _orden = MAX(Sprint[Orden])
        RETURN
            IF(
                HASONEVALUE(Sprint[Sprint]) && _orden > 1,
                CALCULATE([Valor KPI], REMOVEFILTERS(Sprint), Sprint[Orden] = _orden - 1)
            )""", None, "Cuadro de objetivos", "Valor del KPI en el sprint anterior (solo con un sprint seleccionado).", fmt_def=FMT),
    measure("Estado KPI", estado("[Valor KPI]"), None, "Cuadro de objetivos",
            "Cumplido si el KPI alcanza su objetivo (≥ si mayor es mejor, ≤ si menor es mejor); si no, Incumplido."),
    measure("Estado KPI sprint anterior", estado("[Valor KPI sprint anterior]"), None, "Cuadro de objetivos",
            "Estado del KPI en el sprint anterior."),
    measure("Variación KPI", """
        VAR _v = [Valor KPI]
        VAR _p = [Valor KPI sprint anterior]
        RETURN
            IF(
                NOT ISBLANK(_v) && NOT ISBLANK(_p),
                IF(SELECTEDVALUE('Objetivos KPI'[Formato]) = "pct", _v - _p, DIVIDE(_v - _p, ABS(_p)))
            )""", "0.0%", "Cuadro de objetivos",
            "Cambio frente al sprint anterior: en puntos si el KPI es un %, en % si es una cifra."),
    measure("Variación KPI texto", """
        VAR _d = [Variación KPI]
        VAR _flecha = IF(_d > 0, "↗ ", IF(_d < 0, "↘ ", "→ "))
        RETURN
            IF(
                ISBLANK(_d),
                "—",
                _flecha
                    & IF(
                        SELECTEDVALUE('Objetivos KPI'[Formato]) = "pct",
                        FORMAT(_d * 100, "+0.0;-0.0;0.0") & " pp",
                        FORMAT(_d, "+0.0%;-0.0%;0.0%")
                    )
            )""", None, "Cuadro de objetivos", "Flecha y variación frente al sprint anterior (pp = puntos porcentuales)."),
    measure("Color variación", """
        VAR _d = [Variación KPI]
        VAR _mayor = SELECTEDVALUE('Objetivos KPI'[Sentido]) = "Mayor es mejor"
        RETURN
            SWITCH(
                TRUE(),
                ISBLANK(_d) || _d = 0, "#605E5C",
                (_mayor && _d > 0) || (NOT _mayor && _d < 0), "#1E7B5C",
                "#C0392B"
            )""", None, "Cuadro de objetivos", "Verde si el KPI mejora frente al sprint anterior, rojo si empeora."),
    measure("Color estado", """
        SWITCH(
            [Estado KPI],
            "Cumplido", "#1E7B5C",
            "Incumplido", "#C0392B",
            "#9AA3AD"
        )""", None, "Cuadro de objetivos", "Verde si se cumple el objetivo, rojo si no, gris si no hay datos."),
    measure("Color texto estado", '"#FFFFFF"', None, "Cuadro de objetivos",
            "Texto blanco sobre verde, rojo o gris (contraste AA)."),
    measure("Texto estado", 'COALESCE([Estado KPI], "Sin datos")', None, "Cuadro de objetivos", "Estado para mostrar en la etiqueta."),
    measure("Etiqueta sprint anterior", """
        VAR _orden = MAX(Sprint[Orden])
        VAR _anterior = CALCULATE(MAX(Sprint[Sprint]), REMOVEFILTERS(Sprint), Sprint[Orden] = _orden - 1)
        RETURN IF(HASONEVALUE(Sprint[Sprint]) && NOT ISBLANK(_anterior), "vs sprint " & _anterior, "Elige un sprint")""",
            None, "Cuadro de objetivos", "Texto de referencia: con qué sprint se compara."),
    measure("KPI Cumplido", contar("Cumplido", "Estado KPI"), INT, "Cuadro de objetivos", "Nº de KPI que cumplen su objetivo."),
    measure("KPI Incumplido", contar("Incumplido", "Estado KPI"), INT, "Cuadro de objetivos", "Nº de KPI que no cumplen su objetivo."),
    measure("KPI Cumplido sprint anterior", contar("Cumplido", "Estado KPI sprint anterior"), INT, "Cuadro de objetivos", "Nº de KPI cumplidos en el sprint anterior."),
    measure("KPI Incumplido sprint anterior", contar("Incumplido", "Estado KPI sprint anterior"), INT, "Cuadro de objetivos", "Nº de KPI incumplidos en el sprint anterior."),
]
ob_cols = [
    col("Id", "int64", "Id", hidden=True, extra=("isKey",)),
    col("Bloque", "string", "Bloque", extra=("sortByColumn: 'Orden bloque'",)),
    col("'Orden bloque'", "int64", "Orden bloque", hidden=True),
    col("Código", "string", "Código", extra=("sortByColumn: Id",)),
    col("KPI", "string", "KPI", extra=("sortByColumn: Id",)),
    col("Sentido", "string", "Sentido"),
    col("Objetivo", "double", "Objetivo", desc="Umbral del KPI: se cumple si lo alcanza (≥ o ≤ según el sentido)"),
    col("Formato", "string", "Formato", hidden=True),
]
ob_part = """
        let
            // Objetivo de cada KPI (decidido con la estudiante el 2026-10-19). Dos estados: Cumplido / Incumplido.
            // Para cambiar un objetivo basta con editar su fila: tarjetas y resumen se recalculan solos.
            Objetivos = #table(
                type table [Id = Int64.Type, Bloque = text, #"Orden bloque" = Int64.Type, Código = text, KPI = text,
                    Sentido = text, Objetivo = number, Formato = text],
                {
""" + rows + """
                }
            )
        in
            Objetivos
"""
table("Objetivos KPI", "/// Configuración del cuadro de objetivos: un KPI por fila con sus umbrales. Tabla sin relaciones, por diseño.\ntable 'Objetivos KPI'\n",
      ob_measures, ob_cols, partition("Objetivos KPI", ob_part))
print("ok")
