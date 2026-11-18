"""Añade la página «Detalle de KPIs por tipo» al informe guardado por Desktop (no regenera nada más).

- Marco y segmentadores copiados de «Cumplimiento de objetivos» y sincronizados con ella (los cambios de filtro en
  una página se ven en la otra). A los segmentadores de la página 1 que no estaban sincronizados se les añade el
  grupo de sincronización.
- Botones de bloque (Parámetro KPI[Botón]) con SLA seleccionado al abrir.
- Matriz: filas KPI → Total / Incidencia / Petición / Tarea (tabla Tipo detalle) y 7 columnas.
Se puede volver a ejecutar: rehace solo esta página.

Uso: python -X utf8 add_pagina_detalle_kpi.py <carpeta Brujula SLA.Report>
Desktop debe estar cerrado (al guardar reescribe el informe).
"""
import hashlib, json, os, shutil, sys

REPORT = sys.argv[1]
PAGES = os.path.join(REPORT, "definition", "pages")
ORIGEN = "8d6200671df52c4495f0"             # Cumplimiento de objetivos
NOMBRE = "Detalle de KPIs por tipo"
PAGINA = hashlib.sha1(b"page/detalle_kpi").hexdigest()[:20]
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json"

RAIL = ["40440ff6814af27198f6", "fe8373c06c102bf42d41"]                 # fondo del raíl y rótulo «Filtros»
CABECERA = ["4fee60e62da7b63eaf64", "99466d171121210a45b5"]             # antetítulo y caja de periodo
TITULO = "3ab0c78099b049308ef6"
SEGMENTADORES = {                                                     # id en la página 1 → grupo de sincronización
    "84f8848bb517a9edc600": "anio", "bace10e8f86df8988b0b": "sprint",
    "21766630f8f94cab8199": "nivel", "6754ddf224654a03809e": "cliente", "f0def3bbe0715d4e63ee": "departamento",
    "501bd6a9457eb27c8aa0": "tipo", "6bca17d86d3639b71dbb": "prioridad",
}
TINTA, GRIS, AZUL, BORDE = "#1B1F24", "#605E5C", "#1F3A5F", "#C5CBD3"


def hid(clave):
    return hashlib.sha1(f"detalle_kpi/{clave}".encode("utf-8")).hexdigest()[:20]


def lit(v):
    if isinstance(v, bool):
        return {"expr": {"Literal": {"Value": "true" if v else "false"}}}
    if isinstance(v, int):
        return {"expr": {"Literal": {"Value": f"{v}L"}}}
    if isinstance(v, float):
        return {"expr": {"Literal": {"Value": f"{v}D"}}}
    return {"expr": {"Literal": {"Value": "'" + str(v).replace("'", "''") + "'"}}}


def color(h):
    return {"solid": {"color": lit(h)}}


def color_m(medida):
    return {"solid": {"color": {"expr": {"Measure": {"Expression": {"SourceRef": {"Entity": "Medidas"}},
                                                      "Property": medida}}}}}


def props(sel=None, **kw):
    d = {"properties": kw}
    if sel:
        d["selector"] = {"id": sel}
    return d


def c_proj(entity, prop, display=None):
    p = {"field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
         "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop}
    if display:
        p["displayName"] = display
    return p


def m_proj(prop, display):
    return {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "Medidas"}}, "Property": prop}},
            "queryRef": f"Medidas.{prop}", "nativeQueryRef": prop, "displayName": display}


def cargar(pagina, vid):
    return json.load(open(os.path.join(PAGES, pagina, "visuals", vid, "visual.json"), encoding="utf-8"))


