"""Genera el informe PBIR de Brujula SLA (página 1: Cumplimiento de objetivos; página 2: Evolución del cumplimiento)."""
import hashlib, json, os, re, shutil, sys, uuid

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

def color_t(color_id, percent=0):  # color del tema (como lo elige Desktop: ColorId 0 = blanco, percent < 0 lo oscurece)
    return {"solid": {"color": {"expr": {"ThemeDataColor": {"ColorId": color_id, "Percent": percent}}}}}

GRIS_BORDE = color_t(0, -0.2)  # borde gris claro de las tarjetas (elegido en Desktop el 2026-11-09)

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

def vco_basic(bg=None, border=False, padding=0, title=None, title_size=10, radius=None):
    # border: False, True, un color "#RRGGBB" o un color ya construido (dict); con color, borde visible de 1 px
    b = props(show=lit(bool(border)))
    if isinstance(border, (str, dict)):
        b["properties"].update(color=color(border) if isinstance(border, str) else border, width=num(1))
    if radius:  # redondea el contenedor (fondo incluido); con borde visible las esquinas se distinguen mejor
        b["properties"]["radius"] = num(radius)
    v = {
        "padding": [props(top=num(padding), bottom=num(padding), left=num(padding), right=num(padding))],
        "border": [b],
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
        self.interactions = []   # [(visual origen, visual destino, tipo)] → visualInteractions de page.json
        self.background = None   # objeto background de page.json; None = blanco
        self.z = 0

    def vid(self, vname):
        return hid(f"{self.key}/{vname}")

    def override(self, vname, position=None, objects=None, formats=None, vco=None):
        """Ajustes hechos a mano en Desktop que el generador debe conservar: posición/tamaño, objetos de formato
        y del contenedor (se sustituyen enteros, tal como los guardó Desktop) y formato de un campo ({queryRef: formato})."""
        vid = self.vid(vname)
        v = next(x for x in self.visuals if x["name"] == vid)
        if position:
            v["position"].update(position)
        for role in v["visual"].get("query", {}).get("queryState", {}).values():
            for p in role["projections"]:
                if formats and p["queryRef"] in formats:
                    p["format"] = formats[p["queryRef"]]
        for name, value in (objects or {}).items():
            v["visual"]["objects"][name] = value
        for name, value in (vco or {}).items():
            v["visual"]["visualContainerObjects"][name] = value

    def remove(self, *vnames):
        """Quita objetos que el usuario borró en Desktop (para que no vuelvan a aparecer al regenerar)."""
        ids = {self.vid(n) for n in vnames}
        self.visuals = [v for v in self.visuals if v["name"] not in ids]

    def add_desktop(self, from_key=None):
        """Incluye tal cual los objetos creados a mano en Desktop, guardados en _generadores/visuales_desktop/<página>/.
        Con from_key se copian los de otra página (con nombre nuevo, para que no choquen)."""
        carpeta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "visuales_desktop", from_key or self.key)
        for fn in sorted(os.listdir(carpeta)):
            with open(os.path.join(carpeta, fn), encoding="utf-8") as fh:
                v = json.load(fh)
            if from_key:
                v["name"] = hid(f"{self.key}/desktop/{v['name']}")
            self.visuals.append(v)

    def no_filter(self, source, targets):
        """El visual origen (p. ej. un segmentador) no filtra a los destinos."""
        self.interactions += [(self.vid(source), self.vid(t), "NoFilter") for t in targets]

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
def shape(fill, radius=12, text=None, font=11, font_color="#FFFFFF", tile="rectangleRounded", outline=None):
    """outline: color (dict) para un contorno de 1 px; None = sin contorno."""
    objects = {
        "shape": [sel_default(props(tileShape=lit(tile), rectangleRoundedCurve=lit(radius)))],
        "fill": [sel_default(props(show=lit(True), fillColor=color(fill), transparency=num(0)))],
        "outline": [sel_default(props(show=lit(True), lineColor=outline, weight=num(1)) if outline
                                else props(show=lit(False)))],
    }
    if text:
        objects["text"] = [sel_default(props(show=lit(True), text=lit(text), fontSize=num(font), bold=lit(True),
                                             fontColor=color(font_color), horizontalAlignment=lit("center"),
                                             verticalAlignment=lit("middle")))]
    return {"visualType": "shape", "objects": objects,
            "visualContainerObjects": vco_basic(bg=None, border=False, padding=0)}

def textbox(text, size=12, bold=True, color_hex="#1B1F24", bg=None, radius=None, center=False, padding=0):
    """bg/radius: fondo fijo del contenedor con esquinas redondeadas (se pinta bien, a diferencia del texto de un shape).
    Con radio, el borde se activa del mismo color que el fondo para que el redondeo se dibuje."""
    para = {"textRuns": [{"value": text, "textStyle": {"fontWeight": "bold" if bold else "normal",
                                                       "fontSize": f"{size}pt", "color": color_hex}}]}
    if center:
        para["horizontalTextAlignment"] = "center"
    return {"visualType": "textbox", "objects": {"general": [props(paragraphs=[para])]},
            "visualContainerObjects": vco_basic(bg=bg, border=bg if (bg and radius) else False, padding=padding,
                                                radius=radius)}

def card(entity, measure, *, label_text=None, label_pos="aboveValue", value_size=28, value_color="#1B1F24",
         value_color_measure=None, label_size=10, label_color="#605E5C", fill_measure=None, align="left",
         bg="#FFFFFF", border=False, title=None, padding=8, display=None, show_label=True, value_color_fill=None,
         pill=None, radius=None, valign=None):
    value = props(fontSize=num(value_size), bold=lit(True), horizontalAlignment=lit(align),
                  fontColor=value_color_fill or (color_m(*value_color_measure) if value_color_measure else color(value_color)))
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
    if pill:  # (relleno, borde, radio en px); relleno y borde: (entidad, medida) o "#RRGGBB" fijo.
        fondo, borde, radio = pill  # Serializado como lo guarda Desktop: la forma necesita el selector default
        col = lambda c: color(c) if isinstance(c, str) else color_m(*c)
        objects["fillCustom"] = [sel_default(props(show=lit(True), fillColor=col(fondo), transparency=num(0)))]
        objects["outline"] = [sel_default(props(show=lit(True), lineColor=col(borde), weight=num(1)))]
        objects["shapeCustomRectangle"] = [sel_default(props(tileShape=lit("rectangleRoundedByPixel"),
                                                             rectangleRoundedCurve=lit(radio)))]
        # Texto centrado en vertical: alineación 'middle' y sin el margen interior por defecto de la tarjeta
        # (desigual, empuja el texto hacia abajo). Mismo formato que guarda Desktop.
        objects["layout"].append(props(alignment=lit("middle"), cellPadding=lit(0)))
        objects["padding"] = [sel_default(props(paddingSelection=lit("Custom"), topMargin=lit(0), bottomMargin=lit(0),
                                                leftMargin=lit(0), rightMargin=lit(0)))]
    if valign and not pill:
        # Texto anclado arriba / al centro / abajo y sin el margen interior por defecto: dos tarjetas con la misma
        # posición, altura y valign="bottom" apoyan su texto en la misma línea base aunque tengan distinto tamaño
        objects["layout"].append(props(alignment=lit(valign), cellPadding=lit(0)))
        objects["padding"] = [sel_default(props(paddingSelection=lit("Custom"), topMargin=lit(0), bottomMargin=lit(0),
                                                leftMargin=lit(0), rightMargin=lit(0)))]
    if fill_measure:
        objects["fillCustom"] = [sel_default(props(show=lit(True), fillColor=color_m(*fill_measure), transparency=num(0)))]
        objects["shapeCustomRectangle"] = [props(tileShape=lit("rectangleRounded"), rectangleRoundedCurve=lit(18))]
    return {"visualType": "cardVisual",
            "query": {"queryState": {"Data": {"projections": [proj(m_expr(entity, measure), entity, measure, display)]}}},
            "objects": objects,
            "visualContainerObjects": vco_basic(bg=bg, border=border, padding=padding, title=title, title_size=9,
                                                radius=radius)}

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

