"""Cinta de cabecera en las 5 páginas principales (aprobada por el usuario el 2026-11-17).

- Fondo de página = SVG con la cinta azul (y 0–96, degradado, franjas), icono de la página (el de su tarjeta de
  Inicio), separador y «BRÚJULA SOPORTE IT · SERVICE DESK».
- Título de la página dentro de la cinta en blanco; tarjeta «Periodo analizado» a la derecha, con fondo blanco.
- Panel de filtros desde y 106 y segmentadores cada 92 px desde y 158 (x 28).
- Contenido desde y 162 (encajes por página en MOVER).
Las pestañas las coloca add_pestanas.py (y 106). Mueve posiciones de forma relativa: no se aplica dos veces
(si el título ya está en la cinta, la página se salta).

Uso: python -X utf8 add_cinta.py <carpeta Brujula SLA.Report>
Desktop debe estar cerrado.
"""
import glob, json, os, shutil, sys

REPORT = sys.argv[1]
DEF = os.path.join(REPORT, "definition")
PAGES = os.path.join(DEF, "pages")
RES_DIR = os.path.join(REPORT, "StaticResources", "RegisteredResources")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_pagina_inicio import ICONOS  # mismos iconos que las tarjetas de Inicio

PAGINAS = {  # página: (icono, id del cuadro de texto del título)
    "8d6200671df52c4495f0": ("objetivo", "3ab0c78099b049308ef6"),
    "3c0c6420ac95cc7d08c6": ("lista", "80833ea6210da7d9f1c6"),
    "566eea23ca0f45d8afeb": ("evolucion", "a2fe5ad8ac399a565105"),
    "2384e88904eb3db36349": ("euro", "31b1c5078d6c435d5ec2"),
    "d9140412a99203aedb0f": ("barras", "b52f10c84ea16f2acf91"),
    # páginas de detalle (añadidas el 2026-11-17): sin pestañas, contenido desde y 106
    "a32a3f23226e91ff42b8": ("alerta", "15cf4564d17b7631eb43"),
    "d6d9e9f29a60d35c5880": ("organigrama", "5d10984ded232ecc3a95"),
}
ICONOS = dict(ICONOS,
              alerta='<polygon points="0,-10 10,8 -10,8" fill="none" stroke="#FFF" stroke-width="2" '
                     'stroke-linejoin="round"/><line x1="0" y1="-3" x2="0" y2="2" stroke="#FFF" stroke-width="2" '
                     'stroke-linecap="round"/><circle cy="5" r="1.3" fill="#FFF"/>',
              organigrama='<g stroke="#FFF" stroke-width="1.8" fill="none"><rect x="-4" y="-11" width="8" height="6" '
                          'rx="1"/><polyline points="0,-5 0,-1"/><polyline points="-8,3 -8,-1 8,-1 8,3"/>'
                          '<rect x="-12" y="3" width="8" height="6" rx="1"/><rect x="4" y="3" width="8" height="6" '
                          'rx="1"/></g>')
# Páginas con lienzo más bajo (pedido por el usuario el 2026-11-17): alto del lienzo; el panel de filtros acaba
# 30 px antes del borde. La imagen de la cinta se genera con ese alto (con «Ajustar» no se deforma).
ALTO_PAGINA = {"d6d9e9f29a60d35c5880": 800}
ANTETITULO = "BRÚJULA SOPORTE IT · SERVICE DESK"   # el cuadro de texto antiguo se borra (va en la cinta)
FONDO = "#F4F6F9"
Y_CONTENIDO = 162

# Posiciones nuevas por prefijo de id: (x, y, ancho, alto); None = se mantiene
MOVER = {
    "3c0c6420ac95cc7d08c6": {"e8bec6": (None, 162, None, None), "baca46": (288, 214, 1616, 846)},
    "566eea23ca0f45d8afeb": {"ec7a8e": (288, 162, 1616, 286), "e0a4f1": (288, 464, 1616, 286),
                             "d90787": (288, 766, 1616, 286)},
    "2384e88904eb3db36349": {"814f91": (None, 162, None, 150), "e66c64": (None, 162, None, 150),
                             "dc3211": (None, 162, None, 150), "515d00": (None, 162, None, 150),
                             "a298d2": (None, 196, None, None), "cdfdb2": (None, 196, None, None),
                             "2c29fa": (None, 262, None, None), "beba02": (None, 262, None, None),
                             "0bf66d": (None, 262, None, None), "064c17": (None, 262, None, None),
                             "4d3510": (288, 316, 1616, 300), "ae48d7": (288, 620, 1616, 440)},
    "d9140412a99203aedb0f": {"d278a4": (None, 162, None, 130), "f93475": (None, 162, None, 130),
                             "506ed5": (None, 162, None, 130), "84aa23": (288, 304, 1616, 320),
                             "12c1c1": (288, 636, 1616, 424)},
    "a32a3f23226e91ff42b8": {"339946": (288, 106, 1616, 44), "882ec4": (288, 156, 1616, 776),
                             "f7276e": (None, 944, None, None), "133c98": (None, 944, None, None),
                             "e06645": (None, 944, None, None), "f524c0": (None, 944, None, None),
                             "58b160": (None, 944, None, None), "9e94f7": (288, 1032, 1616, 36)},
    "d6d9e9f29a60d35c5880": {"58d9bf": (288, 110, 1616, 24), "3f3a32": (288, 144, 1616, 556),
                             "2283c2": (None, 716, None, None), "a808d1": (None, 716, None, None),
                             "61d9d5": (None, 716, None, None), "2d0776": (None, 716, None, None)},
}


