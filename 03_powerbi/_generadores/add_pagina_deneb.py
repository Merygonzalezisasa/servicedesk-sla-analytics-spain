"""Añade al informe una página de ejemplos con visuales Deneb (AppSource), sobre la página «Impacto financiero».

No regenera nada: copia de «Impacto financiero» solo el marco (raíl de filtros, cabecera, periodo y pie)
y añade 3 gráficos Deneb (Vega-Lite). Registra Deneb en report.json (publicCustomVisuals).
Se puede volver a ejecutar: rehace solo la página de ejemplos.

Uso: python -X utf8 add_pagina_deneb.py <carpeta Brujula SLA.Report>
Desktop debe estar cerrado (al guardar reescribe el informe).
"""
import copy, json, os, shutil, sys

REPORT = sys.argv[1]
PAGES = os.path.join(REPORT, "definition", "pages")
ORIGEN = "d9140412a99203aedb0f"           # Impacto financiero
PAGINA = "de0eb1a7f3c2e5d40b11"           # página nueva
NOMBRE = "Impacto financiero · Deneb"
DENEB = "deneb7E15AEF80B9E4D4F8E12924291ECE89A"

# Marco copiado de Impacto financiero (raíl, filtros, títulos, periodo, pie)
MARCO = ["01399e5288001606856c", "50d5c129656c0e63bbc8", "166617bd56ebe55b2165", "062d8056d8665808b234",
         "7658ad958a043ae01584", "42d2bd6616e1f687d942", "67675aa78bf3961fee70", "228ca6d19d20d562f035",
         "a578cfcb332407665057", "b52f10c84ea16f2acf91", "10f9627de53393536418"]
CABECERA, PIE = "b52f10c84ea16f2acf91", "10f9627de53393536418"

TINTA, GRIS, VERDE, ROJO, AZUL = "#1B1F24", "#605E5C", "#1E7B5C", "#C0392B", "#1F3A5F"


def lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def texto(s):
    return lit("'" + s.replace("'", "''") + "'")


def col(entity, prop):
    return {"field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
            "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop}


def med(prop):
    return {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "Medidas"}}, "Property": prop}},
            "queryRef": f"Medidas.{prop}", "nativeQueryRef": prop}


# ---------- Configuración común de Vega-Lite (estilo del informe) ----------
CONFIG = {
    "autosize": {"type": "fit", "contains": "padding"},
    "customFormatTypes": True,                       # permite formatType 'pbiFormat' (formato de Power BI)
    "view": {"stroke": "transparent"},
    "font": "Segoe UI",
    "padding": 4,
    "axis": {"domain": False, "ticks": False, "grid": False, "labelColor": GRIS, "labelFontSize": 11,
             "titleColor": GRIS, "titleFontSize": 11, "titleFontWeight": "normal", "labelPadding": 6},
    "axisQuantitative": {"grid": True, "gridColor": "#E6E9EE", "gridDash": [2, 3], "tickCount": 5},
    "legend": {"labelColor": GRIS, "titleColor": GRIS, "labelFontSize": 11, "titleFontSize": 11,
               "titleFontWeight": "normal", "orient": "top"},
    "text": {"font": "Segoe UI", "fontSize": 11, "fill": TINTA},
    "bar": {"cornerRadius": 3},
}

PASO = {"field": "paso", "type": "nominal", "title": None,
        "scale": {"domain": ["Bonif. Gold", "Bonif. Silver", "Bonif. Bronze", "Penal. Gold", "Penal. Silver", "Balance"],
                  "paddingInner": 0.35},
        "axis": {"labelAngle": 0, "labelFontSize": 12, "labelColor": TINTA}}