def line_chart(category, series, *, y_max=None, title=None, subtitle=None, boxed_labels=False):
    """Gráfico de líneas: category = (entidad, columna) en el eje X; series = [(entidad, medida, nombre, color)].

    boxed_labels=True aplica el estilo de referencia: etiquetas en cajas del color de su serie con texto blanco,
    leyenda con círculos arriba a la izquierda, líneas finas y cuadrícula punteada suave."""
    cat_ent, cat_col = category
    objects = {
        "labels": [sel_default(props(show=lit(True), fontSize=num(9), labelPosition=lit("Above")))],
        "legend": [props(show=lit(True), position=lit("Top"), fontSize=num(10))],
        "categoryAxis": [props(show=lit(True), axisType=lit("Categorical"), showAxisTitle=lit(True),
                               titleText=lit("Sprint"), fontSize=num(9))],
        "valueAxis": [props(show=lit(True), start=num(0), showAxisTitle=lit(True), titleText=lit("Nº de KPI"),
                            gridlineShow=lit(True), fontSize=num(9))],
        "lineStyles": [sel_default(props(strokeWidth=lit(3), showMarker=lit(True), markerSize=num(5)))],
        "dataPoint": [{"properties": {"fill": color(c)}, "selector": {"metadata": f"{e}.{m}"}} for e, m, _, c in series],
    }
    if boxed_labels:
        objects["labels"] = [sel_default(props(show=lit(True), fontSize=num(9), bold=lit(True), labelPosition=lit("Above"),
                                               color=color("#FFFFFF"), enableBackground=lit(True),
                                               backgroundColor=color("#605E5C"), backgroundTransparency=num(0)))]
        objects["labels"] += [{"properties": {"backgroundColor": color(c), "color": color("#FFFFFF")},
                               "selector": {"metadata": f"{e}.{m}"}} for e, m, _, c in series]
        objects["legend"] = [props(show=lit(True), position=lit("Top"), fontSize=num(9), showTitle=lit(False),
                                   legendMarkerRendering=lit("markerCircleDefault"))]
        objects["categoryAxis"] = [props(show=lit(True), axisType=lit("Categorical"), showAxisTitle=lit(False),
                                         fontSize=num(9), bold=lit(True), gridlineShow=lit(False))]
        objects["valueAxis"] = [props(show=lit(True), start=num(0), showAxisTitle=lit(False), fontSize=num(9), bold=lit(True),
                                      gridlineShow=lit(True), gridlineStyle=lit("dotted"), gridlineColor=color("#C8C6C4"))]
        objects["lineStyles"] = [sel_default(props(strokeWidth=lit(2), showMarker=lit(True), markerShape=lit("circle"),
                                                   markerSize=num(4)))]
    if y_max is not None:
        objects["valueAxis"][0]["properties"]["end"] = num(y_max)
    vco = vco_basic(bg="#FFFFFF", border=False, padding=16, title=title, title_size=12 if not boxed_labels else 14)
    if subtitle:
        vco["subTitle"] = [props(show=lit(True), text=lit(subtitle), fontSize=num(10), fontColor=color("#605E5C"))]
        vco["divider"] = [props(show=lit(True), color=color("#605E5C"), width=num(1), style=lit("solid"))]
    return {"visualType": "lineChart",
            "query": {"queryState": {
                          "Category": {"projections": [proj(c_expr(cat_ent, cat_col), cat_ent, cat_col)]},
                          "Y": {"projections": [proj(m_expr(e, m), e, m, name) for e, m, name, _ in series]}},
                      "sortDefinition": {"sort": [{"field": c_expr(cat_ent, cat_col), "direction": "Ascending"}],
                                         "isDefaultSort": True}},
            "objects": objects,
            "visualContainerObjects": vco}

def f_sprint_no_blank(page, vname):
    """Excluye los días del calendario sin sprint asignado, que saldrían como «(En blanco)» en el eje X."""
    return {
        "name": "Filter" + hid(f"{page}/{vname}/sin_blanco", 24),
        "field": c_expr("Sprint", "Sprint"),
        "type": "Categorical",
        "filter": {
            "Version": 2,
            "From": [{"Name": "s", "Entity": "Sprint", "Type": 0}],
            "Where": [{"Condition": {"Not": {"Expression": {"In": {
                "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "s"}}, "Property": "Sprint"}}],
                "Values": [[{"Literal": {"Value": "null"}}]]}}}}}],
        },
        "howCreated": "User",
        "isHiddenInViewMode": True,
    }

def table_visual(columns, *, header_bg="#1F5C99", title=None, sort=None, widths=None):
    """Tabla con cabecera de color y texto blanco, filas alternas y fila Total.
    columns = [("col"|"measure", entidad, propiedad, nombre visible)];
    sort = ("col"|"measure", entidad, propiedad, "Ascending"|"Descending") (por defecto, la 1ª columna ascendente);
    widths = {"entidad.propiedad": px}."""
    projs = [proj((c_expr if kind == "col" else m_expr)(e, p), e, p, name) for kind, e, p, name in columns]
    objects = {
        "columnHeaders": [props(columnAdjustment=lit("growToFit"), autoSizeColumnWidth=lit(True),
                                fontColor=color("#FFFFFF"), backColor=color(header_bg), bold=lit(True), fontSize=num(11))],
        "values": [props(backColorPrimary=color("#FFFFFF"), backColorSecondary=color("#F3F6FA"),
                         fontColorPrimary=color("#1B1F24"), fontColorSecondary=color("#1B1F24"), fontSize=num(11))],
        "total": [props(totals=lit(True), bold=lit(True), fontSize=num(11))],
        "grid": [props(gridHorizontal=lit(True), gridVertical=lit(True), gridHorizontalColor=color("#D0D7E2"),
                       gridVerticalColor=color("#D0D7E2"))],
    }
    if widths:
        objects["columnWidth"] = [{"properties": {"value": num(px)}, "selector": {"metadata": key}}
                                  for key, px in widths.items()]
    if sort:
        kind, e, p, direction = sort
        sort_def = {"sort": [{"field": (c_expr if kind == "col" else m_expr)(e, p), "direction": direction}]}
    else:
        first = columns[0]
        sort_def = {"sort": [{"field": (c_expr if first[0] == "col" else m_expr)(first[1], first[2]),
                              "direction": "Ascending"}], "isDefaultSort": True}
    return {"visualType": "tableEx",
            "query": {"queryState": {"Values": {"projections": projs}},
                      "sortDefinition": sort_def},
            "objects": objects,
            "visualContainerObjects": vco_basic(bg="#FFFFFF", border=False, padding=12, title=title, title_size=12)}

def matrix_visual(rows, values, *, expanded=None, font_color_measure=None, header_bg="#1F5C99", title=None, sort=None,
                  icon_measure=None):
    """Matriz con el mismo estilo que table_visual (con varios niveles de filas, subtotales por grupo).
    rows / values = [(entidad, columna|medida, nombre visible)]; expanded = valores del 1er nivel que se muestran
    desplegados; font_color_measure = ((entidad, medida coloreada), (entidad, medida con el color hex));
    sort = (entidad, medida, "Ascending"|"Descending")."""
    row_projs = [proj(c_expr(e, c), e, c, name) for e, c, name in rows]
    val_projs = [proj(m_expr(e, m), e, m, name) for e, m, name in values]
    values_obj = [props(backColorPrimary=color("#FFFFFF"), backColorSecondary=color("#F3F6FA"),
                        fontColorPrimary=color("#1B1F24"), fontColorSecondary=color("#1B1F24"), fontSize=num(11))]
    if font_color_measure:
        (te, tm), (ce, cm) = font_color_measure
        values_obj.append({"properties": {"fontColor": color_m(ce, cm)},
                           "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": f"{te}.{tm}"}})
    if icon_measure:
        # ✓ verde si la medida de condición vale 1, ✗ rojo si vale 0 (sin icono si está vacía)
        (te, tm), (ce, cm) = icon_measure
        caso = lambda v, icono: {"Condition": {"Comparison": {"ComparisonKind": 0, "Left": m_expr(ce, cm),
                                                               "Right": {"Literal": {"Value": f"{v}L"}}}},
                                 "Value": {"Literal": {"Value": f"'{icono}'"}}}
        values_obj.append({"properties": {"icon": {
                               "kind": "Icon", "layout": lit("Before"), "verticalAlignment": lit("Middle"),
                               "value": {"expr": {"Conditional": {"Cases": [caso(1, "SymbolHigh"), caso(0, "SymbolLow")]}}}}},
                           "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": f"{te}.{tm}"}})
    objects = {
        "columnHeaders": [props(columnAdjustment=lit("growToFit"), autoSizeColumnWidth=lit(True),
                                fontColor=color("#FFFFFF"), backColor=color(header_bg), bold=lit(True), fontSize=num(11))],
        "rowHeaders": [props(fontSize=num(11), fontColor=color("#1B1F24"))],
        "values": values_obj,
        "subTotals": [props(fontColor=color("#1B1F24"), backColor=color("#E6EEF7"), bold=lit(True))],
        "grid": [props(gridHorizontal=lit(True), gridVertical=lit(True), gridHorizontalColor=color("#D0D7E2"),
                       gridVerticalColor=color("#D0D7E2"))],
    }
    v = {"visualType": "pivotTable",
         "query": {"queryState": {"Rows": {"projections": row_projs}, "Values": {"projections": val_projs}}},
         "objects": objects,
         "visualContainerObjects": vco_basic(bg="#FFFFFF", border=False, padding=12, title=title, title_size=12)}
    if sort:
        se, sm, direction = sort
        v["query"]["sortDefinition"] = {"sort": [{"field": m_expr(se, sm), "direction": direction}]}
    if expanded:
        e0, c0, _ = rows[0]
        v["expansionStates"] = [{
            "roles": ["Rows"],
            "levels": [{"queryRefs": [f"{e0}.{c0}"], "isCollapsed": True, "identityKeys": [c_expr(e0, c0)],
                        "isPinned": True}],
            "root": {"children": [{"identityValues": [{"Literal": {"Value": f"'{x}'"}}], "isToggled": True}
                                  for x in expanded]},
        }]
    return v