def lit(v):
    if isinstance(v, bool):
        return {"expr": {"Literal": {"Value": "true" if v else "false"}}}
    if isinstance(v, float):
        return {"expr": {"Literal": {"Value": f"{v}D"}}}
    return {"expr": {"Literal": {"Value": "'" + str(v) + "'"}}}


def svg_cinta(icono, alto=1080):
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="{alto}" viewBox="0 0 1920 {alto}" '
        'font-family="Segoe UI, sans-serif">',
        '<defs><linearGradient id="g" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="#16314F"/>'
        '<stop offset="0.55" stop-color="#1F3A5F"/><stop offset="1" stop-color="#2E5C8A"/></linearGradient></defs>',
        f'<rect width="1920" height="{alto}" fill="{FONDO}"/>',
        '<rect width="1920" height="96" fill="url(#g)"/>',
        '<polygon points="1250,96 1312,0 1352,0 1290,96" fill="#FFF" opacity="0.06"/>',
        '<polygon points="1340,96 1402,0 1462,0 1400,96" fill="#FFF" opacity="0.08"/>',
        '<polygon points="1450,96 1512,0 1542,0 1480,96" fill="#FFF" opacity="0.06"/>',
        f'<g transform="translate(58,48)"><circle r="28" fill="#FFF" fill-opacity="0.12"/>'
        f'<g transform="scale(1.6)">{ICONOS[icono]}</g></g>',
        '<line x1="104" y1="22" x2="104" y2="74" stroke="#FFF" stroke-opacity="0.4" stroke-width="2"/>',
        '<text x="124" y="34" fill="#C9D6E6" font-size="14" font-weight="700" letter-spacing="1">'
        'BRÚJULA SOPORTE IT · SERVICE DESK</text>',
        '</svg>'])


def cargar(f):
    return json.load(open(f, encoding="utf-8"))


def guardar(f, d):
    json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def mover(pos, x=None, y=None, w=None, h=None):
    for k, v in (("x", x), ("y", y), ("width", w), ("height", h)):
        if v is not None:
            pos[k] = v


def pagina_cumplimiento(visuales):
    """Franja de objetivos 88→162 (alto 88) y 4 bloques de KPI cada 196 px con tarjetas de 140."""
    bloques = [200, 402, 604, 806]
    for d in visuales:
        p = d["position"]
        if p["x"] < 288 or p.get("z", 0) >= 95000:
            continue
        y = p["y"]
        if 88 <= y < 200:
            p["y"] = y + 74
            if d["name"].startswith("8c0c70"):
                p["height"] = 88
        elif 200 <= y < 1040:
            i = max(k for k, L in enumerate(bloques) if L <= y)
            nuevo = 262 + 196 * i
            if d["name"].startswith("ff5694"):          # «€ Penaliza en factura» al pie de su tarjeta
                p["y"] = nuevo + 36 + 112
            else:
                p["y"] = nuevo + (y - bloques[i])
            if p["height"] == 150:
                p["height"] = 140
        elif y >= 1040:
            p["y"] = 1036


