"""Página «Inicio» (portada) aprobada por el usuario el 2026-11-17.

- Fondo de página = una imagen SVG (inicio_fondo.svg, en RegisteredResources) con el banner
  «BRÚJULA SOPORTE IT · SERVICE DESK» (degradado azul, franjas, brújula) y las 5 tarjetas dibujadas
  (icono, título, descripción, «Abrir →»).
- Título y subtítulo como cuadros de texto (editables en Desktop).
- Encima de cada tarjeta un botón transparente que navega a su página; al pasar el ratón la tiñe de azul.
- La página va la primera y queda como página activa al abrir el informe.
Solo crea o sustituye su página, su imagen y su entrada en report.json: se puede volver a ejecutar.

Uso: python -X utf8 add_pagina_inicio.py <carpeta Brujula SLA.Report>
Desktop debe estar cerrado (al guardar reescribe el informe).
"""
import hashlib, json, os, sys

REPORT = sys.argv[1]
DEF = os.path.join(REPORT, "definition")
PAGES = os.path.join(DEF, "pages")
RES_DIR = os.path.join(REPORT, "StaticResources", "RegisteredResources")
SCHEMA_V = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json"
SCHEMA_P = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"
PAGINA = hashlib.sha1(b"inicio/pagina").hexdigest()[:20]
IMAGEN = "inicio_fondo.svg"
W, H = 1920, 1080
AZUL, TINTA, GRIS, BORDE, FONDO = "#1F3A5F", "#1B1F24", "#5A6270", "#D5DAE1", "#F4F6F9"

# x de cada tarjeta = X0 + i * (ANCHO + HUECO)
X0, Y_T, ANCHO, ALTO, HUECO = 72, 390, 328, 470, 34

# Iconos dibujados alrededor de (0, 0), en blanco, para un círculo de radio 18 (se escalan).
ICONOS = {
    "objetivo": '<circle r="9" fill="none" stroke="#FFF" stroke-width="1.8"/>'
                '<polyline points="-4.5,0 -1,3.5 5,-3.5" fill="none" stroke="#FFF" stroke-width="2" '
                'stroke-linecap="round" stroke-linejoin="round"/>',
    "lista": '<g stroke="#FFF" stroke-width="2" stroke-linecap="round"><line x1="-3" y1="-6" x2="8" y2="-6"/>'
             '<line x1="-3" y1="0" x2="8" y2="0"/><line x1="-3" y1="6" x2="8" y2="6"/></g>'
             '<g fill="#FFF"><circle cx="-7.5" cy="-6" r="1.8"/><circle cx="-7.5" cy="0" r="1.8"/>'
             '<circle cx="-7.5" cy="6" r="1.8"/></g>',
    # gráfico de líneas: ejes + serie ascendente con puntos
    "evolucion": '<polyline points="-11,-11 -11,10 11,10" fill="none" stroke="#FFF" stroke-width="1.6" '
                 'stroke-linecap="round" stroke-linejoin="round" opacity="0.75"/>'
                 '<polyline points="-6,4 -1,-1 3,2 9,-7" fill="none" stroke="#FFF" stroke-width="2" '
                 'stroke-linecap="round" stroke-linejoin="round"/>'
                 '<g fill="#FFF"><circle cx="-6" cy="4" r="2"/><circle cx="-1" cy="-1" r="2"/>'
                 '<circle cx="3" cy="2" r="2"/><circle cx="9" cy="-7" r="2"/></g>',
    "euro": '<text y="6.5" text-anchor="middle" fill="#FFF" font-size="19" font-weight="700">€</text>',
    "barras": '<g fill="#FFF"><rect x="-9" y="1" width="4" height="7" rx="1"/>'
              '<rect x="-2" y="-4" width="4" height="12" rx="1"/><rect x="5" y="-9" width="4" height="17" rx="1"/></g>',
}

