"""Botones «← Atrás» y «⌂ Inicio» en la cinta azul de las 7 páginas (add_cinta.py), a la izquierda
de la tarjeta de periodo. Inicio lleva a la portada (add_pagina_inicio.py); Atrás vuelve a la página anterior.

Texto blanco sobre fondo transparente con borde blanco fino; al pasar el ratón el fondo se aclara.
Se puede relanzar (reescribe sus dos botones en cada página).

Uso: python -X utf8 add_boton_inicio.py "<carpeta Brujula SLA.Report>"
"""
import hashlib, json, os, sys

REPORT = sys.argv[1]
PAGES = os.path.join(REPORT, "definition", "pages")
SCHEMA_V = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json"
PORTADA = hashlib.sha1(b"inicio/pagina").hexdigest()[:20]
PAGINAS = ["8d6200671df52c4495f0", "3c0c6420ac95cc7d08c6", "566eea23ca0f45d8afeb", "2384e88904eb3db36349",
           "d9140412a99203aedb0f", "a32a3f23226e91ff42b8", "d6d9e9f29a60d35c5880"]

Y, ANCHO, ALTO = 26, 112, 44
BOTONES = [  # clave, x, texto, enlace
    ("atras", 1300, "←  Atrás", {"type": "'Back'", "tooltip": "'Volver a la página anterior'"}),
    ("inicio", 1424, "⌂  Inicio", {"type": "'PageNavigation'", "navigationSection": f"'{PORTADA}'",
                                    "tooltip": "'Ir a la portada'"}),
]
BLANCO = "#FFFFFF"


def lit(v):
    if isinstance(v, bool):
        v = "true" if v else "false"
    elif isinstance(v, int):
        v = f"{v}L"
    elif isinstance(v, float):
        v = f"{v}D"
    return {"expr": {"Literal": {"Value": v}}}


def color(h):
    return {"solid": {"color": lit(f"'{h}'")}}


def estados(default, hover):
    """Entrada sin selector + una por estado (los actionButton necesitan las dos)."""
    return [{"properties": default}, {"properties": default, "selector": {"id": "default"}},
            {"properties": hover, "selector": {"id": "hover"}}]


def boton(pagina, clave, x, texto, enlace, z):
    txt = {"show": lit(True), "text": lit(f"'{texto}'"), "fontColor": color(BLANCO), "fontSize": lit(12.0),
           "bold": lit(True), "horizontalAlignment": lit("'center'"), "verticalAlignment": lit("'middle'")}
    return {
        "$schema": SCHEMA_V,
        "name": hashlib.sha1(f"boton_{clave}/{pagina}".encode()).hexdigest()[:20],
        "position": {"x": x, "y": Y, "z": z, "width": ANCHO, "height": ALTO, "tabOrder": z},
        "visual": {
            "visualType": "actionButton",
            "objects": {
                "shape": [{"properties": {"tileShape": lit("'rectangleRounded'"), "roundEdge": lit(8)}}],
                "fill": estados({"show": lit(True), "fillColor": color(BLANCO), "transparency": lit(100.0)},
                                {"show": lit(True), "fillColor": color(BLANCO), "transparency": lit(82.0)}),
                "outline": estados({"show": lit(True), "lineColor": color(BLANCO), "weight": lit(1.0),
                                    "transparency": lit(45.0)},
                                   {"show": lit(True), "lineColor": color(BLANCO), "weight": lit(1.5),
                                    "transparency": lit(0.0)}),
                "text": estados(txt, txt),
                "icon": estados({"show": lit(False)}, {"show": lit(False)}),
            },
            "visualContainerObjects": {
                "visualLink": [{"properties": {"show": lit(True), **{k: lit(v) for k, v in enlace.items()}}}],
                "general": [{"properties": {"altText": lit(f"'{enlace['tooltip'][1:-1]}'")}}],
                "visualHeader": [{"properties": {"show": lit(False)}}],
            },
        },
    }


def main():
    for pagina in PAGINAS:
        for i, (clave, x, texto, enlace) in enumerate(BOTONES):
            v = boton(pagina, clave, x, texto, enlace, 30000 + i * 100)
            carpeta = os.path.join(PAGES, pagina, "visuals", v["name"])
            os.makedirs(carpeta, exist_ok=True)
            with open(os.path.join(carpeta, "visual.json"), "w", encoding="utf-8") as f:
                json.dump(v, f, ensure_ascii=False, indent=2)
                f.write("\n")
        print(pagina, "· Atrás e Inicio")


if __name__ == "__main__":
    main()