def heatmap_matrix(rows, column, value, color_measure, *, sort=None, header_bg="#F3F5F8", totals=False, wrap=False,
                   align=None):
    """Matriz tipo mapa de calor: filas en forma de tabla (sin escalonar, desplegadas y sin subtotales), una columna
    por valor de `column` y el fondo de cada celda según `color_measure`. Las líneas blancas gruesas de la cuadrícula
    separan las celdas como bloques. rows = [(entidad, columna, nombre)]; column = (entidad, columna);
    value = (entidad, medida, nombre); color_measure = (entidad, medida con el color hex)."""
    ce, cc = column
    ve, vm, vname = value
    objects = {
        "columnHeaders": [props(fontColor=color("#3B4048"), backColor=color(header_bg), bold=lit(True), fontSize=num(10),
                                alignment=lit("Center"))],
        "rowHeaders": [props(fontSize=num(10), fontColor=color("#1B1F24"), stepped=lit(False), autoExpand=lit(True),
                             showExpandCollapseButtons=lit(False), wordWrap=lit(False))],
        "values": [props(fontSize=num(10), fontColor=color("#1B1F24"), backColorPrimary=color("#FFFFFF"),
                         backColorSecondary=color("#FFFFFF")),
                   {"properties": {"backColor": color_m(*color_measure)},
                    "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": f"{ve}.{vm}"}}],
        "subTotals": [props(rowSubtotals=lit(totals), columnSubtotals=lit(totals))],
        "grid": [props(gridHorizontal=lit(True), gridVertical=lit(True), gridHorizontalColor=color("#FFFFFF"),
                       gridVerticalColor=color("#FFFFFF"), gridHorizontalWeight=num(4), gridVerticalWeight=num(4),
                       rowPadding=num(6))],
    }
    if totals:   # totales en negrita sobre gris claro
        objects["subTotals"][0]["properties"].update(bold=lit(True), backColor=color("#F3F5F8"))
    if wrap:     # celdas de texto con varias líneas (UNICHAR(10) en la medida)
        objects["values"][0]["properties"]["wordWrap"] = lit(True)
    if align:
        objects["columnFormatting"] = [{"properties": {"alignment": lit(align)}, "selector": {"metadata": f"{ve}.{vm}"}}]
    v = {"visualType": "pivotTable",
         "query": {"queryState": {"Rows": {"projections": [proj(c_expr(e, c), e, c, name) for e, c, name in rows]},
                                  "Columns": {"projections": [proj(c_expr(ce, cc), ce, cc)]},
                                  "Values": {"projections": [proj(m_expr(ve, vm), ve, vm, vname)]}}},
         "objects": objects,
         "visualContainerObjects": vco_basic(bg="#FFFFFF", border=False, padding=12)}
    if sort:
        se, sm, direction = sort
        v["query"]["sortDefinition"] = {"sort": [{"field": m_expr(se, sm), "direction": direction}]}
    return v

def f_medida(page, vname, entity, measure, valor, kind=0):
    """Filtro de visual sobre una medida: solo las combinaciones donde la medida cumple la comparación con `valor`
    (kind: 0 igual, 1 mayor que, 2 mayor o igual, 3 menor que, 4 menor o igual)."""
    return {
        "name": "Filter" + hid(f"{page}/{vname}/{measure}", 24),
        "field": m_expr(entity, measure),
        "type": "Advanced",
        "filter": {
            "Version": 2,
            "From": [{"Name": "m", "Entity": entity, "Type": 0}],
            "Where": [{"Condition": {"Comparison": {"ComparisonKind": kind,
                "Left": {"Measure": {"Expression": {"SourceRef": {"Source": "m"}}, "Property": measure}},
                "Right": {"Literal": {"Value": f"{valor}L" if isinstance(valor, int) else f"{valor}D"}}}}}],
        },
        "howCreated": "User",
        "isHiddenInViewMode": True,
    }

def diverging_columns(category, up, down, *, title_measure=None):
    """Columnas apiladas en dos sentidos: `up` hacia arriba y `down` (una medida en negativo) hacia abajo, con una línea
    discontinua en el cero. category = (entidad, columna); up / down = (entidad, medida, nombre en la leyenda, color);
    title_measure = (entidad, medida) cuyo texto es el título del gráfico."""
    ce, cc = category
    series = [up, down]
    objects = {
        "dataPoint": [{"properties": {"fill": color(c)}, "selector": {"metadata": f"{e}.{m}"}} for e, m, _, c in series],
        "legend": [props(show=lit(True), position=lit("TopRight"), fontSize=num(9), showTitle=lit(False))],
        "categoryAxis": [props(show=lit(True), showAxisTitle=lit(False), fontSize=num(9), bold=lit(True),
                               gridlineShow=lit(False))],
        "valueAxis": [props(show=lit(False), showAxisTitle=lit(False), gridlineShow=lit(False))],
        "labels": [sel_default(props(show=lit(False)))],
        "y1AxisReferenceLine": [{"properties": {"show": lit(True), "value": num(0), "style": lit("dashed"),
                                                "lineColor": color("#9AA3AD"), "width": num(1), "position": lit("front")},
                                 "selector": {"id": "1"}}],
    }
    vco = vco_basic(bg="#FFFFFF", border=True, padding=16)
    if title_measure:
        vco["title"] = [props(show=lit(True), text={"expr": m_expr(*title_measure)}, fontSize=num(12), bold=lit(True),
                              fontColor=color("#1B1F24"))]
    return {"visualType": "columnChart",
            "query": {"queryState": {
                          "Category": {"projections": [proj(c_expr(ce, cc), ce, cc)]},
                          "Y": {"projections": [proj(m_expr(e, m), e, m, name) for e, m, name, _ in series]}},
                      "sortDefinition": {"sort": [{"field": c_expr(ce, cc), "direction": "Ascending"}],
                                         "isDefaultSort": True}},
            "objects": objects,
            "visualContainerObjects": vco}