# ---------- 1. Cascada: de la bonificación al balance, por nivel de contrato ----------
CASCADA = {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "data": {"name": "dataset"},
    "transform": [
        {"fold": ["Bonus €", "Penalización €"], "as": ["tipo", "importe"]},
        {"calculate": "datum.tipo === 'Bonus €' ? datum.importe : -datum.importe", "as": "valor"},
        {"filter": "datum.valor !== 0"},
        {"calculate": "(datum.tipo === 'Bonus €' ? 'Bonif. ' : 'Penal. ') + datum['Nivel de contrato']", "as": "paso"},
        {"calculate": "(datum.tipo === 'Bonus €' ? 0 : 10) + indexof(['Gold','Silver','Bronze'], datum['Nivel de contrato'])",
         "as": "orden"},
    ],
    "layer": [
        {   # pasos: cada barra arranca donde acaba la anterior
            "encoding": {"x": PASO},
            "transform": [
                {"window": [{"op": "sum", "field": "valor", "as": "fin"}], "sort": [{"field": "orden"}],
                 "frame": [None, 0]},
                {"calculate": "datum.fin - datum.valor", "as": "inicio"},
                {"calculate": "max(datum.inicio, datum.fin)", "as": "arriba"},
            ],
            "layer": [
                {"mark": {"type": "bar"},
                 "encoding": {
                     "y": {"field": "inicio", "type": "quantitative", "title": None,
                           "axis": {"format": "#,0 €", "formatType": "pbiFormat"}},
                     "y2": {"field": "fin"},
                     "color": {"condition": {"test": "datum.valor > 0", "value": VERDE}, "value": ROJO},
                     "tooltip": [{"field": "Nivel de contrato", "title": "Nivel"},
                                 {"field": "tipo", "title": "Concepto"},
                                 {"field": "importe", "title": "Importe", "format": "#,0 €", "formatType": "pbiFormat"}]}},
                {"mark": {"type": "text", "dy": -9, "fontWeight": "bold"},
                 "encoding": {"y": {"field": "arriba", "type": "quantitative"},
                              "text": {"field": "valor", "format": "+#,0 €;−#,0 €", "formatType": "pbiFormat"},
                              "color": {"condition": {"test": "datum.valor > 0", "value": VERDE}, "value": ROJO}}},
            ],
        },
        {   # barra final: balance neto
            "transform": [{"aggregate": [{"op": "sum", "field": "valor", "as": "balance"}]},
                          {"calculate": "'Balance'", "as": "paso"},
                          {"calculate": "0", "as": "cero"},
                          {"calculate": "max(datum.balance, 0)", "as": "arriba"}],
            "encoding": {"x": PASO},
            "layer": [
                {"mark": {"type": "bar"},
                 "encoding": {"y": {"field": "cero", "type": "quantitative"}, "y2": {"field": "balance"},
                              "color": {"value": AZUL},
                              "tooltip": [{"field": "balance", "title": "Balance", "format": "+#,0 €;−#,0 €",
                                           "formatType": "pbiFormat"}]}},
                {"mark": {"type": "text", "dy": -9, "fontWeight": "bold", "color": AZUL},
                 "encoding": {"y": {"field": "arriba", "type": "quantitative"},
                              "text": {"field": "balance", "format": "+#,0 €;−#,0 €", "formatType": "pbiFormat"}}},
            ],
        },
        {"mark": {"type": "rule", "color": GRIS, "strokeWidth": 1},
         "encoding": {"y": {"datum": 0}}},
    ],
}

# ---------- 2. Bala: % SLA de cada cliente frente a su umbral de penalización ----------
BALA = {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "data": {"name": "dataset"},
    "transform": [
        {"filter": "datum['Nivel de contrato'] !== 'Bronze' && isValid(datum['% SLA del sprint'])"},
        {"calculate": "datum['% SLA del sprint'] - datum['Objetivo contractual']", "as": "margen"},
        {"calculate": "datum.Cliente + '  (' + datum['Nivel de contrato'] + ')'", "as": "fila"},
        {"calculate": "0.8", "as": "suelo"},
        {"calculate": "pbiFormat(datum['% SLA del sprint'], '0.0 %') + (datum['Penalización €'] > 0 ? '   −' + pbiFormat(datum['Penalización €'], '#,0 €') : '')",
         "as": "rotulo"},
    ],
    "encoding": {
        "y": {"field": "fila", "type": "nominal", "title": None, "sort": {"field": "margen", "op": "min", "order": "ascending"},
              "axis": {"labelColor": TINTA, "labelLimit": 260}},
    },
    "layer": [
        {   # zona de penalización: del 80 % al umbral del cliente
            "mark": {"type": "bar", "color": "#FBE3E1", "cornerRadius": 0, "height": {"band": 0.8}},
            "encoding": {"x": {"field": "suelo", "type": "quantitative",
                               "scale": {"domain": [0.8, 1], "clamp": True},
                               "axis": {"format": "0 %", "formatType": "pbiFormat", "orient": "top"}, "title": None},
                         "x2": {"field": "Objetivo contractual"}}},
        {   # % real del cliente
            "mark": {"type": "bar", "height": {"band": 0.38}, "cornerRadius": 2},
            "encoding": {"x": {"field": "suelo", "type": "quantitative"}, "x2": {"field": "% SLA del sprint"},
                         "color": {"condition": {"test": "datum.margen < 0", "value": ROJO}, "value": VERDE},
                         "tooltip": [{"field": "Cliente"}, {"field": "Nivel de contrato", "title": "Nivel"},
                                     {"field": "% SLA del sprint", "title": "% SLA", "format": "0.0 %",
                                      "formatType": "pbiFormat"},
                                     {"field": "Objetivo contractual", "title": "Umbral", "format": "0 %",
                                      "formatType": "pbiFormat"},
                                     {"field": "Penalización €", "title": "Penalización", "format": "#,0 €",
                                      "formatType": "pbiFormat"}]}},
        {   # umbral contractual
            "mark": {"type": "tick", "color": TINTA, "thickness": 2, "size": 18},
            "encoding": {"x": {"field": "Objetivo contractual", "type": "quantitative"}}},
        {   # rótulo: % y penalización
            "mark": {"type": "text", "align": "left", "dx": 6, "fontSize": 10.5},
            "encoding": {"x": {"field": "% SLA del sprint", "type": "quantitative"},
                         "text": {"field": "rotulo"},
                         "color": {"condition": {"test": "datum.margen < 0", "value": ROJO}, "value": GRIS}}},
    ],
}

