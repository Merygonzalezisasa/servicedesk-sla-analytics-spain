"""Botones de navegación a las páginas de detalle (Riesgo por cliente y Tickets por departamento).

- Páginas principales: sección «VER DETALLE» al pie del raíl de filtros con un botón a cada página de detalle.
- Páginas de detalle: «← Volver» (vuelve a la página anterior) y un botón a la otra página de detalle.
- Las dos páginas de detalle se ocultan en las pestañas del informe (siguen accesibles con los botones).
Solo añade o sustituye sus propios visuales (ids fijos): se puede volver a ejecutar.

Uso: python -X utf8 add_navegacion.py <carpeta Brujula SLA.Report>
Desktop debe estar cerrado (al guardar reescribe el informe).
"""
import hashlib, json, os, sys

PAGES = os.path.join(sys.argv[1], "definition", "pages")
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json"
RIESGO, DEPARTAMENTOS = "a32a3f23226e91ff42b8", "d6d9e9f29a60d35c5880"
PRINCIPALES = ["8d6200671df52c4495f0", "3c0c6420ac95cc7d08c6", "566eea23ca0f45d8afeb", "2384e88904eb3db36349",
               "d9140412a99203aedb0f"]
TEXTO = {RIESGO: "Riesgo por cliente", DEPARTAMENTOS: "Tickets por departamento"}
TINTA, AZUL, BORDE, GRIS = "#1B1F24", "#1F3A5F", "#C5CBD3", "#605E5C"
X, ANCHO, Y0 = 28, 224, 880


def hid(clave):
    return hashlib.sha1(f"navegacion/{clave}".encode("utf-8")).hexdigest()[:20]


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


def estados(**por_estado):
    """Entrada sin selector + una por estado (los actionButton necesitan las dos)."""
    out = [{"properties": por_estado["default"]}]
    for estado, props in por_estado.items():
        out.append({"properties": props, "selector": {"id": estado}})
    return out


def boton(pagina, clave, texto, y, z, destino=None):
    accion = ({"show": lit(True), "type": lit("PageNavigation"), "navigationSection": lit(destino),
               "tooltip": lit(f"Ir a {TEXTO[destino]}")} if destino else
              {"show": lit(True), "type": lit("Back"), "tooltip": lit("Volver a la página anterior")})
    return {
        "$schema": SCHEMA, "name": hid(f"{pagina}/{clave}"),
        "position": {"x": X, "y": y, "z": z, "width": ANCHO, "height": 44, "tabOrder": z},
        "visual": {
            "visualType": "actionButton",
            "objects": {
                "shape": [{"properties": {"tileShape": lit("rectangleRounded"), "roundEdge": lit(8)}}],
                "fill": estados(default={"show": lit(True), "fillColor": color("#FFFFFF"), "transparency": lit(0.0)},
                                hover={"show": lit(True), "fillColor": color("#EEF3F9"), "transparency": lit(0.0)}),
                "outline": estados(default={"show": lit(True), "lineColor": color(BORDE), "weight": lit(1.0),
                                            "transparency": lit(0.0)},
                                   hover={"show": lit(True), "lineColor": color(AZUL), "weight": lit(1.5),
                                          "transparency": lit(0.0)}),
                "text": estados(default={"show": lit(True), "text": lit(texto), "fontSize": lit(10.0),
                                         "bold": lit(True), "fontColor": color(TINTA),
                                         "horizontalAlignment": lit("left"), "leftMargin": lit(12)},
                                hover={"show": lit(True), "text": lit(texto), "fontSize": lit(10.0),
                                       "bold": lit(True), "fontColor": color(AZUL),
                                       "horizontalAlignment": lit("left"), "leftMargin": lit(12)}),
                "icon": estados(default={"show": lit(False)}),
            },
            "visualContainerObjects": {
                "visualLink": [{"properties": accion}],
                "general": [{"properties": {"altText": lit(texto)}}],
            },
        },
    }


def rotulo(pagina, texto, z):
    return {
        "$schema": SCHEMA, "name": hid(f"{pagina}/rotulo"),
        "position": {"x": X + 4, "y": Y0, "z": z, "width": ANCHO - 4, "height": 24, "tabOrder": z},
        "visual": {"visualType": "textbox",
                   "objects": {"general": [{"properties": {"paragraphs": [{"textRuns": [{
                       "value": texto, "textStyle": {"fontWeight": "bold", "fontSize": "9pt", "color": GRIS}}]}]}}]},
                   "visualContainerObjects": {"background": [{"properties": {"show": lit(False)}}],
                                              "padding": [{"properties": {k: lit(0.0) for k in
                                                                          ("top", "bottom", "left", "right")}}]}},
    }


def guardar(pagina, d):
    ruta = os.path.join(PAGES, pagina, "visuals", d["name"], "visual.json")
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    json.dump(d, open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def main():
    for pagina in PRINCIPALES + [RIESGO, DEPARTAMENTOS]:
        z = 90000   # por encima de todo lo que hay en las páginas
        if pagina in PRINCIPALES:
            piezas = [rotulo(pagina, "VER DETALLE", z),
                      boton(pagina, "riesgo", "Riesgo por cliente  →", Y0 + 30, z + 100, RIESGO),
                      boton(pagina, "departamentos", "Tickets por departamento  →", Y0 + 82, z + 200, DEPARTAMENTOS)]
        else:
            otra = DEPARTAMENTOS if pagina == RIESGO else RIESGO
            piezas = [rotulo(pagina, "NAVEGACIÓN", z),
                      boton(pagina, "volver", "←  Volver", Y0 + 30, z + 100),
                      boton(pagina, "otra", f"{TEXTO[otra]}  →", Y0 + 82, z + 200, otra)]
        for p in piezas:
            guardar(pagina, p)

    for pagina in (RIESGO, DEPARTAMENTOS):   # ocultas en las pestañas al leer el informe
        pj = os.path.join(PAGES, pagina, "page.json")
        page = json.load(open(pj, encoding="utf-8"))
        page["visibility"] = "HiddenInViewMode"
        json.dump(page, open(pj, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"ok: navegación en {len(PRINCIPALES)} páginas principales y 2 de detalle (ocultas en las pestañas)")


if __name__ == "__main__":
    main()