TARJETAS = [  # página destino, icono, título (2 líneas), descripción (líneas)
    # textos aprobados por el usuario el 2026-11-17
    ("8d6200671df52c4495f0", "objetivo", ["Cumplimiento", "de KPI"],
     ["Grado de cumplimiento de", "los 15 indicadores del", "servicio."]),
    ("3c0c6420ac95cc7d08c6", "lista", ["Detalle de", "indicadores"],
     ["Desglose de resultados", "por tipología de", "indicador."]),
    ("566eea23ca0f45d8afeb", "evolucion", ["Evolución del", "cumplimiento"],
     ["Tendencia del", "cumplimiento a lo largo", "de los sprints."]),
    ("2384e88904eb3db36349", "euro", ["Resultado", "económico del sprint"],
     ["Facturación,", "bonificaciones,", "penalizaciones y", "balance neto."]),
    ("d9140412a99203aedb0f", "barras", ["Impacto económico", "acumulado"],
     ["Impacto acumulado y", "clientes con mayor", "penalización."]),
]


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg_fondo():
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
         'font-family="Segoe UI, Segoe UI Semibold, sans-serif">',
         '<defs>'
         '<linearGradient id="g" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="#16314F"/>'
         '<stop offset="0.55" stop-color="#1F3A5F"/><stop offset="1" stop-color="#2E5C8A"/></linearGradient>'
         '<linearGradient id="gi" x1="0" x2="1" y1="0" y2="1"><stop offset="0" stop-color="#2E5C8A"/>'
         '<stop offset="1" stop-color="#16314F"/></linearGradient>'
         '<filter id="s" x="-10%" y="-10%" width="120%" height="125%">'
         '<feDropShadow dx="0" dy="4" stdDeviation="8" flood-color="#1F3A5F" flood-opacity="0.10"/></filter>'
         f'<clipPath id="ct"><rect width="{ANCHO}" height="{ALTO}" rx="14"/></clipPath>'
         '</defs>',
         f'<rect width="{W}" height="{H}" fill="{FONDO}"/>',
         # banner
         f'<rect width="{W}" height="200" fill="url(#g)"/>',
         '<polygon points="1330,200 1460,0 1530,0 1400,200" fill="#FFF" opacity="0.06"/>',
         '<polygon points="1480,200 1610,0 1720,0 1590,200" fill="#FFF" opacity="0.08"/>',
         '<polygon points="1690,200 1820,0 1890,0 1760,200" fill="#FFF" opacity="0.06"/>',
         '<g transform="translate(130,100)">'
         '<circle r="54" fill="none" stroke="#FFF" stroke-width="4"/>'
         '<polygon points="0,-40 13,0 0,40 -13,0" fill="none" stroke="#FFF" stroke-width="3.5" stroke-linejoin="round"/>'
         '<polygon points="0,-40 13,0 -13,0" fill="#FFF"/>'
         '<circle r="5" fill="#1F3A5F"/></g>',
         '<line x1="226" y1="52" x2="226" y2="148" stroke="#FFF" stroke-opacity="0.5" stroke-width="2.5"/>',
         '<text x="266" y="116" fill="#FFF" font-size="42" font-weight="700" letter-spacing="1.5">'
         'BRÚJULA SOPORTE IT · SERVICE DESK</text>']
    for i, (_, icono, titulo, desc) in enumerate(TARJETAS):
        x = X0 + i * (ANCHO + HUECO)
        p.append(f'<g transform="translate({x},{Y_T})">'
                 f'<rect width="{ANCHO}" height="{ALTO}" rx="14" fill="#FFF" stroke="{BORDE}" filter="url(#s)"/>'
                 f'<rect width="{ANCHO}" height="8" fill="{AZUL}" clip-path="url(#ct)"/>'
                 f'<g transform="translate(76,104)"><circle r="44" fill="url(#gi)"/>'
                 f'<g transform="scale(2.4)">{ICONOS[icono]}</g></g>')
        for j, linea in enumerate(titulo):
            p.append(f'<text x="32" y="{210 + j * 36}" fill="{TINTA}" font-size="27" font-weight="700">{esc(linea)}</text>')
        for j, linea in enumerate(desc):
            p.append(f'<text x="32" y="{300 + j * 30}" fill="{GRIS}" font-size="19">{esc(linea)}</text>')
        p.append(f'<text x="32" y="{ALTO - 40}" fill="{AZUL}" font-size="20" font-weight="700">Abrir  →</text></g>')
    p.append(f'<text x="{X0}" y="1030" fill="#8A9099" font-size="15">Brújula Soporte IT es una empresa ficticia · '
             'datos sintéticos con fines de demostración</text>')
    p.append('</svg>')
    return "\n".join(p)


def hid(clave):
    return hashlib.sha1(f"inicio/{clave}".encode("utf-8")).hexdigest()[:20]


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


def estados(default, hover):
    """Entrada sin selector + una por estado (los actionButton necesitan las dos)."""
    return [{"properties": default}, {"properties": default, "selector": {"id": "default"}},
            {"properties": hover, "selector": {"id": "hover"}}]