# ---------- 3. Mapa de calor: penalización por cliente y sprint ----------
CALOR = {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "data": {"name": "dataset"},
    "transform": [
        {"joinaggregate": [{"op": "sum", "field": "Penalización €", "as": "total"}], "groupby": ["Cliente"]},
        {"filter": "datum.total > 0"},
    ],
    "mark": {"type": "rect", "cornerRadius": 2, "stroke": "#FFFFFF", "strokeWidth": 1.5},
    "encoding": {
        "x": {"field": "Sprint", "type": "ordinal", "title": None, "sort": {"field": "Orden", "op": "min"},
              "axis": {"orient": "top", "labelAngle": 0, "labelExpr": "split(datum.label, '-')[1]"}},
        "y": {"field": "Cliente", "type": "nominal", "title": None,
              "sort": {"field": "total", "op": "max", "order": "descending"},
              "axis": {"labelColor": TINTA, "labelLimit": 200}},
        "color": {"condition": {"test": "datum['Penalización €'] === 0", "value": "#EEF1F5"},
                  "field": "Penalización €", "type": "quantitative",
                  "scale": {"range": ["#F6D5C2", "#D9692F", "#7A2E0E"]},
                  "legend": {"title": "Penalización", "format": "#,0 €", "formatType": "pbiFormat",
                             "gradientLength": 160, "orient": "top-right", "direction": "horizontal"}},
        "tooltip": [{"field": "Cliente"}, {"field": "Sprint"},
                    {"field": "Penalización €", "title": "Penalización", "format": "#,0 €",
                     "formatType": "pbiFormat"}],
    },
}


def deneb(vid, x, y, w, h, z, campos, spec, titulo, subtitulo, alt):
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.6.0/schema.json",
        "name": vid,
        "position": {"x": x, "y": y, "z": z, "width": w, "height": h, "tabOrder": z},
        "visual": {
            "visualType": DENEB,
            "query": {"queryState": {"dataset": {"projections": campos}}},
            "objects": {
                "vega": [{"properties": {
                    "provider": texto("vegaLite"),
                    "renderMode": texto("svg"),
                    "jsonSpec": texto(json.dumps(spec, ensure_ascii=False, indent=2)),
                    "jsonConfig": texto(json.dumps(CONFIG, ensure_ascii=False, indent=2)),
                    "isNewDialogOpen": lit("false"),
                    "enableTooltips": lit("true"),
                    "enableContextMenu": lit("true"),
                    "enableSelection": lit("false"),
                    "enableHighlight": lit("false"),
                }}],
            },
            "visualContainerObjects": {
                "padding": [{"properties": {k: lit("16D") for k in ("top", "bottom", "left", "right")}}],
                "border": [{"properties": {"show": lit("true")}}],
                "visualHeader": [{"properties": {"show": lit("false")}}],
                "dropShadow": [{"properties": {"show": lit("false")}}],
                "background": [{"properties": {"show": lit("true"),
                                               "color": {"solid": {"color": lit("'#FFFFFF'")}},
                                               "transparency": lit("0D")}}],
                "title": [{"properties": {"show": lit("true"), "text": texto(titulo), "fontSize": lit("12D"),
                                          "bold": lit("true"), "fontColor": {"solid": {"color": lit(f"'{TINTA}'")}}}}],
                "subTitle": [{"properties": {"show": lit("true"), "text": texto(subtitulo), "fontSize": lit("9D"),
                                             "fontColor": {"solid": {"color": lit(f"'{GRIS}'")}}}}],
                "general": [{"properties": {"altText": texto(alt)}}],
            },
            "drillFilterOtherVisuals": True,
        },
    }