def guardar(pagina, d):
    ruta = os.path.join(PAGES, pagina, "visuals", d["name"], "visual.json")
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    json.dump(d, open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def sin_contenedor():
    return {"background": [props(show=lit(False))], "border": [props(show=lit(False))],
            "title": [props(show=lit(False))], "visualHeader": [props(show=lit(False))],
            "dropShadow": [props(show=lit(False))],
            "padding": [props(top=lit(0.0), bottom=lit(0.0), left=lit(0.0), right=lit(0.0))]}


# ---------- botones de bloque ----------
def botones():
    return {
        "$schema": SCHEMA, "name": hid("botones"),
        "position": {"x": 288, "y": 96, "z": 20000, "width": 940, "height": 56, "tabOrder": 20000},
        "visual": {
            "visualType": "advancedSlicerVisual",
            "query": {"queryState": {"Values": {"projections": [c_proj("Parámetro KPI", "Botón")]}}},
            "objects": {
                "general": [props(filter={"filter": {
                    "Version": 2, "From": [{"Name": "p", "Entity": "Parámetro KPI", "Type": 0}],
                    "Where": [{"Condition": {"In": {
                        "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "p"}}, "Property": "Botón"}}],
                        "Values": [[{"Literal": {"Value": "'SLA'"}}]]}}}]}})],
                # «Seleccionar todo» como primer botón; Ctrl + clic para elegir varios bloques
                "selection": [props(singleSelect=lit(False), strictSingleSelect=lit(False),
                                    selectAllCheckboxEnabled=lit(True))],
                "layout": [props(rowCount=lit(1), columnCount=lit(5), cellPadding=lit(12))],
                "shapeCustomRectangle": [props("default", tileShape=lit("rectangleRoundedByPixel"),
                                               rectangleRoundedCurve=lit(8))],
                "fillCustom": [props("default", show=lit(True), fillColor=color("#FFFFFF"), transparency=lit(0.0))],
                "outline": [props("default", show=lit(True), lineColor=color(BORDE), weight=lit(1.0)),
                            props("hover", show=lit(True), lineColor=color(AZUL), weight=lit(1.0)),
                            props("selected", show=lit(True), lineColor=color(AZUL), weight=lit(2.0))],
                "accentBar": [props("default", show=lit(False)),
                              props("selected", show=lit(True), position=lit("Bottom"), color=color(AZUL),
                                    width=lit(4.0))],
                "value": [props(show=lit(True), fontSize=lit(12.0), bold=lit(True), fontColor=color(TINTA),
                                horizontalAlignment=lit("center"))],
                "label": [props("default", show=lit(False))],
            },
            "visualContainerObjects": {**sin_contenedor(),
                                       "general": [props(altText=lit("Botones: elige el bloque de KPI que muestra la tabla"))]},
        },
    }


# ---------- matriz KPI → tipo ----------
COLUMNAS = [  # medida, nombre visible
    ("Objetivo detalle KPI", "Objetivo"),
    ("Tickets detalle KPI", "Tickets"),
    ("Tickets que computan KPI", "Computables"),
    ("Tickets incumplidos KPI", "Valor medido"),
    ("Tiempo medio detalle", "Tiempo medio"),
    ("Valor KPI detalle", "% cumplimiento"),
    ("Penalizado KPI €", "Penalizado"),
    ("Bonificado KPI €", "Bonificado"),
]


def matriz():
    wild = lambda m: {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": f"Medidas.{m}"}
    valores = [props(fontSize=lit(11.0), fontColorPrimary=color(TINTA), fontColorSecondary=color(TINTA),
                     backColorPrimary=color("#FFFFFF"), backColorSecondary=color("#FFFFFF"))]
    for m, _ in COLUMNAS:   # fila Total de cada KPI en azul muy claro
        valores.append({"properties": {"backColor": color_m("Fondo fila detalle KPI")}, "selector": wild(m)})
    valores.append({"properties": {"fontColor": color_m("Color valor KPI detalle"), "bold": lit(True)},
                    "selector": wild("Valor KPI detalle")})
    valores.append({"properties": {"fontColor": color_m("Color tiempo medio detalle"), "bold": lit(True)},
                    "selector": wild("Tiempo medio detalle")})
    return {
        "$schema": SCHEMA, "name": hid("matriz"),
        "position": {"x": 288, "y": 168, "z": 21000, "width": 1616, "height": 856, "tabOrder": 21000},
        "visual": {
            "visualType": "pivotTable",
            "query": {"queryState": {
                "Rows": {"projections": [c_proj("Objetivos KPI", "KPI"), c_proj("Tipo detalle", "Tipo")]},
                "Values": {"projections": [m_proj(m, n) for m, n in COLUMNAS]}}},
            "objects": {
                "columnHeaders": [props(fontColor=color("#FFFFFF"), backColor=color("#1F5C99"), bold=lit(True),
                                        fontSize=lit(11.0), alignment=lit("Center"), wordWrap=lit(True),
                                        columnAdjustment=lit("growToFit"), autoSizeColumnWidth=lit(True))],
                "rowHeaders": [props(fontSize=lit(11.0), fontColor=color(TINTA), stepped=lit(False),
                                     autoExpand=lit(True), showExpandCollapseButtons=lit(False),
                                     wordWrap=lit(False))],
                "values": valores,
                "subTotals": [props(rowSubtotals=lit(False), columnSubtotals=lit(False))],
                # ancho fijado a mano en Desktop (2026-11-15)
                "columnWidth": [{"properties": {"value": lit(px)}, "selector": {"metadata": campo}}
                                for campo, px in (("Medidas.Valor KPI detalle", 185.1), ("Tipo detalle.Tipo", 112.0),
                                                  ("Medidas.Tickets incumplidos KPI", 187.4), ("Objetivos KPI.KPI", 187.5))],
                "columnFormatting": [{"properties": {"alignment": lit("Right")},
                                      "selector": {"metadata": "Medidas.Tiempo medio detalle"}}],
                "grid": [props(gridHorizontal=lit(True), gridVertical=lit(True), gridHorizontalColor=color("#D0D7E2"),
                               gridVerticalColor=color("#D0D7E2"), rowPadding=lit(6.0))],
            },
            "visualContainerObjects": {
                "background": [props(show=lit(True), color=color("#FFFFFF"), transparency=lit(0.0))],
                "border": [props(show=lit(True), color=color("#E1E5EB"), radius=lit(10.0))],
                "padding": [props(top=lit(12.0), bottom=lit(12.0), left=lit(12.0), right=lit(12.0))],
                "visualHeader": [props(show=lit(False))], "dropShadow": [props(show=lit(False))],
                "title": [props(show=lit(False))],
                "general": [props(altText=lit("Matriz: cada KPI del bloque elegido con su fila Total y el detalle por "
                                              "tipo de ticket (incidencia, petición y tarea)"))],
            },
        },
    }


def nota():
    texto = ("La fila Total de cada KPI suma los tres tipos. Los importes solo aparecen en SLA resolución (KPI 6), "
             "el único que penaliza; la bonificación por tipo se reparte según sus tickets cumplidos. "
             "Los KPI de Negocio y % de agentes ausentes no se separan por tipo.")
    return {
        "$schema": SCHEMA, "name": hid("nota"),
        "position": {"x": 1252, "y": 96, "z": 20500, "width": 652, "height": 60, "tabOrder": 20500},
        "visual": {"visualType": "textbox",
                   "objects": {"general": [props(paragraphs=[{"textRuns": [
                       {"value": texto, "textStyle": {"fontSize": "9pt", "color": "#3b4048"}}]}])]},
                   "visualContainerObjects": sin_contenedor()},
    }


def main():
    destino = os.path.join(PAGES, PAGINA)
    if os.path.isdir(destino):
        shutil.rmtree(destino)
    os.makedirs(os.path.join(destino, "visuals"))

    page = json.load(open(os.path.join(PAGES, ORIGEN, "page.json"), encoding="utf-8"))
    page["name"], page["displayName"] = PAGINA, NOMBRE
    for k in ("visualInteractions", "filterConfig"):
        page.pop(k, None)
    json.dump(page, open(os.path.join(destino, "page.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # Marco y segmentadores copiados (id y nombres de filtro propios)
    for vid in RAIL + CABECERA + [TITULO] + list(SEGMENTADORES):
        d = cargar(ORIGEN, vid)
        d["name"] = hid(vid)
        for i, f in enumerate(d.get("filterConfig", {}).get("filters", [])):
            f["name"] = hid(f"{vid}/filtro{i}")
        if vid == TITULO:
            d["visual"]["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"][0]["value"] = \
                "Detalle de KPIs por tipo de ticket"
        if vid in SEGMENTADORES:
            d["visual"]["syncGroup"] = {"groupName": SEGMENTADORES[vid], "fieldChanges": True, "filterChanges": True}
        guardar(PAGINA, d)

    # Sincroniza los segmentadores de la página 1 que aún no lo estaban
    for vid, grupo in SEGMENTADORES.items():
        d = cargar(ORIGEN, vid)
        if "syncGroup" not in d["visual"]:
            d["visual"]["syncGroup"] = {"groupName": grupo, "fieldChanges": True, "filterChanges": True}
            guardar(ORIGEN, d)

    for v in (botones(), nota(), matriz()):
        guardar(PAGINA, v)

    # Detrás de Cumplimiento de objetivos
    pj = os.path.join(PAGES, "pages.json")
    pages = json.load(open(pj, encoding="utf-8"))
    orden = [p for p in pages["pageOrder"] if p != PAGINA]
    orden.insert(orden.index(ORIGEN) + 1, PAGINA)
    pages["pageOrder"] = orden
    json.dump(pages, open(pj, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"ok: página «{NOMBRE}» ({PAGINA}) con botones, matriz y {len(SEGMENTADORES)} segmentadores sincronizados")


if __name__ == "__main__":
    main()
