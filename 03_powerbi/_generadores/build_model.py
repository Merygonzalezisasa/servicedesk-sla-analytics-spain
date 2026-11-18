"""Genera el modelo semántico (TMDL) de Brujula SLA. Indentación con tabuladores."""
import json, os, re, sys, textwrap

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

TABLES = ["Medidas", "Tickets", "Facturación", "Calendario", "Sprint", "Cliente", "Departamento", "Política SLA",
          "Objetivos KPI", "Parámetro KPI", "Tipo detalle"]
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

# Las relaciones no admiten descripción (///): la explicación va en una anotación.
w(os.path.join(DEF, "relationships.tmdl"), """
    relationship 'Calendario a Sprint'
        fromColumn: Calendario.'Sprint id'
        toColumn: Sprint.Sprint

        annotation Descripcion = El sprint de cada día del calendario

    relationship 'Tickets a Calendario (medición)'
        fromColumn: Tickets.'Fecha medición'
        toColumn: Calendario.Fecha

        annotation Descripcion = Relación principal: un ticket cuenta en el día (y sprint) en que se conoce su resultado

    relationship 'Tickets a Calendario (creación)'
        isActive: false
        fromColumn: Tickets.'Fecha creación'
        toColumn: Calendario.Fecha

        annotation Descripcion = Inactiva: la usan las medidas de entrada de tickets con USERELATIONSHIP

    relationship 'Tickets a Calendario (salida)'
        isActive: false
        fromColumn: Tickets.'Fecha salida'
        toColumn: Calendario.Fecha

        annotation Descripcion = Inactiva: la usan las medidas de salida (resueltos o cancelados) y el backlog

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

    relationship 'Objetivos KPI a Parámetro KPI'
        fromColumn: 'Objetivos KPI'.Bloque
        toColumn: 'Parámetro KPI'.Bloque

        annotation Descripcion = Los botones del parámetro filtran los KPI de su bloque (página Detalle de KPIs por tipo)
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

def measure(name, dax, fmt=None, folder=None, desc=None, fmt_def=None, data_category=None):
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
    if folder:
        out.append(f"\t\tdisplayFolder: {folder}")
    if data_category:   # p. ej. ImageUrl: la matriz dibuja el SVG que devuelve la medida
        out.append(f"\t\tdataCategory: {data_category}")
    # formatStringDefinition es un objeto hijo: en TMDL va después de las propiedades
    if fmt_def:
        out.append(f"\t\tformatStringDefinition = {fmt_def}")
    return "\n".join(out) + "\n\n"

MEDIDAS = []   # todas las medidas del modelo: se escriben juntas en la tabla Medidas (ver el final del archivo)

def table(fname, header, measures, columns, part):
    MEDIDAS.extend(measures)
    cols = "".join(columns).replace("    ", "\t")
    text = header + "\n" + cols + "\n" + part
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
    # Página «Tickets por departamento»: departamento × tipo de ticket (por fecha de creación, según los segmentadores)
    measure("% sobre su tipo", """
        DIVIDE(
            [Tickets creados],
            CALCULATE([Tickets creados], ALLSELECTED(Departamento))
        )""", PCT, "Departamento",
            "Parte de los tickets de su tipo (incidencias, peticiones o tareas) que lleva el departamento: cada tipo suma 100 %."),
    measure("% impacta en factura", """
        DIVIDE(
            CALCULATE([Tickets creados], Tickets[Computa facturación] = TRUE()),
            [Tickets creados]
        )""", PCT, "Departamento",
            "Parte de los tickets que cuenta para el % de SLA de facturación (incidencias y peticiones no canceladas)."),
    measure("Texto celda departamento", """
        VAR _n = [Tickets creados]
        RETURN
            IF(
                _n > 0,
                FORMAT(_n, "#,0") & UNICHAR(10)
                    & FORMAT([% sobre su tipo], "0.0 %")
                    & IF(HASONEVALUE('Política SLA'[Tipo]), " de su tipo · ", " del total · ")
                    & FORMAT([% impacta en factura], "0 %") & " impacta"
            )""", None, "Departamento",
            "Celda de la matriz: nº de tickets, % sobre el total de su tipo y % que impacta en la factura."),
    # Celda dibujada como imagen SVG: la cifra grande en negrita y debajo dos líneas pequeñas (como el diseño
    # de referencia), algo que el texto de una matriz no permite. En la URL, % y # van codificados (%25, %23).
    measure("Celda departamento SVG", """
        VAR _n = [Tickets creados]
        VAR _tipo = SELECTEDVALUE('Política SLA'[Tipo])
        VAR _deQue =
            SWITCH(
                TRUE(),
                _tipo = "Incidencia", "de las incidencias",
                _tipo = "Petición", "de las peticiones",
                _tipo = "Tarea", "de las tareas",
                HASONEVALUE(Departamento[Departamento]), "del total",
                "de los tickets"
            )
        VAR _fact = [% impacta en factura]
        VAR _linea2 = FORMAT([% sobre su tipo], "0.0 %") & " " & _deQue
        VAR _linea3 = IF(_fact = 0, "No facturable", FORMAT(_fact, "0 %") & " facturable")
        VAR _svg =
            "<svg xmlns='http://www.w3.org/2000/svg' width='300' height='64'>"
                & "<text x='6' y='23' font-family='Segoe UI, sans-serif' font-size='19' font-weight='700' fill='#1B1F24'>"
                & FORMAT(_n, "#,0") & "</text>"
                & "<text x='6' y='42' font-family='Segoe UI, sans-serif' font-size='11.5' fill='#3B4048'>" & _linea2 & "</text>"
                & "<text x='6' y='58' font-family='Segoe UI, sans-serif' font-size='11.5' fill='#3B4048'>" & _linea3 & "</text>"
                & "</svg>"
        RETURN
            IF(
                _n > 0,
                "data:image/svg+xml;utf8," & SUBSTITUTE(SUBSTITUTE(_svg, "%", "%25"), "#", "%23")
            )""", None, "Departamento",
            "Celda de la matriz como imagen: nº de tickets en grande; debajo, su % dentro del tipo (o del total) y el % "
            "facturable («No facturable» en las tareas).", data_category="ImageUrl"),
    measure("Color celda departamento", """
        VAR _p = [% sobre su tipo]
        RETURN
            IF(
                HASONEVALUE(Departamento[Departamento]) && HASONEVALUE('Política SLA'[Tipo]) && NOT ISBLANK(_p),
                -- más peso dentro de su tipo, azul más intenso
                SWITCH(TRUE(), _p >= 0.40, "#9EC5E8", _p >= 0.20, "#BFD8EE", _p >= 0.10, "#D9E7F5", "#EEF4FB")
            )""", None, "Departamento", "Fondo de la celda según su peso dentro de su tipo de ticket."),
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
    measure("Cuota facturada €", "SUM('Facturación'[Cuota sprint])", EUR, "Facturación",
            "Cuota de los sprints facturados (cuota anual ÷ nº de sprints del año)."),
    measure("Bonus €", "COALESCE(CALCULATE(SUM('Facturación'[Ajuste]), 'Facturación'[Ajuste] > 0), 0)", EUR, "Facturación",
            "Bonificaciones ganadas por superar el tramo de bonus."),
    measure("Penalización €", "COALESCE(-CALCULATE(SUM('Facturación'[Ajuste]), 'Facturación'[Ajuste] < 0), 0)", EUR, "Facturación",
            "Penalizaciones (en positivo) por caer en tramo deficiente."),
    measure("Balance €", "COALESCE(SUM('Facturación'[Ajuste]), 0)", EUR, "Facturación", "Bonus − penalización."),
    measure("Balance medio por sprint €", "DIVIDE([Balance €], DISTINCTCOUNT('Facturación'[Sprint id]))", EUR, "Facturación",
            "Balance ÷ nº de sprints del periodo: comparable entre un sprint y varios."),
    measure("% Penalización sobre cuota", "DIVIDE([Penalización €], [Cuota facturada €])", "0.00%", "Facturación",
            "Parte de la cuota que se pierde en penalizaciones (créditos de servicio)."),
    measure("Cliente-sprints deficientes", "COALESCE(CALCULATE(COUNTROWS('Facturación'), 'Facturación'[Tramo] = \"deficiente\"), 0)",
            INT, "Facturación", "Nº de combinaciones cliente × sprint en tramo deficiente."),
    measure("Clientes en tramo deficiente", "DIVIDE([Cliente-sprints deficientes], DISTINCTCOUNT('Facturación'[Sprint id]))",
            DEC1, "Facturación", "Clientes en tramo deficiente por sprint (media si hay varios sprints)."),
    measure("% Ingresos en riesgo", """
        DIVIDE(
            CALCULATE(
                [Cuota facturada €],
                'Facturación'[Puntos sobre tramo inferior] < 1,
                'Facturación'[Tramo] <> "deficiente",
                NOT ISBLANK('Facturación'[% cumplimiento]),
                'Facturación'[% cumplimiento] < 100
            ),
            [Cuota facturada €]
        ) + 0""", PCT, "Facturación",
            "Cuota de los cliente-sprints que quedaron a menos de 1 punto de caer al tramo inferior ÷ cuota total."),
    # Pareto de la penalización por cliente (página Impacto financiero): clientes de mayor a menor penalización
    measure("% acumulado penalización cliente", """
        VAR _actual = [Penalización €]
        VAR _clientes = FILTER(ALLSELECTED(Cliente[Cliente]), [Penalización €] > 0)
        VAR _total = SUMX(_clientes, [Penalización €])
        VAR _acum = SUMX(FILTER(_clientes, [Penalización €] >= _actual), [Penalización €])
        RETURN IF(_actual > 0 && HASONEVALUE(Cliente[Cliente]), DIVIDE(_acum, _total))""", PCT, "Facturación",
            "% de la penalización que suman este cliente y los que penalizan más que él (curva de Pareto)."),
    measure("Texto acumulado penalización", """
        VAR _p = [% acumulado penalización cliente]
        RETURN IF(NOT ISBLANK(_p), "acum. " & FORMAT(_p, "0 %"))""", None, "Facturación",
            "Etiqueta de detalle de cada barra del Pareto: % acumulado."),
    measure("Color Pareto penalización", """
        VAR _actual = [Penalización €]
        VAR _clientes = FILTER(ALLSELECTED(Cliente[Cliente]), [Penalización €] > 0)
        VAR _total = SUMX(_clientes, [Penalización €])
        VAR _antes = SUMX(FILTER(_clientes, [Penalización €] > _actual), [Penalización €])
        -- naranja intenso hasta el cliente que alcanza el 80 % acumulado; naranja claro el resto
        RETURN IF(_actual > 0, IF(_antes < 0.8 * _total, "#D9692F", "#F2C3A6"))""", None, "Facturación",
            "Color de la barra del Pareto: intenso hasta llegar al 80 % de la penalización, claro el resto."),
    measure("Título Pareto penalización", """
        VAR _clientes = FILTER(ALLSELECTED(Cliente[Cliente]), [Penalización €] > 0)
        VAR _total = SUMX(_clientes, [Penalización €])
        VAR _n80 =
            COUNTROWS(
                FILTER(
                    _clientes,
                    VAR _actual = [Penalización €]
                    RETURN SUMX(FILTER(_clientes, [Penalización €] > _actual), [Penalización €]) < 0.8 * _total
                )
            )
        RETURN
            IF(
                COUNTROWS(_clientes) > 0,
                _n80 & " de " & COUNTROWS(_clientes) & " clientes penalizados concentran el 80 % de la penalización",
                "Ningún cliente penalizado en el periodo"
            )""", None, "Facturación", "Título del Pareto: cuántos clientes concentran el 80 % de la penalización."),
    # Tarjetas de la página Facturación (sprint seleccionado): cifra y variación frente al sprint anterior
    measure("Texto cuota sprint", 'FORMAT([Cuota facturada €] / 1000, "#,0") & " mil €"', None, "Facturación",
            "Facturado en el periodo, en miles de euros (cifra de la tarjeta)."),
    measure("Texto clientes facturados",
            '"Cuota del sprint de los " & DISTINCTCOUNT(\'Facturación\'[Cliente id]) & " clientes"', None, "Facturación",
            "Línea inferior de la tarjeta de facturado: nº de clientes que pagan cuota en el periodo."),
    measure("Texto balance", 'FORMAT([Balance €], "+#,0 €;−#,0 €;0 €")', None, "Facturación",
            "Balance con signo (cifra de la tarjeta)."),
    measure("Variación bonificación", """
        VAR _o = MAX(Sprint[Orden])
        RETURN IF(HASONEVALUE(Sprint[Sprint]) && _o > 1,
                  [Bonus €] - CALCULATE([Bonus €], REMOVEFILTERS(Sprint), Sprint[Orden] = _o - 1))""", EUR, "Facturación",
            "Bonificación del sprint menos la del sprint anterior."),
    measure("Variación penalización", """
        VAR _o = MAX(Sprint[Orden])
        RETURN IF(HASONEVALUE(Sprint[Sprint]) && _o > 1,
                  [Penalización €] - CALCULATE([Penalización €], REMOVEFILTERS(Sprint), Sprint[Orden] = _o - 1))""",
            EUR, "Facturación", "Penalización del sprint menos la del sprint anterior."),
    measure("Variación balance", """
        VAR _o = MAX(Sprint[Orden])
        RETURN IF(HASONEVALUE(Sprint[Sprint]) && _o > 1,
                  [Balance €] - CALCULATE([Balance €], REMOVEFILTERS(Sprint), Sprint[Orden] = _o - 1))""", EUR, "Facturación",
            "Balance del sprint menos el del sprint anterior."),
    measure("Texto variación bonificación", """
        VAR _d = [Variación bonificación]
        RETURN IF(ISBLANK(_d), "Sin sprint anterior",
                  IF(_d > 0, "↗ ", IF(_d < 0, "↘ ", "→ ")) & FORMAT(_d, "+#,0 €;−#,0 €;0 €") & " vs anterior")""",
            None, "Facturación", "Línea inferior de la tarjeta de bonificación."),
    measure("Texto variación penalización", """
        VAR _d = [Variación penalización]
        RETURN IF(ISBLANK(_d), "Sin sprint anterior",
                  IF(_d > 0, "↗ ", IF(_d < 0, "↘ ", "→ ")) & FORMAT(_d, "+#,0 €;−#,0 €;0 €") & " vs anterior")""",
            None, "Facturación", "Línea inferior de la tarjeta de penalización."),
    measure("Texto variación balance", """
        VAR _d = [Variación balance]
        RETURN IF(ISBLANK(_d), "Sin sprint anterior",
                  IF(_d > 0, "↗ ", IF(_d < 0, "↘ ", "→ ")) & FORMAT(_d, "+#,0 €;−#,0 €;0 €") & " vs anterior")""",
            None, "Facturación", "Línea inferior de la tarjeta de balance."),
    # Verde si mejora y rojo si empeora: subir es bueno en bonificación y balance, y malo en penalización
    measure("Color variación bonificación",
            'VAR _d = [Variación bonificación] RETURN SWITCH(TRUE(), ISBLANK(_d) || _d = 0, "#605E5C", _d > 0, "#1E7B5C", "#C0392B")',
            None, "Facturación", "Verde si la bonificación sube, rojo si baja."),
    measure("Color variación penalización",
            'VAR _d = [Variación penalización] RETURN SWITCH(TRUE(), ISBLANK(_d) || _d = 0, "#605E5C", _d < 0, "#1E7B5C", "#C0392B")',
            None, "Facturación", "Verde si la penalización baja, rojo si sube."),
    measure("Color variación balance",
            'VAR _d = [Variación balance] RETURN SWITCH(TRUE(), ISBLANK(_d) || _d = 0, "#605E5C", _d > 0, "#1E7B5C", "#C0392B")',
            None, "Facturación", "Verde si el balance sube, rojo si baja."),
    # Leyendas de las tarjetas de la página Impacto económico acumulado
    measure("Texto sprints analizados",
            'DISTINCTCOUNT('Facturación'[Sprint id]) & " sprints analizados"', None, "Facturación",
            "Leyenda de la tarjeta de facturación acumulada."),
    measure("Texto % bonificación sobre cuota",
            'FORMAT(DIVIDE([Bonus €], [Cuota facturada €]) * 100, "0.00") & " % de la facturación"', None, "Facturación",
            "Leyenda de la tarjeta de bonificación acumulada."),
    measure("Texto % penalización sobre cuota",
            'FORMAT([% Penalización sobre cuota] * 100, "0.00") & " % de la facturación"', None, "Facturación",
            "Leyenda de la tarjeta de penalización acumulada."),
    measure("Texto % balance sobre cuota",
            'FORMAT(DIVIDE([Balance €], [Cuota facturada €]) * 100, "0.00;−0.00;0.00") & " % de la facturación"', None, "Facturación",
            "Leyenda de la tarjeta de balance económico neto."),
    measure("Color balance", 'IF([Balance €] < 0, "#C0392B", "#1E7B5C")', None, "Facturación",
            "Rojo si el balance es negativo, verde si es positivo o cero."),
    measure("Referencia 80 %", "IF(HASONEVALUE(Cliente[Cliente]) && [Penalización €] > 0, 0.8)", "0%", "Facturación",
            "Línea discontinua del 80 % en el Pareto de penalización por cliente."),
    # Gráfico de barras divergentes de la página Facturación: bonificación hacia arriba, penalización hacia abajo
    measure("Penalización negativa €", "-[Penalización €]", EUR, "Facturación",
            "Penalización en negativo, para dibujarla hacia abajo frente a la bonificación."),
    measure("Título bonificación y penalización", """
        VAR _bonus = CALCULATE([Bonus €], REMOVEFILTERS(Sprint))
        VAR _pen = CALCULATE([Penalización €], REMOVEFILTERS(Sprint))
        VAR _conDatos = FILTER(ALL(Sprint), CALCULATE(NOT ISEMPTY('Facturación')))
        VAR _desde = MINX(_conDatos, Sprint[Año])
        VAR _hasta = MAXX(_conDatos, Sprint[Año])
        RETURN
            "Bonificación y penalización por sprint · " & _desde & IF(_hasta <> _desde, "–" & _hasta) & ": "
                & FORMAT(_bonus / 1000, "#,0") & " mil € frente a " & FORMAT(_pen / 1000, "#,0") & " mil €"
        """, None, "Facturación", "Título del gráfico de barras: totales de bonificación y penalización de todos los sprints."),
    # Tabla de clientes de la página Facturación: el KPI que penaliza, cliente a cliente, en el sprint elegido
    # Estas tres solo tienen sentido cliente a cliente: con ISINSCOPE quedan vacías en la fila Total de la matriz
    measure("% SLA del sprint",
            "IF(ISINSCOPE(Cliente[Cliente]), DIVIDE(SUM('Facturación'[Tickets cumplidos]), SUM('Facturación'[Tickets computables])))",
            PCT, "Facturación",
            "% de cumplimiento del SLA de resolución con el que se factura (cumplidos ÷ computables), por cliente; vacío en totales."),
    measure("Tickets computables del sprint", "IF(ISINSCOPE(Cliente[Cliente]), SUM('Facturación'[Tickets computables]))",
            INT, "Facturación",
            "Tickets que entran en el % de facturación (incidencias y peticiones, sin cancelados), por cliente; vacío en totales."),
    measure("Incumplidos del sprint",
            "IF(ISINSCOPE(Cliente[Cliente]), SUM('Facturación'[Tickets computables]) - SUM('Facturación'[Tickets cumplidos]))",
            INT, "Facturación",
            "Tickets computables resueltos fuera del plazo de resolución, por cliente; vacío en totales."),
    measure("Nivel", "SELECTEDVALUE(Cliente[Nivel de contrato])", None, "Facturación",
            "Nivel de contrato del cliente en contexto (para mostrarlo como columna en la matriz de clientes)."),
    measure("Umbral de penalización", """
        VAR _nivel = SELECTEDVALUE(Cliente[Nivel de contrato])
        RETURN
            SWITCH(
                TRUE(),
                ISBLANK(_nivel), BLANK(),
                _nivel = "Bronze", "Sin penalización",
                "< " & FORMAT(SELECTEDVALUE(Cliente[Objetivo contractual]), "0 %")
            )""", None, "Facturación",
            "Por debajo de este % el cliente penaliza (Ficha §0.3): su objetivo contractual. Bronze no penaliza nunca."),
    # Página «Riesgo por cliente»: % de SLA de resolución de cada cliente Gold/Silver en los últimos 6 sprints
    measure("Último sprint facturado", "MAXX(FILTER(ALL(Sprint), CALCULATE(NOT ISEMPTY('Facturación'))), Sprint[Orden])",
            INT, "Facturación", "Orden del último sprint con facturación (fin de la ventana de 6 sprints)."),
    # La ventana de 6 sprints va dentro de la medida (vacía fuera de ella): un filtro de visual sobre una medida en una
    # matriz se evalúa por fila, sin el sprint, y dejaba la matriz vacía. Las columnas sin ningún valor no se muestran.
    measure("% SLA celda riesgo", """
        VAR _pct =
            DIVIDE(SUM('Facturación'[Tickets cumplidos]), SUM('Facturación'[Tickets computables]))
        VAR _u = [Último sprint facturado]
        VAR _o = MAX(Sprint[Orden])
        RETURN
            IF(
                HASONEVALUE(Sprint[Sprint]),
                IF(_o > _u - 6 && _o <= _u, _pct),
                -- fuera de un sprint concreto (total de la fila, oculto): margen sobre el objetivo en el último
                -- sprint, que es por lo que se ordena la matriz (de menor a mayor margen)
                CALCULATE(
                    DIVIDE(SUM('Facturación'[Tickets cumplidos]), SUM('Facturación'[Tickets computables])),
                    FILTER(ALL(Sprint), Sprint[Orden] = _u)
                ) - SELECTEDVALUE(Cliente[Objetivo contractual])
            )""", PCT, "Facturación",
            "% de SLA de resolución del cliente en el sprint; en el total de la fila, su margen en el último sprint (orden)."),
    measure("Color tramo SLA", """
        VAR _p = DIVIDE(SUM('Facturación'[Tickets cumplidos]), SUM('Facturación'[Tickets computables]))
        VAR _n = SELECTEDVALUE(Cliente[Nivel de contrato])
        VAR _u = [Último sprint facturado]
        VAR _o = MAX(Sprint[Orden])
        RETURN
            IF(
                NOT ISBLANK(_p) && HASONEVALUE(Sprint[Sprint]) && _o > _u - 6 && _o <= _u,
                -- tramos del contrato (Ficha §0.3): bonus azul, neutro gris, deficiente leve / medio / máximo en naranjas
                SWITCH(
                    _n,
                    "Gold", SWITCH(TRUE(), _p >= 0.98, "#CFE0F3", _p >= 0.95, "#F1F3F6", _p >= 0.92, "#FBE0CC",
                                   _p >= 0.88, "#F7C39E", "#F2A26F"),
                    "Silver", SWITCH(TRUE(), _p >= 0.95, "#CFE0F3", _p >= 0.90, "#F1F3F6", _p >= 0.85, "#FBE0CC",
                                     "#F2A26F")
                )
            )""", None, "Facturación", "Color de fondo de la celda según el tramo del cliente en ese sprint."),
    measure("Título riesgo clientes", """
        VAR _u = [Último sprint facturado]
        VAR _clientes = CALCULATETABLE(VALUES(Cliente[Cliente]), Cliente[Nivel de contrato] IN {"Gold", "Silver"})
        VAR _riesgo =
            COUNTROWS(
                FILTER(
                    _clientes,
                    VAR _p = CALCULATE(
                        DIVIDE(SUM('Facturación'[Tickets cumplidos]), SUM('Facturación'[Tickets computables])),
                        FILTER(ALL(Sprint), Sprint[Orden] = _u)
                    )
                    VAR _obj = CALCULATE(SELECTEDVALUE(Cliente[Objetivo contractual]))
                    RETURN NOT ISBLANK(_p) && _p < _obj + 0.01
                )
            ) + 0
        VAR _sprint = CALCULATE(MAX(Sprint[Sprint]), FILTER(ALL(Sprint), Sprint[Orden] = _u))
        RETURN
            _riesgo & " de " & COUNTROWS(_clientes) & " clientes Gold y Silver están en tramo deficiente o a menos de "
                & "1 pp de su objetivo (sprint " & _sprint & ")"
        """, None, "Facturación",
            "Título de la página Riesgo por cliente: clientes en tramo deficiente o a menos de 1 pp de su objetivo."),
    measure("Cumple umbral SLA", """
        VAR _pct = [% SLA del sprint]
        RETURN
            IF(
                NOT ISBLANK(_pct) && HASONEVALUE(Cliente[Cliente]),
                IF(_pct >= SELECTEDVALUE(Cliente[Objetivo contractual]), 1, 0)
            )""", INT, "Facturación",
            "1 si el cliente alcanza su umbral de penalización en el sprint, 0 si no (icono ✓/✗ de la matriz de clientes)."),
    measure("Color % SLA del sprint", """
        VAR _nivel = SELECTEDVALUE(Cliente[Nivel de contrato])
        VAR _pct = [% SLA del sprint]
        RETURN
            IF(
                _nivel <> "Bronze" && NOT ISBLANK(_pct) && _pct < SELECTEDVALUE(Cliente[Objetivo contractual]),
                "#C0392B",
                "#1B1F24"
            )""", None, "Facturación", "Rojo si el % del sprint queda por debajo del umbral de penalización."),
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
    # Etiqueta corta para ejes: «2024-01, 02, 03 … 2025-01, 02…». Los números se repiten cada año, así que se les añade
    # un carácter invisible por año (UNICHAR 8203) para que Power BI no junte en una barra los «02» de años distintos.
    "    /// Etiqueta corta para ejes: año completo solo en el primer sprint del año\n"
    "    column 'Etiqueta eje' = IF(Sprint[Número] = 1, Sprint[Sprint], FORMAT(Sprint[Número], \"00\") & "
    "REPT(UNICHAR(8203), Sprint[Año] - 2024))\n"
    "        dataType: string\n"
    "        summarizeBy: none\n"
    "        sortByColumn: Orden\n",
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
        VAR _obj = [Objetivo KPI]
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
    # KPI 6: el umbral que penaliza va por contrato (Ficha §0.3); si el filtro deja un único nivel o cliente se usa ese
    measure("Objetivo KPI", """
        VAR _base = SELECTEDVALUE('Objetivos KPI'[Objetivo])
        VAR _contrato = SELECTEDVALUE(Cliente[Objetivo contractual])
        RETURN
            IF(SELECTEDVALUE('Objetivos KPI'[Id]) = 6 && NOT ISBLANK(_contrato), _contrato, _base)""",
            None, "Cuadro de objetivos",
            "Objetivo con el que se compara el KPI. En el KPI 6, si el filtro deja un único nivel o cliente, usa su "
            "umbral de contrato (Gold 95 %, Silver 90 %, Bronze 85 %); si no, el de Objetivos KPI.", fmt_def=FMT),
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
    # Etiqueta de estado en tono suave: fondo claro, borde medio y texto oscuro del mismo color (contraste AA)
    measure("Color estado", """
        SWITCH(
            [Estado KPI],
            "Cumplido", "#E3F2EA",
            "Incumplido", "#FBE4E2",
            "#EEF0F3"
        )""", None, "Cuadro de objetivos", "Fondo de la etiqueta: verde claro si se cumple, rojo claro si no, gris si no hay datos."),
    measure("Color borde estado", """
        SWITCH(
            [Estado KPI],
            "Cumplido", "#9CCFB5",
            "Incumplido", "#E8A39C",
            "#C5CBD3"
        )""", None, "Cuadro de objetivos", "Borde de la etiqueta de estado, en un tono intermedio del mismo color."),
    measure("Color texto estado", """
        SWITCH(
            [Estado KPI],
            "Cumplido", "#1E6B4A",
            "Incumplido", "#A93226",
            "#5A6270"
        )""", None, "Cuadro de objetivos", "Texto verde oscuro o rojo oscuro sobre su fondo claro (contraste AA)."),
    measure("Texto estado", """
        SWITCH(
            [Estado KPI],
            "Cumplido", "✓ Cumplido",
            "Incumplido", "✕ Incumplido",
            "Sin datos"
        )""", None, "Cuadro de objetivos", "Estado con icono para mostrar en la etiqueta."),
    measure("Texto objetivo KPI", """
        VAR _obj = [Objetivo KPI]
        VAR _signo = IF(SELECTEDVALUE('Objetivos KPI'[Sentido]) = "Mayor es mejor", "≥ ", "≤ ")
        VAR _txt =
            SWITCH(
                SELECTEDVALUE('Objetivos KPI'[Formato]),
                "pct", FORMAT(_obj, "0%"),
                "eur", FORMAT(_obj, "#,##0") & " €",
                "num", FORMAT(_obj, "#,##0"),
                "dec2", FORMAT(_obj, "0.00"),
                "h", FORMAT(_obj, "0") & " h",
                "min", FORMAT(_obj, "0") & " min",
                FORMAT(_obj, "0")
            )
        RETURN
            IF(NOT ISBLANK(_obj), "Objetivo " & _signo & _txt)""", None, "Cuadro de objetivos",
            "Umbral con el que se compara el KPI, con su sentido (≥ / ≤), para mostrarlo bajo el estado de la tarjeta."),
    measure("Etiqueta sprint anterior", """
        VAR _orden = MAX(Sprint[Orden])
        VAR _anterior = CALCULATE(MAX(Sprint[Sprint]), REMOVEFILTERS(Sprint), Sprint[Orden] = _orden - 1)
        RETURN IF(HASONEVALUE(Sprint[Sprint]) && NOT ISBLANK(_anterior), "vs sprint " & _anterior, "Elige un sprint")""",
            None, "Cuadro de objetivos", "Texto de referencia: con qué sprint se compara."),
    measure("KPI Cumplido", contar("Cumplido", "Estado KPI"), INT, "Cuadro de objetivos", "Nº de KPI que cumplen su objetivo."),
    measure("KPI Incumplido", contar("Incumplido", "Estado KPI"), INT, "Cuadro de objetivos", "Nº de KPI que no cumplen su objetivo."),
    measure("KPI Cumplido sprint anterior", contar("Cumplido", "Estado KPI sprint anterior"), INT, "Cuadro de objetivos", "Nº de KPI cumplidos en el sprint anterior."),
    measure("KPI Incumplido sprint anterior", contar("Incumplido", "Estado KPI sprint anterior"), INT, "Cuadro de objetivos", "Nº de KPI incumplidos en el sprint anterior."),
    # Cabecera «Objetivos cumplidos»: el total son los KPI con datos (cumplidos + incumplidos)
    measure("Texto total objetivos", '"de " & ([KPI Cumplido] + [KPI Incumplido])', None, "Cuadro de objetivos",
            "«de N» junto al nº de cumplidos: N = KPI con datos en el periodo."),
    measure("Texto sprint anterior objetivos", """
        VAR _c = [KPI Cumplido]
        VAR _p = [KPI Cumplido sprint anterior]
        VAR _pt = _p + [KPI Incumplido sprint anterior]
        RETURN
            IF(
                _pt = 0,
                "Sin sprint anterior para comparar",
                "Sprint anterior: " & _p & " de " & _pt & " ("
                    & SWITCH(TRUE(), _c > _p, "mejora", _c < _p, "empeora", "igual") & ")"
            )""", None, "Cuadro de objetivos",
            "Cumplidos del sprint anterior y si el sprint actual mejora, empeora o queda igual."),
    measure("Texto leyenda cumplidos", '"✓  " & [KPI Cumplido] & " cumplidos"', None, "Cuadro de objetivos",
            "Leyenda de la barra de la cabecera: nº de KPI cumplidos."),
    measure("Texto leyenda incumplidos", '"✕  " & [KPI Incumplido] & " incumplidos"', None, "Cuadro de objetivos",
            "Leyenda de la barra de la cabecera: nº de KPI incumplidos."),
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
table("Objetivos KPI", "/// Configuración del cuadro de objetivos: un KPI por fila con sus umbrales. Solo la filtra el Parámetro KPI (por bloque).\ntable 'Objetivos KPI'\n",
      ob_measures, ob_cols, partition("Objetivos KPI", ob_part))

# ------------------------------------------------------------------------------------------
# Parámetro KPI: botones de bloque de la página «Detalle de KPIs por tipo» y medidas de esa matriz
# (filas KPI → tipo de ticket; la fila del KPI es el total de los tres tipos)
# ------------------------------------------------------------------------------------------
SIN_TIPO = "{8, 9, 10, 11, 15}"   # KPI que no se pueden separar por tipo de ticket (cliente-sprint o plantilla)
KPI_ID = "SELECTEDVALUE('Objetivos KPI'[Id])"
RESUELTOS = "CALCULATE(COUNTROWS(Tickets), Tickets[Resuelto] = TRUE())"
# Cartera del periodo: abiertos al empezar el primer día + los que entran (base del backlog al cierre)
CARTERA = ("CALCULATE(COUNTROWS(Tickets), REMOVEFILTERS(Calendario), REMOVEFILTERS(Sprint), "
           "Tickets[Fecha creación] < MIN(Calendario[Fecha]), "
           "ISBLANK(Tickets[Fecha salida]) || Tickets[Fecha salida] >= MIN(Calendario[Fecha])) + [Tickets creados]")
TIPO = "SELECTEDVALUE('Tipo detalle'[Tipo], \"Total\")"
KPI_TIEMPO = "{12, 13}"           # KPI de tiempo medio: MTTR y 1ª respuesta media

def por_tipo(expr):
    """Fila «Total»: la expresión tal cual; filas Incidencia / Petición / Tarea: la misma expresión filtrada por ese
    tipo (KEEPFILTERS respeta el segmentador Tipo). Los KPI que no dependen del tipo solo salen en la fila Total.
    Vacía si el KPI de la fila no está en el bloque elegido con los botones: así la matriz no muestra su fila."""
    e = textwrap.dedent(expr).strip("\n")
    a = textwrap.indent(e, " " * 20)
    b = textwrap.indent(e, " " * 28)
    return f"""
        VAR _t = {TIPO}
        RETURN
            IF(
                NOT ISBLANK({KPI_ID}),
                IF(
                    _t = "Total",
{a},
                    IF(
                        NOT ({KPI_ID} IN {SIN_TIPO}),
                        CALCULATE(
{b},
                            KEEPFILTERS('Política SLA'[Tipo] = _t)
                        )
                    )
                )
            )"""

pk_measures = [
    measure("Tickets detalle KPI", por_tipo(f"""
        IF(NOT ({KPI_ID} IN {SIN_TIPO}), [Tickets creados])"""), INT, "Detalle KPI",
            "Tickets creados en el periodo, en la fila Total o por tipo (vacío en los KPI que no dependen de tickets)."),
    measure("Tickets que computan KPI", por_tipo(f"""
        SWITCH(
            {KPI_ID},
            1, [Tickets creados],
            2, {CARTERA},
            3, {RESUELTOS},
            4, COUNTROWS(Tickets),
            5, [Tickets computables],
            6, [Tickets computables],
            7, CALCULATE([Tickets computables], 'Política SLA'[Prioridad] = "P1"),
            12, {RESUELTOS},
            13, COUNT(Tickets[Minutos respuesta]),
            14, [Tickets creados]
        )"""), INT, "Detalle KPI",
            "Tickets que entran en el cálculo de cada KPI (su base; en el backlog, la cartera: abiertos al empezar + entradas); vacío en los KPI que no se calculan con tickets."),
    measure("Tickets incumplidos KPI", por_tipo(f"""
        VAR _obj = SELECTEDVALUE('Objetivos KPI'[Objetivo])
        VAR _n =
            SWITCH(
                {KPI_ID},
                1, [Tickets salida],
                2, [Backlog al cierre],
                3, {RESUELTOS}
                    - CALCULATE(COUNTROWS(Tickets), Tickets[Resuelto] = TRUE(), Tickets[Departamento id] = 1, Tickets[Reasignaciones] = 0),
                4, CALCULATE(COUNTROWS(Tickets), Tickets[Reasignaciones] > 0),
                5, [Tickets computables] - CALCULATE([Tickets computables], Tickets[Cumple respuesta] = TRUE()),
                6, [Tickets incumplidos],
                7, CALCULATE([Tickets incumplidos], 'Política SLA'[Prioridad] = "P1"),
                12, CALCULATE(COUNTROWS(Tickets), Tickets[Resuelto] = TRUE(), Tickets[Minutos resolución] > _obj * 60),
                13, CALCULATE(COUNTROWS(Tickets), Tickets[Minutos respuesta] > _obj)
            )
        RETURN IF(NOT ISBLANK(_n), _n + 0)"""), INT, "Detalle KPI",
            "Columna «Valor medido»: tickets que salieron en el periodo (KPI 1, resueltos o cancelados), abiertos al cierre (KPI 2) o que restan al KPI: no resueltos en N1 (KPI 3), escalados (4), fuera de plazo de respuesta (5) o "
            "de resolución (6 y 7), o por encima del objetivo de tiempo: más de 17 h de SLA en resolverse (12) o más de "
            "90 min en la 1ª respuesta (13). Vacío en los KPI que son recuentos o ratios."),
    measure("Objetivo detalle KPI", f"""
        IF(
            {TIPO} = "Total" && NOT ISBLANK({KPI_ID}),
            SUBSTITUTE([Texto objetivo KPI], "Objetivo ", "")
        )""", None, "Detalle KPI", "Objetivo del KPI (≥ / ≤), solo en la fila Total: es el mismo para los tres tipos."),
    measure("Media KPI detalle", por_tipo("[Valor KPI]"), None, "Detalle KPI",
            "Valor del KPI tal como sale en las tarjetas (en los KPI de tiempo, la media), en la fila Total y por tipo.",
            fmt_def=FMT),
    measure("Valor KPI detalle", f"""
        SWITCH(
            TRUE(),
            {KPI_ID} IN {KPI_TIEMPO},
                DIVIDE([Tickets que computan KPI] - [Tickets incumplidos KPI], [Tickets que computan KPI]),
            {KPI_ID} = 2,
                1 - DIVIDE([Tickets incumplidos KPI], [Tickets que computan KPI]),
            [Media KPI detalle]
        )""", None, "Detalle KPI",
            "Columna «% cumplimiento»: en los KPI de tiempo (12 y 13), % de tickets dentro del objetivo de tiempo "
            "((computables − incumplidos) ÷ computables); en el backlog (2), % de la cartera del periodo que se cerró "
            "(100 % − abiertos al cierre ÷ cartera); en el resto, el valor del KPI.",
            fmt_def=f'IF({KPI_ID} IN {{2, 12, 13}}, "0.0%", {FMT})'),
    measure("Tiempo medio detalle", f"""
        VAR _m = [Media KPI detalle]
        RETURN
            SWITCH(
                TRUE(),
                ISBLANK([Fondo fila detalle KPI]), BLANK(),
                {KPI_ID} = 12, IF(NOT ISBLANK(_m), FORMAT(_m, "0.0") & " h"),
                {KPI_ID} = 13, IF(NOT ISBLANK(_m), FORMAT(_m, "0") & " min"),
                "No aplica"
            )""", None, "Detalle KPI",
            "Columna «Tiempo medio»: la media de los KPI de tiempo (MTTR en horas de SLA, 1ª respuesta en minutos); "
            "«No aplica» en el resto."),
    measure("Color tiempo medio detalle", f"""
        IF(
            NOT ISBLANK([Fondo fila detalle KPI]),
            IF({KPI_ID} IN {KPI_TIEMPO}, [Color valor KPI detalle], "#8A9099")
        )""", None, "Detalle KPI",
            "Color de «Tiempo medio»: verde o rojo según la media frente al objetivo; gris en «No aplica»."),
    measure("Color valor KPI detalle", """
        VAR _v = [Media KPI detalle]
        VAR _mayor = SELECTEDVALUE('Objetivos KPI'[Sentido]) = "Mayor es mejor"
        VAR _obj = [Objetivo KPI]
        RETURN
            SWITCH(
                TRUE(),
                ISBLANK(_v), BLANK(),
                ISBLANK(_obj), "#1B1F24",
                (_mayor && _v >= _obj) || (NOT _mayor && _v <= _obj), "#1E6B4A",
                "#A93226"
            )""", None, "Detalle KPI", "Verde oscuro si el KPI cumple su objetivo (en los de tiempo, si la media lo cumple), rojo oscuro si no."),
    measure("Fondo fila detalle KPI", f"""
        IF(
            NOT ISBLANK({KPI_ID}),
            IF({TIPO} = "Total", "#EEF3F9", IF(NOT ({KPI_ID} IN {SIN_TIPO}), "#FFFFFF"))
        )""", None, "Detalle KPI",
            "Fondo azul muy claro en la fila Total de cada KPI y blanco en las filas por tipo."),
    measure("Penalizado KPI €", por_tipo(f"""
        VAR _p = [Penalización atribuida €]
        RETURN IF({KPI_ID} = 6 && _p > 0, _p)"""), EUR, "Detalle KPI",
            "Penalización del KPI 6 (el único que penaliza): la de cada ticket incumplido, sumada por tipo."),
    measure("Bonificado KPI €", por_tipo(f"""
        IF(
            {KPI_ID} = 6,
            VAR _b =
                SUMX(
                    FILTER('Facturación', 'Facturación'[Ajuste] > 0),
                    VAR _c = 'Facturación'[Cliente id]
                    VAR _s = 'Facturación'[Sprint id]
                    VAR _deTipo =
                        CALCULATE([Tickets cumplidos], REMOVEFILTERS(Cliente), REMOVEFILTERS(Sprint),
                                  Cliente[Cliente id] = _c, Sprint[Sprint] = _s)
                    VAR _todos =
                        CALCULATE([Tickets cumplidos], REMOVEFILTERS(Cliente), REMOVEFILTERS(Sprint),
                                  REMOVEFILTERS('Política SLA'), Cliente[Cliente id] = _c, Sprint[Sprint] = _s)
                    RETURN 'Facturación'[Ajuste] * DIVIDE(_deTipo, _todos)
                )
            RETURN IF(_b > 0, _b)
        )"""), EUR, "Detalle KPI",
            "Bonificación del KPI 6 repartida entre los tipos de ticket en proporción a sus tickets cumplidos en cada "
            "cliente-sprint (la bonificación se calcula por cliente-sprint, no por ticket)."),
]
pk_cols = [
    col("Bloque", "string", "Bloque", hidden=True, extra=("sortByColumn: Orden",),
        desc="Bloque de Objetivos KPI que filtra el botón"),
    col("Orden", "int64", "Orden", hidden=True),
    col("Botón", "string", "Botón", extra=("sortByColumn: Orden",), desc="Texto de cada botón"),
]
pk_part = """
        let
            // Un botón por bloque del cuadro de objetivos. El texto del botón se puede cambiar sin tocar Objetivos KPI.
            Parametro = #table(
                type table [Bloque = text, Orden = Int64.Type, #"Botón" = text],
                {
                    {"KPI TICKETS", 1, "KPI Tickets"},
                    {"SLA", 2, "SLA"},
                    {"NEGOCIO", 3, "Negocio"},
                    {"OPERACIÓN", 4, "Operación"}
                }
            )
        in
            Parametro
"""
table("Parámetro KPI", "/// Botones de navegación por bloque de KPI (página Detalle de KPIs por tipo). Filtra Objetivos KPI.\ntable 'Parámetro KPI'\n",
      pk_measures, pk_cols, partition("Parámetro KPI", pk_part))

td_cols = [
    col("Tipo", "string", "Tipo", extra=("sortByColumn: Orden",), desc="Total, Incidencia, Petición o Tarea"),
    col("Orden", "int64", "Orden", hidden=True),
]
td_part = """
        let
            // Filas de la matriz de detalle: el total del KPI y cada tipo de ticket. Sin relaciones: las medidas
            // de «Detalle KPI» filtran Política SLA[Tipo] según la fila.
            Tipos = #table(
                type table [Orden = Int64.Type, Tipo = text],
                {{0, "Total"}, {1, "Incidencia"}, {2, "Petición"}, {3, "Tarea"}}
            )
        in
            Tipos
