"""Barra de pestañas de navegación entre las 5 páginas principales (aprobada por el usuario el 2026-11-16).

En cada página principal: 5 botones arriba (y = 4), la pestaña de la página actual en azul oscuro con texto
blanco y las demás en blanco con borde gris, que navegan a su página. Quita el antetítulo
«BRÚJULA SOPORTE IT · SERVICE DESK» de esas páginas (ocupa ese hueco) y renombra la página 5.
Solo añade o sustituye sus propios botones (ids fijos): se puede volver a ejecutar.

Uso: python -X utf8 add_pestanas.py <carpeta Brujula SLA.Report>
Desktop debe estar cerrado (al guardar reescribe el informe).
"""
import glob, hashlib, json, os, shutil, sys

PAGES = os.path.join(sys.argv[1], "definition", "pages")
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json"
PESTANAS = [  # página, texto de la pestaña (= nombre de la página)
    ("8d6200671df52c4495f0", "Cumplimiento de KPIs"),
    ("3c0c6420ac95cc7d08c6", "Detalle de indicadores"),
    ("566eea23ca0f45d8afeb", "Evolución del cumplimiento"),
    ("2384e88904eb3db36349", "Resultado económico del sprint"),
    ("d9140412a99203aedb0f", "Impacto económico acumulado"),
]
ANTETITULO = "BRÚJULA SOPORTE IT · SERVICE DESK"
X0, Y, ANCHO, ALTO, HUECO = 288, 106, 240, 44, 8   # debajo de la cinta (add_cinta.py)
AZUL, TINTA, BORDE, HOVER = "#1F3A5F", "#1B1F24", "#C5CBD3", "#EEF3F9"


def hid(clave):
    return hashlib.sha1(f"pestanas/{clave}".encode("utf-8")).hexdigest()[:20]


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


def estados(default, hover=None):
    """Entrada sin selector + una por estado (los actionButton necesitan las dos)."""
    out = [{"properties": default}, {"properties": default, "selector": {"id": "default"}}]
    if hover:
        out.append({"properties": hover, "selector": {"id": "hover"}})
    return out


def texto(t, fuente):
    return {"show": lit(True), "text": lit(t), "fontSize": lit(10.0), "bold": lit(True), "fontColor": color(fuente),
            "horizontalAlignment": lit("center"), "verticalAlignment": lit("middle")}


def pestana(pagina, i, destino, nombre):
    activa = destino == pagina
    fondo = AZUL if activa else "#FFFFFF"
    objetos = {
        "shape": [{"properties": {"tileShape": lit("rectangleRounded"), "roundEdge": lit(25)}}],   # redondeo del 25 %
        "fill": estados({"show": lit(True), "fillColor": color(fondo), "transparency": lit(0.0)},
                        None if activa else {"show": lit(True), "fillColor": color(HOVER), "transparency": lit(0.0)}),
        "outline": estados({"show": lit(True), "lineColor": color(AZUL if activa else BORDE), "weight": lit(1.0),
                            "transparency": lit(0.0)},
                           None if activa else {"show": lit(True), "lineColor": color(AZUL), "weight": lit(1.0),
                                                "transparency": lit(0.0)}),
        "text": estados(texto(nombre, "#FFFFFF" if activa else TINTA),
                        None if activa else texto(nombre, AZUL)),
        "icon": estados({"show": lit(False)}),
    }
    vco = {"general": [{"properties": {"altText": lit(f"Pestaña: {nombre}" + (" (página actual)" if activa else ""))}}]}
    if not activa:
        vco["visualLink"] = [{"properties": {"show": lit(True), "type": lit("PageNavigation"),
                                             "navigationSection": lit(destino), "tooltip": lit(f"Ir a {nombre}")}}]
    z = 95000 + i
    return {
        "$schema": SCHEMA, "name": hid(f"{pagina}/{i}"),
        "position": {"x": X0 + i * (ANCHO + HUECO), "y": Y, "z": z, "width": ANCHO, "height": ALTO, "tabOrder": z},
        "visual": {"visualType": "actionButton", "objects": objetos, "visualContainerObjects": vco},
    }


def main():
    for pagina, nombre in PESTANAS:
        base = os.path.join(PAGES, pagina)
        # nombre de la página = texto de su pestaña
        pj = os.path.join(base, "page.json")
        page = json.load(open(pj, encoding="utf-8"))
        page["displayName"] = nombre
        json.dump(page, open(pj, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        # fuera el antetítulo (su hueco lo ocupa la barra)
        for f in glob.glob(os.path.join(base, "visuals", "*", "visual.json")):
            d = json.load(open(f, encoding="utf-8"))
            if d["visual"]["visualType"] == "textbox" and ANTETITULO in json.dumps(d, ensure_ascii=False):
                shutil.rmtree(os.path.dirname(f))
        for i, (destino, texto_p) in enumerate(PESTANAS):
            v = pestana(pagina, i, destino, texto_p)
            ruta = os.path.join(base, "visuals", v["name"], "visual.json")
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            json.dump(v, open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"ok: barra de {len(PESTANAS)} pestañas en {len(PESTANAS)} páginas")


if __name__ == "__main__":
    main()