def main():
    rj = os.path.join(DEF, "report.json")
    rep = cargar(rj)
    paquete = next(p for p in rep["resourcePackages"] if p["name"] == "RegisteredResources")
    for pagina, (icono, titulo_id) in PAGINAS.items():
        base = os.path.join(PAGES, pagina)
        archivos = {f: cargar(f) for f in glob.glob(os.path.join(base, "visuals", "*", "visual.json"))}
        titulo = next(d for d in archivos.values() if d["name"] == titulo_id)
        if titulo["position"]["y"] == 42:
            print(f"{pagina}: ya tiene la cinta, se salta")
            continue

        # fondo con la cinta
        imagen = f"cinta_{icono}.svg"
        open(os.path.join(RES_DIR, imagen), "w", encoding="utf-8").write(svg_cinta(icono, ALTO_PAGINA.get(pagina, 1080)))
        if not any(it["name"] == imagen for it in paquete["items"]):
            paquete["items"].append({"name": imagen, "path": imagen, "type": "Image"})
        pj = os.path.join(base, "page.json")
        page = cargar(pj)
        url = {"expr": {"ResourcePackageItem": {"PackageName": "RegisteredResources", "PackageType": 1,
                                                "ItemName": imagen}}}
        page.setdefault("objects", {})["background"] = [{"properties": {
            "color": {"solid": {"color": lit(FONDO)}}, "transparency": lit(0.0),
            "image": {"image": {"name": lit(imagen), "url": url, "scaling": lit("Fit")}}}}]
        guardar(pj, page)

        # título en la cinta, en blanco
        mover(titulo["position"], 120, 42, 1000, 44)
        for par in titulo["visual"]["objects"]["general"][0]["properties"]["paragraphs"]:
            for run in par["textRuns"]:
                run.setdefault("textStyle", {}).update({"color": "#FFFFFF", "fontSize": "24pt", "fontWeight": "bold"})
        vco_t = titulo["visual"].setdefault("visualContainerObjects", {})
        vco_t["padding"] = [{"properties": {k: lit(0.0) for k in ("top", "bottom", "left", "right")}}]
        vco_t["background"] = [{"properties": {"show": lit(False)}}]

        visuales = list(archivos.values())
        slicers = []
        for d in visuales:
            v, p = d.get("visual", {}), d["position"]
            t = v.get("visualType")
            if t == "cardVisual" and "Periodo seleccionado" in json.dumps(v.get("query", {}), ensure_ascii=False):
                mover(p, 1552, 12, 340, 72)
                vco = v.setdefault("visualContainerObjects", {})
                vco["background"] = [{"properties": {"show": lit(True), "color": {"solid": {"color": lit("#FFFFFF")}},
                                                     "transparency": lit(0.0)}}]
                borde = vco.setdefault("border", [{"properties": {}}])[0]["properties"]
                borde["radius"] = lit(10.0)
            elif t == "shape" and p["x"] < 40 and p["height"] > 900:          # panel de filtros
                mover(p, y=106, h=962)
            elif t == "textbox" and p["x"] < 288 and "Filtros" in json.dumps(v, ensure_ascii=False):
                mover(p, y=118)
            elif t == "slicer" and p["x"] < 288:
                slicers.append(d)
        for k, d in enumerate(sorted(slicers, key=lambda d: d["position"]["y"])):
            mover(d["position"], x=28, y=158 + 92 * k)

        if pagina == "8d6200671df52c4495f0":
            pagina_cumplimiento(visuales)
        for d in visuales:
            for pref, (x, y, w, h) in MOVER.get(pagina, {}).items():
                if d["name"].startswith(pref):
                    mover(d["position"], x, y, w, h)
        for f, d in archivos.items():
            if d["visual"].get("visualType") == "textbox" and ANTETITULO in json.dumps(d, ensure_ascii=False):
                shutil.rmtree(os.path.dirname(f))      # antetítulo antiguo: ahora está dibujado en la cinta
            else:
                guardar(f, d)
        print(f"{pagina}: cinta aplicada ({imagen}, {len(slicers)} segmentadores)")
    guardar(rj, rep)
    ajustar_altos()


def ajustar_altos():
    """Lienzo más bajo en ALTO_PAGINA (se puede relanzar: fija valores absolutos)."""
    for pagina, alto in ALTO_PAGINA.items():
        icono = PAGINAS[pagina][0]
        open(os.path.join(RES_DIR, f"cinta_{icono}.svg"), "w", encoding="utf-8").write(svg_cinta(icono, alto))
        pj = os.path.join(PAGES, pagina, "page.json")
        page = cargar(pj)
        page["height"] = alto
        guardar(pj, page)
        for f in glob.glob(os.path.join(PAGES, pagina, "visuals", "*", "visual.json")):
            d = cargar(f)
            p = d["position"]
            if d["visual"].get("visualType") == "shape" and p["x"] < 40 and p["y"] == 106:   # panel de filtros
                p["height"] = alto - 136
                guardar(f, d)
            elif p["y"] + p["height"] > alto:
                print(f"  aviso: {d['name']} se sale del lienzo de {alto}")
        print(f"{pagina}: lienzo de 1920×{alto}")


if __name__ == "__main__":
    main()
