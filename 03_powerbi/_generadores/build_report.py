"""Genera el informe PBIR de Brujula SLA (página 1: Cumplimiento de objetivos)."""
import hashlib, json, os, shutil, sys, uuid

ROOT = sys.argv[1]                       # carpeta 03_powerbi
NAME = "Brujula SLA"
REP = os.path.join(ROOT, f"{NAME}.Report")
DEF = os.path.join(REP, "definition")
BASE_THEME = sys.argv[2]                 # assets/base.json del skill de diseño

SCH = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
VIS_SCHEMA = f"{SCH}/visualContainer/2.9.0/schema.json"

def hid(key, n=20):
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:n]

def dump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

# ---------- helpers de expresiones ----------
def lit(v):
    if isinstance(v, bool):
        return {"expr": {"Literal": {"Value": "true" if v else "false"}}}
    if isinstance(v, int):
        return {"expr": {"Literal": {"Value": f"{v}L"}}}
    if isinstance(v, float):
        return {"expr": {"Literal": {"Value": f"{v}D"}}}
    return {"expr": {"Literal": {"Value": "'" + str(v).replace("'", "''") + "'"}}}

def num(v):  # numérico decimal (D)
    return {"expr": {"Literal": {"Value": f"{float(v)}D"}}}

def color(hexv):
    return {"solid": {"color": {"expr": {"Literal": {"Value": f"'{hexv}'"}}}}}

def m_expr(entity, prop):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}

def c_expr(entity, prop):
    return {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}

def color_m(entity, prop):
    return {"solid": {"color": {"expr": m_expr(entity, prop)}}}