"""
table("Tipo detalle", "/// Filas de la matriz «Detalle de KPIs por tipo»: Total + tipos de ticket. Sin relaciones, por diseño.\ntable 'Tipo detalle'\n",
      [], td_cols, partition("Tipo detalle", td_part))

# ------------------------------------------------------------------------------------------
# Tabla Medidas: todas las medidas juntas, en carpetas numeradas (orden lógico, no alfabético).
# No tiene datos ni relaciones; su única columna está oculta para que Power BI la trate como tabla de medidas.
# ------------------------------------------------------------------------------------------
CARPETAS = {   # carpeta de cada medida según su carpeta original; las excepciones van por nombre
    "Volumen": "01 Volumen", "SLA": "02 SLA", "Operación": "03 Operación", "Contexto": "04 Plantilla",
    "Facturación": "05 Facturación", "Cuadro de objetivos": "07 Cuadro de objetivos", "Sprint": "08 Etiquetas",
    "Departamento": "09 Tickets por departamento", "Detalle KPI": "10 Detalle KPI por tipo",
}
CARPETA_POR_NOMBRE = {
    **{m: "06 Facturación por cliente" for m in ("% SLA del sprint", "Tickets computables del sprint",
                                                  "Incumplidos del sprint", "Nivel", "Último sprint facturado",
                                                  "% SLA celda riesgo", "Color tramo SLA",
                                                  "Título riesgo clientes",
                                                  "Umbral de penalización", "Cumple umbral SLA", "Color % SLA del sprint")},
    "Etiqueta sprint anterior": "08 Etiquetas",
}

def a_carpeta(bloque):
    nombre = re.search(r"^\tmeasure '([^']+)'", bloque, re.M).group(1)
    actual = re.search(r"^\t\tdisplayFolder: (.*)$", bloque, re.M).group(1)
    nueva = CARPETA_POR_NOMBRE.get(nombre) or CARPETAS[actual]
    return re.sub(r"^\t\tdisplayFolder: .*$", f"\t\tdisplayFolder: {nueva}", bloque, count=1, flags=re.M)

assert len({re.search(r"^\tmeasure '([^']+)'", b, re.M).group(1) for b in MEDIDAS}) == len(MEDIDAS), "medida duplicada"
with open(os.path.join(DEF, "tables", "Medidas.tmdl"), "w", encoding="utf-8", newline="\n") as f:
    f.write("/// Tabla de medidas: aquí están todas las medidas del modelo, agrupadas en carpetas. Sin datos ni relaciones.\n"
            "table Medidas\n\n"
            + "".join(a_carpeta(b) for b in MEDIDAS)
            + "\tcolumn Medidas\n\t\tdataType: string\n\t\tisHidden\n\t\tsummarizeBy: none\n\t\tsourceColumn: [Medidas]\n\n"
            + "\tpartition Medidas = calculated\n\t\tmode: import\n\t\tsource = ROW(\"Medidas\", \"\")\n")
print(f"ok · {len(MEDIDAS)} medidas en la tabla Medidas")
