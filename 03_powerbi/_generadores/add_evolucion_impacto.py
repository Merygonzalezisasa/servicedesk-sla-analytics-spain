"""DESHECHO el 2026-11-18 a petición del usuario (repetía el gráfico de «Resultado económico del sprint»):
se restauró el visual original. NO relanzar.

Gráfico «Evolución económica» de la página «Impacto económico acumulado»: columnas apiladas nativas
(bonificación azul hacia arriba, penalización naranja hacia abajo) en lugar del visual de AppSource
«Line & Stacked Column with Table», más un recuadro «Balance acumulado» en su esquina superior derecha.

Mantiene nombre, posición y contenedor (borde, fondo) del visual que sustituye. El recuadro se crea
copiando la tarjeta «Balance económico neto» (add_tarjetas_impacto.py). Se puede relanzar.

Uso: python -X utf8 add_evolucion_impacto.py "<carpeta Brujula SLA.Report>"
"""
import copy, hashlib, json, os, sys

REPORT = sys.argv[1]
VISUALES = os.path.join(REPORT, "definition", "pages", "d9140412a99203aedb0f", "visuals")
GRAFICO = "84aa2309bca205c5b5e5"
TARJETA_BALANCE = hashlib.sha1(b"impacto/balance").hexdigest()[:20]          # la de la fila de tarjetas
RECUADRO = hashlib.sha1(b"impacto/balance_acumulado").hexdigest()[:20]

AZUL, NARANJA, TEXTO, GRIS, REJILLA, CERO = "#2E6DB4", "#F28C4A", "#1B1F24", "#605E5C", "#D5DAE1", "#8A9099"
BONUS, PEN = "Medidas.Bonus €", "Medidas.Penalización negativa €"


def lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def color(c):
    return {"solid": {"color": lit(f"'{c}'")}}


def medida(nombre):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": "Medidas"}}, "Property": nombre}}


def leer(vid):
    with open(os.path.join(VISUALES, vid, "visual.json"), encoding="utf-8") as f:
        return json.load(f)


def guardar(vid, v):
    os.makedirs(os.path.join(VISUALES, vid), exist_ok=True)
    with open(os.path.join(VISUALES, vid, "visual.json"), "w", encoding="utf-8") as f:
        json.dump(v, f, ensure_ascii=False, indent=2)
        f.write("\n")


def grafico():
    v = leer(GRAFICO)
    vco = v["visual"]["visualContainerObjects"]
    vco.pop("lockAspect", None)
    vco["title"] = [{"properties": {"show": lit("true"), "text": lit("'Evolución económica'"),
                                    "fontSize": lit("14D"), "bold": lit("true"), "fontColor": color("#1F3A5F")}}]
    vco["subTitle"] = [{"properties": {"show": lit("true"), "text": lit("'Bonificaciones y penalizaciones por sprint'"),
                                       "fontSize": lit("10D"), "fontColor": color(GRIS)}}]
    vco["spacing"] = [{"properties": {"spaceAboveSubtitle": lit("2D"), "spaceAbovePlotArea": lit("24D")}}]
    vco["padding"] = [{"properties": {"top": lit("8D"), "bottom": lit("4D"), "left": lit("16D"), "right": lit("16D")}}]
    vco["general"] = [{"properties": {"altText": lit(
        "'Columnas: bonificación (hacia arriba) y penalización (hacia abajo) de cada sprint'")}}]

    v["visual"] = {
        "visualType": "columnChart",
        "query": {
            "queryState": {
                "Category": {"projections": [{
                    "field": {"Column": {"Expression": {"SourceRef": {"Entity": "Sprint"}}, "Property": "Sprint"}},
                    "queryRef": "Sprint.Sprint", "nativeQueryRef": "Sprint", "active": True}]},
                "Y": {"projections": [
                    {"field": medida("Bonus €"), "queryRef": BONUS, "nativeQueryRef": "Bonus €",
                     "displayName": "Bonificaciones"},
                    {"field": medida("Penalización negativa €"), "queryRef": PEN,
                     "nativeQueryRef": "Penalización negativa €", "displayName": "Penalizaciones"}]},
            },
            "sortDefinition": {"sort": [{"field": {"Column": {"Expression": {"SourceRef": {"Entity": "Sprint"}},
                                                              "Property": "Sprint"}}, "direction": "Ascending"}],
                               "isDefaultSort": True},
        },
        "objects": {
            "dataPoint": [
                {"properties": {"fill": color(AZUL)}, "selector": {"metadata": BONUS}},
                {"properties": {"fill": color(NARANJA)}, "selector": {"metadata": PEN}},
            ],
            "labels": [{"properties": {"show": lit("true"), "color": color("#FFFFFF"), "bold": lit("true"),
                                       "fontSize": lit("9D"), "labelPosition": lit("'InsideEnd'")}}],
            "categoryAxis": [{"properties": {"show": lit("true"), "fontSize": lit("9D"), "labelColor": color(TEXTO),
                                             "showAxisTitle": lit("false"), "innerPadding": lit("12L")}}],
            "valueAxis": [{"properties": {"show": lit("true"), "fontSize": lit("9D"), "labelColor": color(GRIS),
                                          "showAxisTitle": lit("false"), "gridlineShow": lit("true"),
                                          "gridlineColor": color(REJILLA), "gridlineStyle": lit("'dashed'")}}],
            "y1AxisReferenceLine": [{"properties": {"show": lit("true"), "displayName": lit("'Cero'"),
                                                    "value": lit("0D"), "lineColor": color(CERO),
                                                    "width": lit("1D"), "style": lit("'solid'"),
                                                    "position": lit("'front'"), "dataLabelShow": lit("false")},
                                     "selector": {"id": "1"}}],
            "legend": [{"properties": {"show": lit("true"), "position": lit("'BottomCenter'"),
                                       "showTitle": lit("false"), "fontSize": lit("10D"), "labelColor": color(TEXTO)}}],
        },
        "visualContainerObjects": vco,
        "drillFilterOtherVisuals": True,
    }
    return v


def recuadro():
    v = copy.deepcopy(leer(TARJETA_BALANCE))
    g = leer(GRAFICO)["position"]
    v["name"] = RECUADRO
    ancho, alto = 296, 64
    v["position"] = {"x": g["x"] + g["width"] - ancho - 12, "y": g["y"] + 10, "z": g["z"] + 500,
                     "height": alto, "width": ancho, "tabOrder": g["tabOrder"] + 500}
    o = v["visual"]["objects"]
    for k in ("referenceLabel", "referenceLabelTitle", "referenceLabelValue", "referenceLabelDetail",
              "referenceLabelLayout"):
        o.pop(k, None)
    for e in o["value"]:
        if e.get("selector", {}).get("id") == "default":
            e["properties"]["fontSize"] = lit("20.0D")
    for e in o["label"]:
        e["properties"]["text"] = lit("'Balance acumulado'")
    vco = v["visual"]["visualContainerObjects"]
    vco["padding"] = [{"properties": {k: lit(n) for k, n in
                                      (("top", "6.0D"), ("bottom", "6.0D"), ("left", "12.0D"), ("right", "12.0D"))}}]
    vco["general"] = [{"properties": {"altText": lit("'Balance acumulado (bonificación menos penalización)'")}}]
    return v


def main():
    guardar(GRAFICO, grafico())
    guardar(RECUADRO, recuadro())
    print("gráfico", GRAFICO, "→ columnChart · recuadro", RECUADRO)


if __name__ == "__main__":
    main()