def pareto_bars(category, measure, color_measure, detail_measure, *, title_measure=None, subtitle=None):
    """Barras horizontales de mayor a menor, con el color de cada barra según `color_measure`, la cifra al final de la
    barra y una etiqueta de detalle (`detail_measure`, p. ej. el % acumulado) a su lado.
    category = (entidad, columna); el resto, (entidad, medida)."""
    ce, cc = category
    me, mm = measure
    objects = {
        "dataPoint": [{"properties": {"fill": {"solid": {"color": {"expr": m_expr(*color_measure)}}}},
                       "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}}],
        "legend": [props(show=lit(False))],
        "categoryAxis": [props(show=lit(True), showAxisTitle=lit(False), fontSize=num(10), gridlineShow=lit(False))],
        "valueAxis": [props(show=lit(False), showAxisTitle=lit(False), gridlineShow=lit(False))],
        "labels": [sel_default(props(show=lit(True), labelPosition=lit("OutsideEnd"), fontSize=num(10), bold=lit(True),
                                     color=color("#1B1F24"), enableDetailDataLabel=lit(True),
                                     detailColor=color("#605E5C"), labelContentLayout=lit("SingleLine"))),
                   {"properties": {"dynamicLabelDetail": {"expr": m_expr(*detail_measure)}},
                    "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}}],
    }
    vco = vco_basic(bg="#FFFFFF", border=True, padding=16)
    if title_measure:
        vco["title"] = [props(show=lit(True), text={"expr": m_expr(*title_measure)}, fontSize=num(12), bold=lit(True),
                              fontColor=color("#1B1F24"))]
    if subtitle:
        vco["subTitle"] = [props(show=lit(True), text=lit(subtitle), fontSize=num(9), fontColor=color("#605E5C"))]
    return {"visualType": "barChart",
            "query": {"queryState": {
                          "Category": {"projections": [proj(c_expr(ce, cc), ce, cc)]},
                          "Y": {"projections": [proj(m_expr(me, mm), me, mm)]}},
                      "sortDefinition": {"sort": [{"field": m_expr(me, mm), "direction": "Descending"}]}},
            "objects": objects,
            "visualContainerObjects": vco}

def stacked_bar(category, series, *, title=None, subtitle=None):
    """Barras horizontales apiladas: category = (entidad, columna) en el eje Y; series = [(entidad, medida, nombre, color)]."""
    cat_ent, cat_col = category
    objects = {
        "labels": [sel_default(props(show=lit(True), fontSize=num(11), bold=lit(True), color=color("#FFFFFF")))],
        "legend": [props(show=lit(True), position=lit("Top"), fontSize=num(10), showTitle=lit(False))],
        "categoryAxis": [props(show=lit(True), showAxisTitle=lit(False), fontSize=num(11), bold=lit(True))],
        "valueAxis": [props(show=lit(True), start=num(0), showAxisTitle=lit(True), titleText=lit("Nº de KPI"),
                            fontSize=num(9), gridlineShow=lit(True), gridlineStyle=lit("dotted"),
                            gridlineColor=color("#C8C6C4"))],
        "dataPoint": [{"properties": {"fill": color(c)}, "selector": {"metadata": f"{e}.{m}"}} for e, m, _, c in series],
    }
    vco = vco_basic(bg="#FFFFFF", border=False, padding=16, title=title, title_size=14)
    if subtitle:
        vco["subTitle"] = [props(show=lit(True), text=lit(subtitle), fontSize=num(10), fontColor=color("#605E5C"))]
        vco["divider"] = [props(show=lit(True), color=color("#605E5C"), width=num(1), style=lit("solid"))]
    return {"visualType": "barChart",
            "query": {"queryState": {
                          "Category": {"projections": [proj(c_expr(cat_ent, cat_col), cat_ent, cat_col)]},
                          "Y": {"projections": [proj(m_expr(e, m), e, m, name) for e, m, name, _ in series]}},
                      "sortDefinition": {"sort": [{"field": c_expr(cat_ent, cat_col), "direction": "Ascending"}],
                                         "isDefaultSort": True}},
            "objects": objects,
            "visualContainerObjects": vco}

def progress_bar(category, series):
    """Barra 100 % apilada sin ejes, leyenda, etiquetas ni rejilla. category = (entidad, columna), obligatoria en este
    visual: usar una con un único valor en contexto para que salga una sola barra. series = [(entidad, medida, nombre, color)]."""
    cat_ent, cat_col = category
    objects = {
        "legend": [props(show=lit(False))],
        "categoryAxis": [props(show=lit(False), gridlineShow=lit(False))],
        "valueAxis": [props(show=lit(False), gridlineShow=lit(False))],
        "labels": [props(show=lit(False))],
        "dataPoint": [{"properties": {"fill": color(c)}, "selector": {"metadata": f"{e}.{m}"}} for e, m, _, c in series],
    }
    return {"visualType": "hundredPercentStackedBarChart",
            "query": {"queryState": {
                "Category": {"projections": [proj(c_expr(cat_ent, cat_col), cat_ent, cat_col)]},
                "Y": {"projections": [proj(m_expr(e, m), e, m, name) for e, m, name, _ in series]}}},
            "objects": objects,
            "visualContainerObjects": vco_basic(bg=None, border=False, padding=0)}

def f_valores(page, vname, entity, column, valores):
    """Filtro de visual: la columna solo puede tomar estos valores."""
    return {
        "name": "Filter" + hid(f"{page}/{vname}/{column}", 24),
        "field": c_expr(entity, column),
        "type": "Categorical",
        "filter": {
            "Version": 2,
            "From": [{"Name": "f", "Entity": entity, "Type": 0}],
            "Where": [{"Condition": {"In": {
                "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "f"}}, "Property": column}}],
                "Values": [[{"Literal": {"Value": f"'{v}'"}}] for v in valores]}}}],
        },
        "howCreated": "User",
        "isHiddenInViewMode": True,
    }

def f_bloque(page, vname, bloque):
    """Limita los recuentos KPI Cumplido / Incumplido a los KPI de un bloque de Objetivos KPI."""
    return {
        "name": "Filter" + hid(f"{page}/{vname}/bloque", 24),
        "field": c_expr("Objetivos KPI", "Bloque"),
        "type": "Categorical",
        "filter": {
            "Version": 2,
            "From": [{"Name": "o", "Entity": "Objetivos KPI", "Type": 0}],
            "Where": [{"Condition": {"In": {
                "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "o"}}, "Property": "Bloque"}}],
                "Values": [[{"Literal": {"Value": f"'{bloque}'"}}]]}}}],
        },
        "howCreated": "User",
        "isHiddenInViewMode": True,
    }

# ---------- panel de filtros (común a las páginas) ----------
def rail(page, sprint_kw):
    """Panel izquierdo con los mismos segmentadores en todas las páginas; solo cambia el de Sprint."""
    page.add("rail_bg", 16, 16, 248, 1048, shape("#DDE2E8", radius=10))
    page.add("rail_title", 32, 24, 216, 32, textbox("Filtros", 13, True, "#1B1F24"))
    slicers = [
        ("s_anio", "Sprint", "Año", "Año", dict(sync="anio")),
        ("s_sprint", "Sprint", "Sprint", "Sprint", sprint_kw),
        ("s_nivel", "Cliente", "Nivel de contrato", "Nivel de contrato", {}),
        ("s_cliente", "Cliente", "Cliente", "Cliente", {}),
        ("s_dep", "Departamento", "Departamento", "Departamento", {}),
        ("s_tipo", "Política SLA", "Tipo", "Tipo de ticket", {}),
        ("s_prio", "Política SLA", "Prioridad", "Prioridad", {}),
    ]
    for i, (vn, ent, colname, header, kw) in enumerate(slicers):
        page.add(vn, 28, 64 + i * 92, 224, 80, slicer(ent, colname, header, **kw))
    page.add("rail_note", 28, 720, 224, 120, textbox(
        "Los KPI de negocio (8–11) se calculan por cliente: no cambian con Departamento, Tipo ni Prioridad.",
        9, False, "#3B4048"))

# ---------- página 1: cumplimiento de objetivos ----------
OK = "Objetivos KPI"
p1 = Page("objetivos", "Cumplimiento de objetivos")
rail(p1, dict(single=True, default="2025-17", sync="sprint"))
# Ajuste hecho en Desktop el 2026-11-10 (copiado tal cual): fondo del panel de filtros pegado a la esquina
p1.override("rail_bg", position={"x": 0, "y": 0})
# Ajuste hecho en Desktop el 2026-11-09 (copiado tal cual): panel de filtros con el color 0 del tema (blanco)
p1.override("rail_bg", objects={
    "fill": [sel_default(props(show=lit(True), fillColor={"solid": {"color": {"expr": {"ThemeDataColor": {"ColorId": 0, "Percent": 0}}}}},
                               transparency=num(0))), props(show=lit(True))],
    "outline": [sel_default(props(show=lit(False))), props(show=lit(False))],
    # 18:10: forma con una segunda entrada de radio 8 (sin selector), tal cual la guardó Desktop
    "shape": [sel_default(props(tileShape=lit("rectangleRounded"), rectangleRoundedCurve=lit(10))),
              props(tileShape=lit("rectangleRounded"), rectangleRoundedCurve=lit(8))]},
    vco={"border": [props(show=lit(True), color=GRIS_BORDE)]})  # 18:10: borde gris claro
# Ajuste hecho en Desktop el 2026-11-09: fondo de esta página gris muy claro (blanco −10 % al 52 % de transparencia)
p1.background = [props(color=color_t(0, -0.1), transparency={"expr": {"Literal": {"Value": "52D"}}})]

# Cabecera: antetítulo gris en mayúsculas (se añade al final de la página para no mover el orden de capas),
# título en minúsculas y el periodo en una caja blanca redondeada
p1.add("title", 288, 36, 1000, 40, textbox("Cumplimiento de los objetivos", 20, True, "#1B1F24"))
p1.add("periodo", 1564, 14, 340, 62, card("Sprint", "Periodo seleccionado", label_text="Periodo analizado",
       value_size=14, label_size=9, align="right", bg="#FFFFFF", border=GRIS_BORDE, radius=10, padding=10),
       alt="Sprint seleccionado")

# Resumen: una tarjeta con «N de total», la comparación con el sprint anterior y una barra cumplidos / incumplidos
p1.add("sum_bg", 288, 88, 1616, 96, shape("#FFFFFF", radius=12, outline=GRIS_BORDE))
# Esquinas ligeramente redondeadas: Desktop solo pinta el radio de la entrada sin selector (como en el panel de filtros)
p1.override("sum_bg", objects={"shape": [sel_default(props(tileShape=lit("rectangleRounded"), rectangleRoundedCurve=lit(10))),
                                         props(tileShape=lit("rectangleRounded"), rectangleRoundedCurve=lit(10))]})
# Tres filas dentro de la caja (88–184): título 92–110 · número 108–152 · sprint anterior 156–176 (8 px de aire abajo).
# «2» y «de 15» comparten caja vertical y van anclados abajo: así apoyan en la misma línea base.
p1.add("sum_titulo", 308, 92, 300, 18, textbox("Objetivos cumplidos", 10, True, "#3B4048"))
p1.add("sum_num", 308, 108, 44, 44, card(OK, "KPI Cumplido", show_label=False, value_size=30, bg=None, padding=0,
       valign="bottom"), alt="Número de KPI cumplidos en el sprint seleccionado")
p1.add("sum_total", 354, 108, 120, 44, card(OK, "Texto total objetivos", show_label=False, value_size=14,
       value_color="#3B4048", bg=None, padding=0, valign="bottom"), alt="Número de KPI con datos")
p1.add("sum_prev", 308, 156, 480, 20, card(OK, "Texto sprint anterior objetivos", show_label=False, value_size=9,
       value_color="#3B4048", bg=None, padding=0, valign="middle"), alt="KPI cumplidos en el sprint anterior y tendencia")
# Solo cumplidos e incumplidos (los KPI sin datos no cuentan). Sprint es de selección única aquí: una sola barra
p1.add("sum_barra", 820, 104, 1060, 30, progress_bar(("Sprint", "Sprint"),
    [(OK, "KPI Cumplido", "Cumplidos", "#1E7B5C"), (OK, "KPI Incumplido", "Incumplidos", "#C0392B")]),
    alt="Barra: proporción de KPI cumplidos (verde) e incumplidos (rojo)")
for i, (medida, fondo, borde, letra) in enumerate([("Texto leyenda cumplidos", "#E3F2EA", "#9CCFB5", "#1E6B4A"),
                                                    ("Texto leyenda incumplidos", "#FBE4E2", "#E8A39C", "#A93226")]):
    p1.add(f"sum_ley_{i}", 820 + i * 172, 142, 160, 30, card(OK, medida, show_label=False, value_size=10,
           value_color=letra, align="center", bg=None, padding=0, pill=(fondo, borde, 15)),
           alt=medida.replace("Texto leyenda ", "Leyenda: KPI "))

# Bloques de KPI
BLOQUES = [
    ("KPI TICKETS", [(1, "Ritmo de cierre"), (2, "Backlog al cierre"), (3, "Resolución en primer nivel"), (4, "% Escalados")]),
    ("SLA", [(5, "SLA 1ª respuesta"), (6, "SLA resolución"), (7, "SLA de los P1")]),
    ("NEGOCIO", [(8, "Balance medio por sprint"), (9, "Penalización sobre la cuota"),
                 (10, "Clientes en tramo deficiente"), (11, "Ingresos en riesgo")]),
    ("OPERACIÓN", [(12, "MTTR (horas de SLA)"), (13, "1ª respuesta media"), (14, "Tickets por agente y día"),
                   (15, "% Agentes ausentes")]),
]
# KPI que penalizan en la factura (Ficha §0.3): su caja lleva borde azul oscuro y la etiqueta «€ Penaliza en factura»
PENALIZA = {6}
AZUL_PENALIZA = "#1F3A5F"
y = 200
for bname, kpis in BLOQUES:
    p1.add(f"blk_{bname}", 288, y, 600, 32, textbox(bname, 14, True, "#1B1F24"))
    cy = y + 36
    for j, (kid, kname) in enumerate(kpis):
        x = 288 + j * 404
        f = lambda vn: [filter_id(p1.key, vn, kid)]
        vn = f"kpi_{kid}"
        penaliza = kid in PENALIZA
        p1.add(vn, x, cy, 380, 150, card(OK, "Valor KPI", label_text=kname, value_size=30, label_size=11,
               title=f"KPI {kid}", padding=12, display=kname, bg="#FFFFFF",
               border=AZUL_PENALIZA if penaliza else GRIS_BORDE, radius=12), filters=f(vn),
               alt=f"KPI {kid}: {kname} del sprint seleccionado" + (" (penaliza en la factura)" if penaliza else ""))
        if penaliza:  # abajo a la izquierda: entre el rótulo y el valor no cabe sin desalinear el valor con sus vecinas
            p1.add(f"kpi_{kid}_pen", x + 12, cy + 114, 140, 24,
                   textbox("€ Penaliza en factura", 9, True, "#FFFFFF", bg=AZUL_PENALIZA, radius=8, center=True, padding=3),
                   alt="Este KPI penaliza en la factura")
        if penaliza:  # ajustes que estaban en el proyecto el 2026-11-10 (copiados tal cual): margen inferior 20 de la
            # caja y etiqueta 6 px más abajo y 1 px más alta
            p1.override(vn, vco={"padding": [props(top=num(12), bottom={"expr": {"Literal": {"Value": "20D"}}},
                                                   left=num(12), right=num(12))]})
            p1.override(f"kpi_{kid}_pen", position={"y": cy + 120, "height": 25})
        vn = f"kpi_{kid}_estado"
        p1.add(vn, x + 236, cy + 12, 132, 40, card(OK, "Texto estado", show_label=False, value_size=11,
               value_color_measure=(OK, "Color texto estado"),
               pill=((OK, "Color estado"), (OK, "Color borde estado"), 25),
               align="center", bg=None, padding=0), filters=f(vn), alt=f"Estado del KPI {kid}")
        vn = f"kpi_{kid}_obj"
        p1.add(vn, x + 236, cy + 52, 132, 26, card(OK, "Texto objetivo KPI", show_label=False, value_size=10,
               value_color="#3B4048", align="right", bg=None, padding=0), filters=f(vn),
               alt=f"Objetivo del KPI {kid}")
        vn = f"kpi_{kid}_var"
        p1.add(vn, x + 236, cy + 80, 132, 56, card(OK, "Variación KPI texto", label_text="vs sprint anterior",
               value_size=13, label_size=9, value_color_measure=(OK, "Color variación"), align="right",
               bg=None, padding=0), filters=f(vn), alt=f"Variación del KPI {kid} frente al sprint anterior")
    y = cy + 150 + 16

p1.add("footer", 288, 1040, 1616, 28, textbox(
    "Borde azul = único indicador que penaliza en la factura (por cliente y sprint: Gold < 95 %, Silver < 90 %) · "
    "Brújula Soporte IT (empresa ficticia) · tickets sintéticos (SEED=42), clima y festivos reales · "
    "objetivos editables en la tabla Objetivos KPI · ↗↘ = variación frente al sprint anterior (pp = puntos)",
    9, False, "#3B4048"))
p1.add("kicker", 288, 18, 700, 18, textbox("BRÚJULA SOPORTE IT · SERVICE DESK", 9, True, "#605E5C"))
# Ajuste hecho en Desktop el 2026-11-10 (último guardado, copiado tal cual): número de cumplidos recolocado a mano
p1.override("sum_num", position={"x": 310.12594458438286, "y": 114.25692695214106})

# ---------- página 2: evolución del cumplimiento ----------
# Mismos segmentadores que la página 1, pero Sprint admite varios sprints (sin valor por defecto) y no se
# sincroniza con la página 1, que exige un único sprint.
p2 = Page("evolucion", "Evolución del cumplimiento")
rail(p2, {})

p2.add("title", 288, 16, 1000, 56, textbox("EVOLUCIÓN DEL CUMPLIMIENTO", 22, True, "#1B1F24"))
p2.add("periodo", 1400, 16, 504, 56, card("Sprint", "Periodo seleccionado", label_text="Periodo analizado",
       value_size=14, label_size=9, align="right", bg=None, padding=0), alt="Sprints seleccionados")
SERIES = [(OK, "KPI Cumplido", "Cumplidos", "#1E7B5C"), (OK, "KPI Incumplido", "Incumplidos", "#C0392B")]
# Tres gráficos apilados en la página de 1080 px: 300 px cada uno con 18 px de separación
p2.add("chart", 288, 88, 1616, 300, line_chart(
    ("Sprint", "Sprint"), SERIES, y_max=15, title="Nº de KPI cumplidos e incumplidos por sprint (de 15)"),
    filters=[f_sprint_no_blank(p2.key, "chart")],
    alt="Gráfico de líneas: número de KPI cumplidos e incumplidos en cada sprint")
# Gráficos por bloque, con el formato de referencia (cajas de color en las etiquetas, subtítulo y separador)
for i, (vn, bloque, n, titulo, sub) in enumerate([
    ("chart_sla", "SLA", 3, "Evolución del cumplimiento de los SLA",
     "Nº de KPI de SLA (1ª respuesta, resolución y P1) que cumplen o no su objetivo en cada sprint."),
    ("chart_op", "OPERACIÓN", 4, "Evolución del cumplimiento de la operación",
     "Nº de KPI de operación (MTTR, 1ª respuesta media, tickets por agente y % ausentes) que cumplen o no su objetivo."),
]):
    p2.add(vn, 288, 406 + i * 318, 1616, 300, line_chart(
        ("Sprint", "Sprint"), SERIES, y_max=n, title=titulo, subtitle=sub, boxed_labels=True),
        filters=[f_sprint_no_blank(p2.key, vn), f_bloque(p2.key, vn, bloque)],
        alt=f"Gráfico de líneas: KPI de {bloque.lower()} cumplidos e incumplidos en cada sprint")
# Ajuste hecho en Desktop el 2026-11-10 (copiado tal cual): en el gráfico de SLA, texto de las etiquetas de
# «Cumplidos» en gris del tema (en vez de blanco) y una entrada sin selector con el color 1 del tema
_tc = lambda cid, pct: {"solid": {"color": {"expr": {"ThemeDataColor": {"ColorId": cid, "Percent": pct}}}}}
p2.override("chart_sla", objects={"labels": [
    sel_default(props(show=lit(True), fontSize=num(9), bold=lit(True), labelPosition=lit("Above"), color=color("#FFFFFF"),
                      enableBackground=lit(True), backgroundColor=color("#605E5C"), backgroundTransparency=num(0))),
    {"properties": {"backgroundColor": color("#1E7B5C"), "color": _tc(1, 0.4)}, "selector": {"metadata": f"{OK}.KPI Cumplido"}},
    {"properties": {"backgroundColor": color("#C0392B"), "color": color("#FFFFFF")}, "selector": {"metadata": f"{OK}.KPI Incumplido"}},
    {"properties": {"color": _tc(1, 0)}},
]})
p2.add("footer", 288, 1040, 1616, 28, textbox(
    "Cada sprint se evalúa contra la tabla Objetivos KPI (15 KPI). Si un KPI no tiene datos en un sprint "
    "(p. ej. ningún P1), no cuenta en ninguna de las dos líneas.",
    9, False, "#3B4048"))

# ---------- página 3: facturación ----------
FA = "Facturación"
p3 = Page("facturacion", "Facturación")
# Sprint de un solo valor (siempre hay uno) y sincronizado con las páginas 1 y 4: tarjetas y tabla de clientes
# muestran ese sprint; el gráfico de líneas lo ignora (NoFilter) para seguir mostrando todos los sprints.
rail(p3, dict(single=True, default="2025-17", sync="sprint"))

p3.add("title", 288, 16, 1000, 56, textbox("FACTURACIÓN, PENALIZACIONES Y BONIFICACIONES", 22, True, "#1B1F24"))
p3.add("periodo", 1400, 16, 504, 56, card("Sprint", "Periodo seleccionado", label_text="Periodo analizado",
       value_size=14, label_size=9, align="right", bg=None, padding=0), alt="Sprints seleccionados")

# Balance en verde si es ≥ 0 y en rojo si es negativo (regla de formato condicional, sin medida de color)
BALANCE_FILL = {"solid": {"color": {"expr": {"Conditional": {
    "Cases": [{"Condition": {"Comparison": {"ComparisonKind": 2, "Left": m_expr(FA, "Balance €"),
                                            "Right": {"Literal": {"Value": "0D"}}}},
               "Value": {"Literal": {"Value": "'#1E7B5C'"}}}],
    "DefaultValue": {"Literal": {"Value": "'#C0392B'"}}}}}}}
# Tarjetas (rediseño del 2026-11-12): rótulo gris arriba, cifra grande y una línea inferior con el contexto o la
# variación frente al sprint anterior (verde si mejora, rojo si empeora). Bonificación y penalización llevan un
# cuadradito con el color de su barra en el gráfico; el balance va destacado con borde azul.
TARJETAS = [  # nombre visual, medida de la cifra, rótulo, línea inferior (medida de texto, medida de color o None), cuadradito
    ("kpi_cuota", "Texto cuota sprint", "Facturado en el sprint", ("Texto clientes facturados", None), None),
    ("kpi_bonus", "Bonus €", "Bonificación", ("Texto variación bonificación", "Color variación bonificación"), "#3E7CB8"),
    ("kpi_pen", "Penalización €", "Penalización", ("Texto variación penalización", "Color variación penalización"), "#E8875A"),
    ("kpi_balance", "Texto balance", "Balance (bonificación − penalización)",
     ("Texto variación balance", "Color variación balance"), None),
]
for i, (vn, medida, rotulo, (sub, sub_color), cuadro) in enumerate(TARJETAS):
    x = 288 + i * 410
    p3.add(vn, x, 88, 386, 136, card(FA, medida, label_text=("     " + rotulo) if cuadro else rotulo, value_size=30,
           label_size=11, padding=16, display=rotulo, value_color="#1B1F24"),
           alt=f"{rotulo} del sprint seleccionado")
    p3.add(f"sub_{vn}", x + 16, 186, 354, 22, card(FA, sub, show_label=False, value_size=10,
           value_color_measure=(FA, sub_color) if sub_color else None, value_color="#605E5C", bg=None, padding=0),
           alt=f"{rotulo}: contexto o variación frente al sprint anterior")
    if cuadro:
        p3.add(f"sq_{vn}", x + 16, 107, 10, 10, shape(cuadro, radius=2))
p3.override("kpi_bonus", formats={f"{FA}.Bonus €": "#,0 €"})
p3.override("kpi_pen", formats={f"{FA}.Penalización €": "#,0 €"})

# Barras divergentes (2026-11-12, sustituye al gráfico de líneas): bonificación hacia arriba en azul y penalización
# hacia abajo en naranja, un par de barras por sprint. Siempre todos los sprints (el segmentador Sprint no le afecta).
p3.add("chart_pen_bonus", 288, 242, 1616, 782, diverging_columns(
    ("Sprint", "Etiqueta eje"),
    (FA, "Bonus €", "Bonificación (↑)", "#3E7CB8"),
    (FA, "Penalización negativa €", "Penalización (↓)", "#E8875A"),
    title_measure=(FA, "Título bonificación y penalización")),
    filters=[f_sprint_no_blank(p3.key, "chart_pen_bonus")],
    alt="Gráfico de barras: bonificación (hacia arriba) y penalización (hacia abajo) en euros por sprint")
# Ajuste hecho en Desktop el 2026-10-20 (copiado tal cual): tamaño y posición del gráfico
p3.override("chart_pen_bonus",
    position={"x": 287.41641337386017, "y": 242.1884498480243, "width": 1616.534954407295, "height": 342.85714285714283})
p3.add("clientes", 288, 601, 1616, 423, matrix_visual(
    # Lista plana, sin agrupar: una fila por cliente; el nivel va como columna. Peor % primero.
    rows=[("Cliente", "Cliente", "Cliente")],
    values=[(FA, "Nivel", "Nivel"),
            (FA, "Umbral de penalización", "Umbral de penalización"),
            (FA, "Tickets computables del sprint", "Tickets computables"),
            (FA, "Incumplidos del sprint", "Incumplidos"),
            (FA, "% SLA del sprint", "% SLA de resolución"),
            (FA, "Penalización €", "Total penalización"),
            (FA, "Bonus €", "Total bonificación")],
    sort=(FA, "% SLA del sprint", "Ascending"),
    font_color_measure=((FA, "% SLA del sprint"), (FA, "Color % SLA del sprint")),
    icon_measure=((FA, "% SLA del sprint"), (FA, "Cumple umbral SLA")),
    title="Clientes Gold y Silver: umbral de penalización y % de SLA de resolución en el sprint seleccionado"),
    # Solo los niveles que penalizan (Bronze no penaliza nunca, Ficha §0.3)
    filters=[f_valores(p3.key, "clientes", "Cliente", "Nivel de contrato", ["Gold", "Silver"])],
    alt="Matriz de clientes Gold y Silver ordenada por % de SLA de resolución (✓ cumple / ✗ no cumple): nivel, umbral, tickets computables, incumplidos, %, penalización y bonificación del sprint")
p3.no_filter("s_sprint", ["chart_pen_bonus"])

p3.add("footer", 288, 1036, 1616, 40, textbox(
    "Tarjetas y tabla de clientes (Gold y Silver, los únicos que penalizan): el sprint seleccionado. Gráfico: todos los sprints. "
    "% SLA de resolución = (computables − incumplidos) ÷ computables · ✓ = cumple su umbral · ✗ en rojo = penaliza (tope −3,5 % de la cuota). "
    "Departamento, Tipo y Prioridad no afectan a esta página.",
    9, False, "#3B4048"))

# ---------- página 4: impacto financiero ----------
# Sprint de un solo valor y sincronizado con la página 1: lo usan las barras de cumplimiento. Las tarjetas y la tabla
# lo ignoran (NoFilter) para mostrar todos los sprints del año, y así sus totales cuadran con la fila Total de la tabla.
p4 = Page("impacto", "Impacto financiero")
rail(p4, dict(single=True, default="2025-17", sync="sprint"))

p4.add("title", 288, 16, 1000, 56, textbox("IMPACTO FINANCIERO", 22, True, "#1B1F24"))
p4.add("periodo", 1400, 16, 504, 56, card("Sprint", "Periodo seleccionado", label_text="Sprint de las barras de cumplimiento",
       value_size=14, label_size=9, align="right", bg=None, padding=0), alt="Sprint seleccionado para las barras")

TOTALES = [  # nombre visual, medida, rótulo, color del valor
    ("tot_cuota", "Cuota facturada €", "Total facturado", "#1B1F24"),
    ("tot_bonus", "Bonus €", "Total bonificado", "#1E7B5C"),
    ("tot_pen", "Penalización €", "Total penalizado", "#C0392B"),
]
for i, (vn, medida, rotulo, col) in enumerate(TOTALES):
    p4.add(vn, 288 + i * 547, 88, 522, 130, card(FA, medida, label_text=f"{rotulo} · todos los sprints del año",
           value_size=30, label_size=11, padding=16, display=rotulo, value_color=col),
           alt=f"{rotulo} de todos los sprints del año seleccionado")

p4.add("tabla", 288, 242, 640, 782, table_visual(
    [("col", "Sprint", "Sprint", "Sprint"), ("measure", FA, "Bonus €", "Bonificación"),
     ("measure", FA, "Penalización €", "Penalización")],
    title="Bonificación y penalización por sprint",
    # Ajustes hechos en Desktop el 2026-10-20: sprints con más penalización arriba y anchos de columna
    sort=("measure", FA, "Penalización €", "Descending"),
    widths={f"{FA}.Bonus €": 125.33129244691433, f"{FA}.Penalización €": 174.6595489068937}),
    filters=[f_sprint_no_blank(p4.key, "tabla")],
    alt="Tabla: bonificación y penalización de cada sprint, con el total")

p4.add("barras", 952, 242, 952, 782, stacked_bar(
    (OK, "Bloque"),
    [(OK, "KPI Cumplido", "Cumplidos", "#1E7B5C"), (OK, "KPI Incumplido", "Incumplidos", "#C0392B")],
    title="Cumplimiento por tipo de indicador",
    subtitle="Nº de KPI de cada bloque que cumplen o no su objetivo en el sprint seleccionado."),
    alt="Barras apiladas: KPI cumplidos e incumplidos por tipo de indicador en el sprint seleccionado")
# Ajuste hecho en Desktop el 2026-10-20 (copiado tal cual): alto de las barras
p4.override("barras", position={"x": 952.7051671732522, "y": 242.1884498480243,
                                "width": 951.2462006079028, "height": 322.4316109422492})

p4.no_filter("s_sprint", [vn for vn, *_ in TOTALES] + ["tabla"])
# Pareto de la penalización por cliente (2026-11-12), en el hueco bajo las barras de cumplimiento. Como las tarjetas y
# la tabla de esta página, muestra todo el año (el segmentador Sprint no le afecta). Solo clientes con penalización.
p4.add("pareto", 953, 580, 951, 444, pareto_bars(
    ("Cliente", "Cliente"), (FA, "Penalización €"), (FA, "Color Pareto penalización"),
    (FA, "Texto acumulado penalización"), title_measure=(FA, "Título Pareto penalización"),
    subtitle="Clic en un cliente para filtrar la página"),
    filters=[f_medida(p4.key, "pareto", "Medidas", "Penalización €", 0.0, kind=1)],
    alt="Barras: penalización de cada cliente de mayor a menor, con el % acumulado; en naranja intenso los que suman el 80 %")
p4.override("pareto", vco={"padding": [props(top=num(16), bottom=num(44), left=num(16), right=num(16))]})
for i, (txt, col, letra) in enumerate([("Hasta el 80 % acumulado", "#D9692F", "#FFFFFF"), ("Resto", "#F2C3A6", "#3B4048")]):
    p4.add(f"pareto_ley_{i}", 969 + i * 186, 990, 176 if i == 0 else 80, 22, textbox(txt, 9, True, letra, bg=col, radius=6,
           center=True, padding=2), alt=f"Leyenda: {txt}")
p4.no_filter("s_sprint", ["pareto"])
p4.add("footer", 288, 1040, 1616, 28, textbox(
    "Tarjetas y tabla: todos los sprints del año seleccionado (no les afecta el filtro Sprint). "
    "Barras: el sprint seleccionado, igual que en Cumplimiento de objetivos.",
    9, False, "#3B4048"))

# ---------- página 5: riesgo de penalización por cliente ----------
# Mapa de calor: % de SLA de resolución de cada cliente Gold/Silver (los que penalizan) en los 6 últimos sprints
# facturados, con el fondo de cada celda según su tramo. La ventana es fija (los 6 últimos), así que la matriz y el
# título ignoran los segmentadores Año y Sprint; el resto de filtros (cliente, nivel…) sí les afecta.
p5 = Page("riesgo", "Riesgo por cliente")
rail(p5, {})
p5.add("kicker", 288, 18, 700, 18, textbox("BRÚJULA SOPORTE IT · SERVICE DESK", 9, True, "#605E5C"))
p5.add("titulo", 288, 36, 1240, 34, card("Medidas", "Título riesgo clientes", show_label=False, value_size=18,
       bg=None, padding=0), alt="Cuántos clientes Gold y Silver están en tramo deficiente o cerca de su objetivo")
p5.add("subtitulo", 288, 72, 1240, 20, textbox(
    "SLA de resolución de cada cliente Gold y Silver en los últimos 6 sprints · ordenado de menor a mayor margen "
    "sobre su objetivo en el último sprint", 10, False, "#605E5C"))
p5.add("matriz", 288, 100, 1616, 880, heatmap_matrix(
    rows=[("Cliente", "Cliente", "Cliente"), ("Cliente", "Nivel de contrato", "Nivel"),
          ("Cliente", "Objetivo contractual", "Objetivo")],
    column=("Sprint", "Sprint"),
    value=(FA, "% SLA celda riesgo", "% SLA de resolución"),
    color_measure=(FA, "Color tramo SLA"),
    sort=(FA, "% SLA celda riesgo", "Ascending")),
    # La ventana de 6 sprints la aplica la medida (vacía fuera de ella), no un filtro de visual
    filters=[f_valores("riesgo", "matriz", "Cliente", "Nivel de contrato", ["Gold", "Silver"])],
    alt="Matriz: % de SLA de resolución de cada cliente Gold y Silver en los 6 últimos sprints, coloreado por tramo")
p5.no_filter("s_sprint", ["matriz", "titulo"])
p5.no_filter("s_anio", ["matriz", "titulo"])
# Leyenda de colores (los mismos de la medida Color tramo SLA)
LEYENDA = [("Deficiente máximo", "#F2A26F"), ("Deficiente medio", "#F7C39E"), ("Deficiente leve", "#FBE0CC"),
           ("Neutro", "#F1F3F6"), ("Bonus", "#CFE0F3")]
for i, (txt, col) in enumerate(LEYENDA):
    p5.add(f"ley_{i}", 288 + i * 170, 996, 160, 26, textbox(txt, 9, True, "#3B4048", bg=col, radius=6, center=True,
           padding=3), alt=f"Leyenda: {txt}")
p5.add("footer", 288, 1040, 1616, 28, textbox(
    "Tramos del contrato (Ficha §0.3) · Gold: bonus ≥ 98 %, neutro ≥ 95 %, leve ≥ 92 %, medio ≥ 88 %, máximo < 88 % · "
    "Silver: bonus ≥ 95 %, neutro ≥ 90 %, leve ≥ 85 %, máximo < 85 % · la penalización aplicada tiene el tope del −3,5 %.",
    9, False, "#3B4048"))

# ---------- rediseño hecho en Desktop el 2026-11-10 (19:21) ----------
# Sin la nota del panel de filtros; caja de periodo propia (340 × 80, arriba a la derecha) en todas las páginas;
# fondo de panel propio en las páginas 2–4; sin pie en las páginas 2 y 3. Los objetos nuevos se guardan tal cual en
# _generadores/visuales_desktop/ y los que se quitaron no se vuelven a generar.
for p, quitar in [(p1, ["rail_note", "periodo"]),
                  (p2, ["rail_note", "periodo", "rail_bg", "footer"]),
                  (p3, ["rail_note", "periodo", "rail_bg", "footer"]),
                  (p4, ["rail_note", "periodo", "rail_bg"])]:
    p.remove(*quitar)
    p.add_desktop()
# La página 5 sigue el mismo diseño: copia la caja de periodo y el fondo del panel de la página 2, fondo de página
# gris claro y segmentadores sin fondo ni borde (como los dejó Desktop en las demás páginas)
p5.remove("rail_note", "rail_bg")
p5.add_desktop(from_key="evolucion")
p5.background = [props(color=color("#F3F5F8"), transparency={"expr": {"Literal": {"Value": "10D"}}})]
for s in ("s_anio", "s_sprint", "s_nivel", "s_cliente", "s_dep", "s_tipo", "s_prio"):
    p5.override(s, vco={"background": [props(show=lit(False), color=color("#FFFFFF"), transparency=num(0))],
                        "border": [props(show=lit(False))]})

# ---------- página 6: tickets por departamento ----------
# Departamento × tipo de ticket: nº de tickets (por fecha de creación), % sobre el total y % que impacta en la factura.
# Responde a todos los segmentadores. Mismo estilo que la página 5.
p6 = Page("departamentos", "Tickets por departamento")
rail(p6, {})
p6.add("kicker", 288, 18, 700, 18, textbox("BRÚJULA SOPORTE IT · SERVICE DESK", 9, True, "#605E5C"))
p6.add("titulo", 288, 36, 1240, 34, textbox("Tickets por departamento y tipo", 18, True, "#1B1F24"))
p6.add("subtitulo", 288, 72, 1240, 20, textbox(
    "En cada celda: nº de tickets que entraron en el periodo · % sobre el total de su tipo (cada columna suma 100 %) · % que impacta en la factura "
    "(incidencias y peticiones no canceladas, de todos los clientes)", 10, False, "#605E5C"))
p6.add("matriz", 288, 100, 1616, 560, heatmap_matrix(
    rows=[("Departamento", "Departamento", "Departamento")],
    column=("Política SLA", "Tipo"),
    value=("Departamento", "Texto celda departamento", "Tickets"),
    color_measure=("Departamento", "Color celda departamento"),
    totals=True, wrap=True, align="Center"),
    alt="Matriz: tickets por departamento y tipo, con su % sobre el total y el % que impacta en la factura")
LEYENDA6 = [("≥ 40 % de su tipo", "#9EC5E8"), ("20–40 %", "#BFD8EE"), ("10–20 %", "#D9E7F5"), ("< 10 %", "#EEF4FB")]
for i, (txt, col) in enumerate(LEYENDA6):
    p6.add(f"ley_{i}", 288 + i * 170, 676, 160, 26, textbox(txt, 9, True, "#3B4048", bg=col, radius=6, center=True,
           padding=3), alt=f"Leyenda: {txt}")
p6.add("footer", 288, 1040, 1616, 28, textbox(
    "Tickets por fecha de creación · las tareas son trabajo interno y nunca impactan en la factura · "
    "el color indica el peso del departamento dentro de cada tipo de ticket (incidencias, peticiones o tareas).",
    9, False, "#3B4048"))
p6.remove("rail_note", "rail_bg")
p6.add_desktop(from_key="evolucion")
p6.background = [props(color=color("#F3F5F8"), transparency={"expr": {"Literal": {"Value": "10D"}}})]
for s in ("s_anio", "s_sprint", "s_nivel", "s_cliente", "s_dep", "s_tipo", "s_prio"):
    p6.override(s, vco={"background": [props(show=lit(False), color=color("#FFFFFF"), transparency=num(0))],
                        "border": [props(show=lit(False))]})

PAGES = [p1, p2, p3, p4, p5, p6]

# ---------- todas las medidas viven en la tabla Medidas ----------
# Las páginas se escriben citando cada medida con la tabla donde estaba antes (más legible al construirlas).
# Este paso redirige a "Medidas" toda referencia a una medida: campos, queryRef y selectores.
MEDIDAS_TMDL = os.path.join(ROOT, f"{NAME}.SemanticModel", "definition", "tables", "Medidas.tmdl")
with open(MEDIDAS_TMDL, encoding="utf-8") as fh:
    # TMDL solo entrecomilla los nombres con espacios o símbolos (measure Nivel = ... va sin comillas)
    MEDIDAS = {a or b for a, b in re.findall(r"^\tmeasure (?:'([^']+)'|([^\s=]+))", fh.read(), re.M)}

def a_medidas(o):
    if isinstance(o, dict):
        m = o.get("Measure")
        if isinstance(m, dict) and m.get("Property") in MEDIDAS and "Entity" in m.get("Expression", {}).get("SourceRef", {}):
            m["Expression"]["SourceRef"]["Entity"] = "Medidas"
        for k in ("queryRef", "metadata"):
            v = o.get(k)
            if isinstance(v, str) and "." in v and v.split(".", 1)[1] in MEDIDAS:
                o[k] = "Medidas." + v.split(".", 1)[1]
        for v in o.values():
            a_medidas(v)
    elif isinstance(o, list):
        for v in o:
            a_medidas(v)

for p in PAGES:
    for v in p.visuals:
        a_medidas(v)

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
if os.path.isdir(theme_dir):  # se vacía en vez de borrarla: en Windows falla si otro proceso tiene la carpeta abierta
    for f in os.listdir(theme_dir):
        p = os.path.join(theme_dir, f)
        shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
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
    # Ajuste hecho en Desktop el 2026-11-09: panel de filtros de Power BI plegado
    "objects": {"outspacePane": [props(expanded=lit(False))]},
})
dump(os.path.join(DEF, "pages", "pages.json"), {
    "$schema": f"{SCH}/pagesMetadata/1.0.0/schema.json",
    "pageOrder": [p.id for p in PAGES], "activePageName": PAGES[0].id})
for p in PAGES:
    pdir = os.path.join(DEF, "pages", p.id)
    page_obj = {
        "$schema": f"{SCH}/page/2.1.0/schema.json", "name": p.id, "displayName": p.display,
        "displayOption": "FitToPage", "height": 1080, "width": 1920,
        "objects": {"background": p.background or [props(color=color("#FFFFFF"), transparency=num(0))],
                    "outspace": [props(color=color("#FFFFFF"))]}}
    if p.interactions:
        page_obj["visualInteractions"] = [{"source": s, "target": t, "type": ty} for s, t, ty in p.interactions]
    dump(os.path.join(pdir, "page.json"), page_obj)
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