def boton(i, destino, nombre):
    z = 20000 + i * 100
    return {
        "$schema": SCHEMA_V, "name": hid(f"boton/{i}"),
        "position": {"x": X0 + i * (ANCHO + HUECO), "y": Y_T, "z": z, "width": ANCHO, "height": ALTO, "tabOrder": z},
        "visual": {
            "visualType": "actionButton",
            "objects": {
                "shape": [{"properties": {"tileShape": lit("rectangleRounded"), "roundEdge": lit(4)}}],
                "fill": estados({"show": lit(True), "fillColor": color(AZUL), "transparency": lit(100.0)},
                                {"show": lit(True), "fillColor": color(AZUL), "transparency": lit(93.0)}),
                "outline": estados({"show": lit(False)},
                                   {"show": lit(True), "lineColor": color(AZUL), "weight": lit(2.0),
                                    "transparency": lit(0.0)}),
                "text": estados({"show": lit(False)}, {"show": lit(False)}),
                "icon": estados({"show": lit(False)}, {"show": lit(False)}),
            },
            "visualContainerObjects": {
                "visualLink": [{"properties": {"show": lit(True), "type": lit("PageNavigation"),
                                               "navigationSection": lit(destino), "tooltip": lit(f"Ir a {nombre}")}}],
                "general": [{"properties": {"altText": lit(f"Ir a la página {nombre}")}}],
            },
        },
    }


def cuadro_texto(clave, texto, y, alto, tam, negrita, col, z):
    estilo = {"fontSize": f"{tam}pt", "color": col, "fontFamily": "Segoe UI"}
    if negrita:
        estilo["fontWeight"] = "bold"
    return {
        "$schema": SCHEMA_V, "name": hid(clave),
        "position": {"x": X0 - 4, "y": y, "z": z, "width": 1500, "height": alto, "tabOrder": z},
        "visual": {"visualType": "textbox",
                   "objects": {"general": [{"properties": {"paragraphs": [{"textRuns": [{
                       "value": texto, "textStyle": estilo}]}]}}]},
                   "visualContainerObjects": {"background": [{"properties": {"show": lit(False)}}],
                                              "padding": [{"properties": {k: lit(0.0) for k in
                                                                          ("top", "bottom", "left", "right")}}]}},
    }


def guardar(ruta, d):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    json.dump(d, open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def main():
    # 1) imagen de fondo + registro en report.json
    os.makedirs(RES_DIR, exist_ok=True)
    open(os.path.join(RES_DIR, IMAGEN), "w", encoding="utf-8").write(svg_fondo())
    rj = os.path.join(DEF, "report.json")
    rep = json.load(open(rj, encoding="utf-8"))
    paquete = next(p for p in rep["resourcePackages"] if p["name"] == "RegisteredResources")
    if not any(it["name"] == IMAGEN for it in paquete["items"]):
        paquete["items"].append({"name": IMAGEN, "path": IMAGEN, "type": "Image"})
    guardar(rj, rep)

    # 2) página
    base = os.path.join(PAGES, PAGINA)
    url = {"expr": {"ResourcePackageItem": {"PackageName": "RegisteredResources", "PackageType": 1,
                                            "ItemName": IMAGEN}}}
    guardar(os.path.join(base, "page.json"), {
        "$schema": SCHEMA_P, "name": PAGINA, "displayName": "Inicio", "displayOption": "FitToPage",
        "height": H, "width": W,
        "objects": {
            "background": [{"properties": {"color": color(FONDO), "transparency": lit(0.0),
                                           "image": {"image": {"name": lit(IMAGEN), "url": url,
                                                               "scaling": lit("Fit")}}}}],
            "outspace": [{"properties": {"color": color(FONDO)}}],
        },
    })
    nombres = {pid: " ".join(titulo) for pid, _, titulo, _ in TARJETAS}   # texto de la tarjeta (tooltip y altText)
    visuales = [cuadro_texto("titulo", "Cuadro de mando del SLA de soporte", 252, 56, 26, True, TINTA, 1000),
                cuadro_texto("subtitulo", "Cumplimiento de objetivos, impacto en la facturación y riesgo por "
                             "cliente · sprints de 3 semanas · 2024–2025", 314, 34, 13, False, GRIS, 1100)]
    visuales += [boton(i, pid, nombres[pid]) for i, (pid, *_) in enumerate(TARJETAS)]
    for v in visuales:
        guardar(os.path.join(base, "visuals", v["name"], "visual.json"), v)

    # 3) primera en el orden y página activa al abrir
    pj = os.path.join(PAGES, "pages.json")
    meta = json.load(open(pj, encoding="utf-8"))
    meta["pageOrder"] = [PAGINA] + [p for p in meta["pageOrder"] if p != PAGINA]
    meta["activePageName"] = PAGINA
    guardar(pj, meta)
    print(f"ok: página Inicio ({PAGINA}) con {len(visuales)} visuales y fondo {IMAGEN}")


if __name__ == "__main__":
    main()