VISUALES = [
    deneb("de0eb1a7c0a5ca0a0001", 288, 88, 790, 430, 20000,
          [col("Cliente", "Nivel de contrato"), med("Bonus €"), med("Penalización €")], CASCADA,
          "De la bonificación al balance",
          "Deneb · cascada: cada barra suma (verde) o resta (rojo) por nivel de contrato hasta el balance neto",
          "Cascada: bonificación y penalización por nivel de contrato que acaban en el balance neto del periodo"),
    deneb("de0eb1a7c0a5ca0a0002", 288, 538, 790, 486, 20100,
          [col("Cliente", "Cliente"), col("Sprint", "Sprint"), col("Sprint", "Orden"), med("Penalización €")], CALOR,
          "¿Cuándo y a quién se penaliza?",
          "Deneb · mapa de calor: penalización por cliente y sprint; cuanto más oscuro, más importe",
          "Mapa de calor: clientes penalizados en filas, sprints en columnas, color según el importe penalizado"),
    deneb("de0eb1a7c0a5ca0a0003", 1098, 88, 806, 936, 20200,
          [col("Cliente", "Cliente"), col("Cliente", "Nivel de contrato"), col("Cliente", "Objetivo contractual"),
           med("% SLA del sprint"), med("Penalización €")], BALA,
          "% SLA de resolución frente al umbral de cada cliente",
          "Deneb · gráfico de bala: barra = % del periodo, raya = umbral, rosa = zona de penalización; € = sprints penalizados",
          "Gráfico de bala por cliente Gold y Silver: % de SLA de resolución frente a su umbral contractual"),
]


def renombrar_filtros(d):
    """Los nombres de filtro deben ser únicos en todo el informe: les cambio el prefijo al copiarlos."""
    for f in d.get("filterConfig", {}).get("filters", []):
        f["name"] = "de0e" + f["name"][4:]


def main():
    origen, destino = os.path.join(PAGES, ORIGEN), os.path.join(PAGES, PAGINA)
    if os.path.isdir(destino):
        shutil.rmtree(destino)
    os.makedirs(os.path.join(destino, "visuals"))

    page = json.load(open(os.path.join(origen, "page.json"), encoding="utf-8"))
    page["name"], page["displayName"] = PAGINA, NOMBRE
    renombrar_filtros(page)
    page.pop("visualInteractions", None)
    json.dump(page, open(os.path.join(destino, "page.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    for vid in MARCO:
        d = json.load(open(os.path.join(origen, "visuals", vid, "visual.json"), encoding="utf-8"))
        nuevo = "de0e" + vid[4:]                                   # id propio en la página nueva
        d["name"] = nuevo
        renombrar_filtros(d)
        props = d["visual"].get("objects", {}).get("general", [{}])[0].get("properties", {})
        if vid == CABECERA:
            props["paragraphs"][0]["textRuns"][0]["value"] = "IMPACTO FINANCIERO · EJEMPLOS DENEB"
        if vid == PIE:
            props["paragraphs"][0]["textRuns"][0]["value"] = (
                "Visuales Deneb (AppSource, Vega-Lite). Muestran el año seleccionado y responden a los filtros "
                "de la izquierda. Pasa el ratón por encima para ver el detalle.")
        os.makedirs(os.path.join(destino, "visuals", nuevo))
        json.dump(d, open(os.path.join(destino, "visuals", nuevo, "visual.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)

    for v in VISUALES:
        os.makedirs(os.path.join(destino, "visuals", v["name"]))
        json.dump(v, open(os.path.join(destino, "visuals", v["name"], "visual.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)

    # Orden de páginas: justo detrás de Impacto financiero
    pj = os.path.join(PAGES, "pages.json")
    pages = json.load(open(pj, encoding="utf-8"))
    orden = [p for p in pages["pageOrder"] if p != PAGINA]
    orden.insert(orden.index(ORIGEN) + 1, PAGINA)
    pages["pageOrder"] = orden
    json.dump(pages, open(pj, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # Registrar Deneb como visual de AppSource
    rj = os.path.join(REPORT, "definition", "report.json")
    rep = json.load(open(rj, encoding="utf-8"))
    vis = rep.setdefault("publicCustomVisuals", [])
    if DENEB not in vis:
        vis.append(DENEB)
    json.dump(rep, open(rj, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"ok: página «{NOMBRE}» con {len(MARCO)} piezas de marco y {len(VISUALES)} visuales Deneb")


if __name__ == "__main__":
    main()
