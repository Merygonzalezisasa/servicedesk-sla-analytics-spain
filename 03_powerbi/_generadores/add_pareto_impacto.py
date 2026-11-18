"""Pareto de penalización por cliente (página «Impacto económico acumulado») con el gráfico nativo
de columnas y líneas, en lugar del visual de AppSource «Pareto Chart Pro».

Barras naranjas con el importe, curva azul oscuro del % acumulado (eje secundario 0–100 %) con
sombreado suave, línea discontinua del 80 % y nombres completos de cliente.
Mantiene el nombre, la posición y el contenedor (título, borde, fondo) del visual que sustituye.
Se puede relanzar.

Uso: python -X utf8 add_pareto_impacto.py "<carpeta Brujula SLA.Report>"
"""
import json, os, sys

REPORT = sys.argv[1]
VISUAL = os.path.join(REPORT, "definition", "pages", "d9140412a99203aedb0f", "visuals",
                      "12c1c127c96e12bb19d4", "visual.json")

NARANJA, AZUL, AREA, TEXTO, GRIS, REJILLA = "#F28C4A", "#1F3A5F", "#DCE8F5", "#1B1F24", "#605E5C", "#E6E9EE"

PEN = "Medidas.Penalización €"
ACUM = "Medidas.% acumulado penalización cliente"
REF = "Medidas.Referencia 80 %"


def lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def color(c):
    return {"solid": {"color": lit(f"'{c}'")}}


def medida_expr(nombre):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": "Medidas"}}, "Property": nombre}}


def proy_medida(nombre, etiqueta):
    return {"field": medida_expr(nombre), "queryRef": f"Medidas.{nombre}",
            "nativeQueryRef": nombre, "displayName": etiqueta}


def main():
    with open(VISUAL, encoding="utf-8") as f:
        v = json.load(f)
    vco = v["visual"]["visualContainerObjects"]
    vco["subTitle"] = [{"properties": {
        "show": lit("true"), "text": {"expr": medida_expr("Título Pareto penalización")},
        "fontSize": lit("9.0D"), "fontColor": color(GRIS)}}]
    vco["general"] = [{"properties": {"altText": lit(
        "'Barras: penalización de cada cliente de mayor a menor. Línea: % acumulado de la penalización, "
        "con la referencia del 80 %'")}}]

    v["visual"] = {
        "visualType": "lineClusteredColumnComboChart",
        "query": {
            "queryState": {
                "Category": {"projections": [{
                    "field": {"Column": {"Expression": {"SourceRef": {"Entity": "Cliente"}}, "Property": "Cliente"}},
                    "queryRef": "Cliente.Cliente", "nativeQueryRef": "Cliente", "active": True}]},
                "Y": {"projections": [proy_medida("Penalización €", "Penalización por cliente")]},
                "Y2": {"projections": [proy_medida("% acumulado penalización cliente", "% acumulado de penalizaciones"),
                                       proy_medida("Referencia 80 %", "80 %")]},
            },
            "sortDefinition": {"sort": [{"field": medida_expr("Penalización €"), "direction": "Descending"}],
                               "isDefaultSort": True},
        },
        "objects": {
            "dataPoint": [
                {"properties": {"fill": color(NARANJA)}, "selector": {"metadata": PEN}},
                {"properties": {"fill": color(AZUL)}, "selector": {"metadata": ACUM}},
                {"properties": {"fill": color(AZUL)}, "selector": {"metadata": REF}},
            ],
            "lineStyles": [
                {"properties": {"strokeWidth": lit("3D"), "showMarker": lit("true"), "markerShape": lit("'circle'"),
                                "markerSize": lit("6D"), "markerColor": color(AZUL), "areaShow": lit("true"),
                                "areaColor": color(AREA), "areaMatchStrokeColor": lit("false")},
                 "selector": {"metadata": ACUM}},
                {"properties": {"strokeWidth": lit("2D"), "lineStyle": lit("'dashed'"), "showMarker": lit("false"),
                                "areaShow": lit("false")},
                 "selector": {"metadata": REF}},
            ],
            "labels": [
                {"properties": {"show": lit("true"), "fontSize": lit("9D")}},
                {"properties": {"color": color(TEXTO), "bold": lit("true"), "labelPosition": lit("'OutsideEnd'")},
                 "selector": {"metadata": PEN}},
                {"properties": {"color": color(AZUL), "bold": lit("true"), "labelPosition": lit("'Above'"),
                                "enableBackground": lit("true"), "backgroundColor": color("#FFFFFF"),
                                "backgroundTransparency": lit("20D")},
                 "selector": {"metadata": ACUM}},
                {"properties": {"showSeries": lit("false")}, "selector": {"metadata": REF}},
            ],
            "categoryAxis": [{"properties": {
                "show": lit("true"), "fontSize": lit("9D"), "labelColor": color(TEXTO),
                "showAxisTitle": lit("false"), "maxMarginFactor": lit("35L"), "concatenateLabels": lit("false")}}],
            "valueAxis": [{"properties": {
                "show": lit("true"), "start": lit("0D"), "fontSize": lit("9D"), "labelColor": color(GRIS),
                "showAxisTitle": lit("true"), "titleText": lit("'Penalización'"), "titleColor": color(GRIS),
                "titleFontSize": lit("10D"), "gridlineShow": lit("true"), "gridlineColor": color(REJILLA),
                "secShow": lit("true"), "secStart": lit("0D"), "secEnd": lit("1D"), "secFontSize": lit("9D"),
                "secLabelColor": color(GRIS), "secShowAxisTitle": lit("true"), "secTitleText": lit("'% acumulado'"),
                "secTitleColor": color(GRIS), "secTitleFontSize": lit("10D"), "alignZeros": lit("true")}}],
            "legend": [{"properties": {
                "show": lit("true"), "position": lit("'BottomCenter'"), "showTitle": lit("false"),
                "fontSize": lit("9D"), "labelColor": color(GRIS), "legendMarkerRendering": lit("'lineAndMarker'")}}],
        },
        "visualContainerObjects": vco,
        "drillFilterOtherVisuals": True,
    }
    v["$schema"] = ("https://developer.microsoft.com/json-schemas/fabric/item/report/definition/"
                    "visualContainer/2.14.0/schema.json")
    with open(VISUAL, "w", encoding="utf-8") as f:
        json.dump(v, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("Pareto nativo escrito en", VISUAL)


if __name__ == "__main__":
    main()