def proj(expr, entity, prop, display=None):
    p = {"field": expr, "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop}
    if display:
        p["displayName"] = display
    return p

def props(**kw):
    return {"properties": kw}

def sel_default(d):
    d["selector"] = {"id": "default"}
    return d

def vco_basic(bg=None, border=False, padding=0, title=None, title_size=10):
    v = {
        "padding": [props(top=num(padding), bottom=num(padding), left=num(padding), right=num(padding))],
        "border": [props(show=lit(border))],
        "visualHeader": [props(show=lit(False))],
        "dropShadow": [props(show=lit(False))],
    }
    if bg is None:
        v["background"] = [props(show=lit(False))]
    else:
        v["background"] = [props(show=lit(True), color=color(bg), transparency=num(0))]
    if title:
        v["title"] = [props(show=lit(True), text=lit(title), fontSize=num(title_size), bold=lit(True),
                            fontColor=color("#1B1F24"))]
    else:
        v["title"] = [props(show=lit(False))]
    return v

def filter_id(page, vname, kpi_id):
    return {
        "name": "Filter" + hid(f"{page}/{vname}/filter", 24),
        "field": c_expr("Objetivos KPI", "Id"),
        "type": "Categorical",
        "filter": {
            "Version": 2,
            "From": [{"Name": "o", "Entity": "Objetivos KPI", "Type": 0}],
            "Where": [{"Condition": {"In": {
                "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "o"}}, "Property": "Id"}}],
                "Values": [[{"Literal": {"Value": f"{kpi_id}L"}}]]}}}],
        },
        "howCreated": "User",
        "isHiddenInViewMode": True,
    }

class Page:
    def __init__(self, key, display):
        self.key = key
        self.id = hid("page/" + key)
        self.display = display
        self.visuals = []
        self.z = 0

    def add(self, vname, x, y, w, h, visual, filters=None, alt=None):
        self.z += 100
        vid = hid(f"{self.key}/{vname}")
        obj = {"$schema": VIS_SCHEMA, "name": vid,
               "position": {"x": x, "y": y, "z": self.z, "width": w, "height": h, "tabOrder": self.z},
               "visual": visual}
        if alt:
            visual.setdefault("visualContainerObjects", {}).setdefault("general", []).append(props(altText=lit(alt)))
        if filters:
            obj["filterConfig"] = {"filters": filters}
        self.visuals.append(obj)
        return vid

# ---------- primitivas ----------
def shape(fill, radius=12, text=None, font=11, font_color="#FFFFFF", tile="rectangleRounded"):
    objects = {
        "shape": [sel_default(props(tileShape=lit(tile), rectangleRoundedCurve=lit(radius)))],
        "fill": [sel_default(props(show=lit(True), fillColor=color(fill), transparency=num(0)))],
        "outline": [sel_default(props(show=lit(False)))],
    }
    if text:
        objects["text"] = [sel_default(props(show=lit(True), text=lit(text), fontSize=num(font), bold=lit(True),
                                             fontColor=color(font_color), horizontalAlignment=lit("center"),
                                             verticalAlignment=lit("middle")))]
    return {"visualType": "shape", "objects": objects,
            "visualContainerObjects": vco_basic(bg=None, border=False, padding=0)}

def textbox(text, size=12, bold=True, color_hex="#1B1F24"):
    return {"visualType": "textbox", "objects": {"general": [props(paragraphs=[{
        "textRuns": [{"value": text, "textStyle": {"fontWeight": "bold" if bold else "normal",
                                                    "fontSize": f"{size}pt", "color": color_hex}}]}])]},
            "visualContainerObjects": vco_basic(bg=None, border=False, padding=0)}

def card(entity, measure, *, label_text=None, label_pos="aboveValue", value_size=28, value_color="#1B1F24",
         value_color_measure=None, label_size=10, label_color="#605E5C", fill_measure=None, align="left",
         bg="#FFFFFF", border=False, title=None, padding=8, display=None, show_label=True):
    value = props(fontSize=num(value_size), bold=lit(True), horizontalAlignment=lit(align),
                  fontColor=color_m(*value_color_measure) if value_color_measure else color(value_color))
    label = props(show=lit(show_label), fontSize=num(label_size), fontColor=color(label_color),
                  position=lit(label_pos), horizontalAlignment=lit(align))
    if label_text is not None:
        label["properties"]["text"] = lit(label_text)
    objects = {
        "value": [sel_default(value)],
        "label": [sel_default(label)],
        "outline": [sel_default(props(show=lit(False)))],
        "layout": [sel_default(props(paddingUniform=lit(0), topOuterMargin=lit(0), bottomOuterMargin=lit(0),
                                     leftOuterMargin=lit(0), rightOuterMargin=lit(0)))],
    }
    if fill_measure:
        objects["fillCustom"] = [sel_default(props(show=lit(True), fillColor=color_m(*fill_measure), transparency=num(0)))]
        objects["shapeCustomRectangle"] = [props(tileShape=lit("rectangleRounded"), rectangleRoundedCurve=lit(18))]
    return {"visualType": "cardVisual",
            "query": {"queryState": {"Data": {"projections": [proj(m_expr(entity, measure), entity, measure, display)]}}},
            "objects": objects,
            "visualContainerObjects": vco_basic(bg=bg, border=border, padding=padding, title=title, title_size=9)}

def slicer(entity, column, header, *, single=False, default=None, sync=None):
    objects = {
        "data": [props(mode=lit("Dropdown"))],
        "header": [props(show=lit(True), text=lit(header))],
    }
    if single:
        objects["selection"] = [props(strictSingleSelect=lit(True))]
    if default is not None:
        objects["general"] = [props(filter={"filter": {
            "Version": 2,
            "From": [{"Name": "s", "Entity": entity, "Type": 0}],
            "Where": [{"Condition": {"In": {
                "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "s"}}, "Property": column}}],
                "Values": [[{"Literal": {"Value": f"'{default}'"}}]]}}}]}})]
    v = {"visualType": "slicer",
         "query": {"queryState": {"Values": {"projections": [proj(c_expr(entity, column), entity, column)]}}},
         "objects": objects,
         "visualContainerObjects": {
             "background": [props(show=lit(True), color=color("#FFFFFF"), transparency=num(0))],
             "padding": [props(top=num(0), bottom=num(0), left=num(0), right=num(0))],
         }}
    if sync:
        v["syncGroup"] = {"groupName": sync, "fieldChanges": True, "filterChanges": True}
    return v

# ---------- página 1: cumplimiento de objetivos ----------
OK = "Objetivos KPI"
p1 = Page("objetivos", "Cumplimiento de objetivos")

# Panel de filtros
p1.add("rail_bg", 16, 16, 248, 1048, shape("#DDE2E8", radius=10))
p1.add("rail_title", 32, 24, 216, 32, textbox("Filtros", 13, True, "#1B1F24"))
slicers = [
    ("s_anio", "Sprint", "Año", "Año", dict(sync="anio")),
    ("s_sprint", "Sprint", "Sprint", "Sprint", dict(single=True, default="2025-17", sync="sprint")),
    ("s_nivel", "Cliente", "Nivel de contrato", "Nivel de contrato", {}),
    ("s_cliente", "Cliente", "Cliente", "Cliente", {}),
    ("s_dep", "Departamento", "Departamento", "Departamento", {}),
    ("s_tipo", "Política SLA", "Tipo", "Tipo de ticket", {}),
    ("s_prio", "Política SLA", "Prioridad", "Prioridad", {}),
]
for i, (vn, ent, colname, header, kw) in enumerate(slicers):
    p1.add(vn, 28, 64 + i * 92, 224, 80, slicer(ent, colname, header, **kw))
p1.add("rail_note", 28, 720, 224, 120, textbox(
    "Los KPI de negocio (8–11) se calculan por cliente: no cambian con Departamento, Tipo ni Prioridad.",
    9, False, "#3B4048"))

# Cabecera
p1.add("title", 288, 16, 1000, 56, textbox("CUMPLIMIENTO DE LOS OBJETIVOS", 22, True, "#1B1F24"))
p1.add("periodo", 1400, 16, 504, 56, card("Sprint", "Periodo seleccionado", label_text="Periodo analizado",
       value_size=14, label_size=9, align="right", bg=None, padding=0), alt="Sprint seleccionado")

# Resumen por estado
ESTADOS = [("Cumplido", "#1E7B5C", "#DDF1E8", "✓ Cumplidos"), ("Incumplido", "#C0392B", "#F7DDDA", "✗ Incumplidos")]
for i, (est, strong, light, rotulo) in enumerate(ESTADOS):
    x = 288 + i * 820          # dos tarjetas de 796 px con 24 px de separación
    p1.add(f"sum_bg_{i}", x, 88, 796, 96, shape(light, radius=12))
    p1.add(f"sum_now_{i}", x + 24, 100, 96, 72, card(OK, f"KPI {est}", show_label=False, value_size=34,
           bg=None, padding=0, align="center"), alt=f"Número de KPI {est.lower()}s en el sprint seleccionado")
    p1.add(f"sum_pill_{i}", x + 136, 118, 200, 36, shape(strong, radius=18, text=rotulo, font=12, font_color="#FFFFFF"))
    p1.add(f"sum_prev_{i}", x + 600, 100, 172, 72, card(OK, f"KPI {est} sprint anterior", label_text="Sprint anterior",
           label_pos="belowValue", value_size=24, label_size=10, bg=None, padding=0, align="center"),
           alt=f"Número de KPI {est.lower()}s en el sprint anterior")

# Bloques de KPI
BLOQUES = [
    ("KPI TICKETS", [(1, "Ritmo de cierre"), (2, "Backlog al cierre"), (3, "Resolución en primer nivel"), (4, "% Escalados")]),
    ("SLA", [(5, "SLA 1ª respuesta"), (6, "SLA resolución"), (7, "SLA de los P1")]),
    ("NEGOCIO", [(8, "Balance medio por sprint"), (9, "Penalización sobre la cuota"),
                 (10, "Clientes en tramo deficiente"), (11, "Ingresos en riesgo")]),
    ("OPERACIÓN", [(12, "MTTR (horas de SLA)"), (13, "1ª respuesta media"), (14, "Tickets por agente y día"),
                   (15, "% Agentes ausentes")]),
]
y = 200
for bname, kpis in BLOQUES:
    p1.add(f"blk_{bname}", 288, y, 600, 32, textbox(bname, 14, True, "#1B1F24"))
    cy = y + 36
    for j, (kid, kname) in enumerate(kpis):
        x = 288 + j * 404
        f = lambda vn: [filter_id(p1.key, vn, kid)]
        vn = f"kpi_{kid}"
        p1.add(vn, x, cy, 380, 150, card(OK, "Valor KPI", label_text=kname, value_size=30, label_size=11,
               title=f"KPI {kid}", padding=12, display=kname), filters=f(vn),
               alt=f"KPI {kid}: {kname} del sprint seleccionado")
        vn = f"kpi_{kid}_estado"
        p1.add(vn, x + 236, cy + 12, 132, 40, card(OK, "Texto estado", show_label=False, value_size=11,
               value_color_measure=(OK, "Color texto estado"), fill_measure=(OK, "Color estado"),
               align="center", bg=None, padding=0), filters=f(vn), alt=f"Estado del KPI {kid}")
        vn = f"kpi_{kid}_var"
        p1.add(vn, x + 236, cy + 80, 132, 56, card(OK, "Variación KPI texto", label_text="vs sprint anterior",
               value_size=13, label_size=9, value_color_measure=(OK, "Color variación"), align="right",
               bg=None, padding=0), filters=f(vn), alt=f"Variación del KPI {kid} frente al sprint anterior")
    y = cy + 150 + 16

p1.add("footer", 288, 1040, 1616, 28, textbox(
    "Brújula Soporte IT (empresa ficticia) · tickets sintéticos (SEED=42), clima y festivos reales · "
    "objetivos editables en la tabla Objetivos KPI · ↗↘ = variación frente al sprint anterior (pp = puntos)",
    9, False, "#3B4048"))

PAGES = [p1]

# ---------- escritura ----------
if os.path.isdir(os.path.join(DEF, "pages")):
    shutil.rmtree(os.path.join(DEF, "pages"))

theme_name = "BrujulaSLA-7c2e9a41.json"
with open(BASE_THEME, encoding="utf-8") as fh:
    theme = json.load(fh)
theme["name"] = theme_name
# Propiedades de cardVisual del tema base que el validador no reconoce: se quitan
for obj, keys in {"border": ["radius"], "spacing": ["customizeSpacing"], "padding": None}.items():
    for entry in theme.get("visualStyles", {}).get("cardVisual", {}).get("*", {}).get(obj, []):
        for k in (keys or list(entry.keys())):
            entry.pop(k, None)
    cv = theme.get("visualStyles", {}).get("cardVisual", {}).get("*", {})
    if obj in cv and all(not e for e in cv[obj]):
        del cv[obj]
theme["dataColors"] = ["#1F3A5F", "#C0392B", "#1E7B5C", "#B7791F", "#7A8794", "#8C5A3C", "#1F6FB2", "#E3B23C"]
theme["good"], theme["neutral"], theme["bad"] = "#1E7B5C", "#E3B23C", "#C0392B"
theme["background"] = "#FFFFFF"
theme["foreground"] = "#1B1F24"
theme_dir = os.path.join(REP, "StaticResources", "RegisteredResources")
if os.path.isdir(theme_dir):
    shutil.rmtree(theme_dir)
dump(os.path.join(theme_dir, theme_name), theme)

dump(os.path.join(DEF, "version.json"), {
    "$schema": f"{SCH}/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
dump(os.path.join(DEF, "report.json"), {
    "$schema": f"{SCH}/report/3.0.0/schema.json",
    "themeCollection": {"customTheme": {"name": theme_name,
                                        "reportVersionAtImport": {"visual": "2.6.0", "report": "3.1.0", "page": "2.3.0"},
                                        "type": "RegisteredResources"}},
    "resourcePackages": [{"name": "RegisteredResources", "type": "RegisteredResources",
                          "items": [{"name": theme_name, "path": theme_name, "type": "CustomTheme"}]}],
    "settings": {"useStylableVisualContainerHeader": True, "defaultDrillFilterOtherVisuals": True,
                 "allowChangeFilterTypes": True, "useEnhancedTooltips": True},
})
dump(os.path.join(DEF, "pages", "pages.json"), {
    "$schema": f"{SCH}/pagesMetadata/1.0.0/schema.json",
    "pageOrder": [p.id for p in PAGES], "activePageName": PAGES[0].id})
for p in PAGES:
    pdir = os.path.join(DEF, "pages", p.id)
    dump(os.path.join(pdir, "page.json"), {
        "$schema": f"{SCH}/page/2.1.0/schema.json", "name": p.id, "displayName": p.display,
        "displayOption": "FitToPage", "height": 1080, "width": 1920,
        "objects": {"background": [props(color=color("#EEF1F5"), transparency=num(0))],
                    "outspace": [props(color=color("#EEF1F5"))]}})
    for v in p.visuals:
        dump(os.path.join(pdir, "visuals", v["name"], "visual.json"), v)

dump(os.path.join(REP, "definition.pbir"), {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
    "version": "4.0", "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}}})
for folder, typ in [(REP, "Report"), (os.path.join(ROOT, f"{NAME}.SemanticModel"), "SemanticModel")]:
    dump(os.path.join(folder, ".platform"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": typ, "displayName": NAME},
        "config": {"version": "2.0", "logicalId": str(uuid.UUID(hid(typ + NAME, 32)))}})
dump(os.path.join(ROOT, f"{NAME}.pbip"), {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
    "version": "1.0", "artifacts": [{"report": {"path": f"{NAME}.Report"}}], "settings": {"enableAutoRecovery": True}})
print(f"ok · {sum(len(p.visuals) for p in PAGES)} visuales")
