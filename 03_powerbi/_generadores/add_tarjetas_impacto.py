"""Tarjetas de la página «Impacto económico acumulado»: 4 en fila (añade Balance económico neto)
y una leyenda debajo de cada cifra (etiqueta de referencia del cardVisual).

Parte del último guardado: conserva iconos, títulos y formato de las tres tarjetas existentes;
solo cambia posición/ancho, añade la leyenda y crea la tarjeta de balance copiando la de penalización.
Se puede relanzar.

Uso: python -X utf8 add_tarjetas_impacto.py "<carpeta Brujula SLA.Report>"
"""
import copy, hashlib, json, os, sys, uuid

REPORT = sys.argv[1]
PAGINA = os.path.join(REPORT, "definition", "pages", "d9140412a99203aedb0f")
VISUALES = os.path.join(PAGINA, "visuals")

Y, ALTO, X0, ANCHO, HUECO = 162, 130, 288, 386, 24   # 4 × 386 + 3 × 24 = 1616 (ancho del contenido)
GRIS_LEYENDA = "#605E5C"

BALANCE_ID = hashlib.sha1(b"impacto/balance").hexdigest()[:20]
ICONO_BALANCE = ("balance-de-peso.png", "balance-de-peso9854340694944405.png")

# id de visual (prefijo) → medida de la leyenda
TARJETAS = [
    ("d278a4e6335aef26271f", "Texto sprints analizados"),
    ("f93475ef96e7329c4238", "Texto % bonificación sobre cuota"),
    ("506ed5c06b0b23e01f56", "Texto % penalización sobre cuota"),
    (BALANCE_ID, "Texto % balance sobre cuota"),
]


def lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def medida(nombre):
    return {"expr": {"Measure": {"Expression": {"SourceRef": {"Entity": "Medidas"}}, "Property": nombre}}}


def leer(vid):
    with open(os.path.join(VISUALES, vid, "visual.json"), encoding="utf-8") as f:
        return json.load(f)


def guardar(vid, v):
    os.makedirs(os.path.join(VISUALES, vid), exist_ok=True)
    with open(os.path.join(VISUALES, vid, "visual.json"), "w", encoding="utf-8") as f:
        json.dump(v, f, ensure_ascii=False, indent=2)
        f.write("\n")


def crear_balance():
    """Copia la tarjeta de penalización y la convierte en la de balance."""
    v = copy.deepcopy(leer("506ed5c06b0b23e01f56"))
    v["name"] = BALANCE_ID
    v["position"].update(z=11500, tabOrder=10500)
    vis = v["visual"]
    proy = vis["query"]["queryState"]["Data"]["projections"][0]
    proy["field"]["Measure"]["Property"] = "Balance €"
    proy.update(queryRef="Medidas.Balance €", nativeQueryRef="Balance €", displayName="Balance económico neto")
    o = vis["objects"]
    for e in o["value"]:
        if e.get("selector", {}).get("id") == "default":
            e["properties"]["fontColor"] = {"solid": {"color": medida("Color balance")}}
        elif "metadata" in e.get("selector", {}):
            e["selector"]["metadata"] = "Medidas.Balance €"
    o["label"] = [e for e in o["label"] if "metadata" not in e.get("selector", {})]
    for e in o["label"]:
        e["properties"]["text"] = lit("'Balance económico neto'")
    o["label"].append({"properties": {"text": lit("'Balance económico neto'")},
                       "selector": {"metadata": "Medidas.Balance €"}})
    img = o["image"][0]["properties"]["image"]["image"]
    img["name"] = lit(f"'{ICONO_BALANCE[0]}'")
    img["url"]["expr"]["ResourcePackageItem"]["ItemName"] = ICONO_BALANCE[1]
    v["visual"]["visualContainerObjects"]["general"][0]["properties"]["altText"] = lit(
        "'Balance neto (bonificación menos penalización) de todos los sprints del año seleccionado'")
    return v


def poner_leyenda(v, texto):
    o = v["visual"]["objects"]
    qref = v["visual"]["query"]["queryState"]["Data"]["projections"][0]["queryRef"]
    fid = "field-" + str(uuid.uuid5(uuid.NAMESPACE_URL, f"brujula/{v['name']}/leyenda"))
    sel = {"metadata": qref, "id": fid}
    o["referenceLabel"] = [{"properties": {"value": medida(texto)},
                            "selector": {"data": [{"dataViewWildcard": {"matchingOption": 0}}], **sel, "order": 0}}]
    o["referenceLabelTitle"] = [{"properties": {"show": lit("false")}, "selector": dict(sel)}]
    o["referenceLabelValue"] = [{"properties": {"show": lit("true"), "valueFontSize": lit("10D"), "valueBold": lit("false"),
                                                "valueFontColor": {"solid": {"color": lit(f"'{GRIS_LEYENDA}'")}}},
                                 "selector": dict(sel)}]
    o["referenceLabelDetail"] = [{"properties": {"show": lit("false")}, "selector": dict(sel)}]
    o["referenceLabelLayout"] = [{"properties": {"position": lit("'below'")}}]


def main():
    if not os.path.isdir(os.path.join(VISUALES, BALANCE_ID)):
        guardar(BALANCE_ID, crear_balance())
        print("creada la tarjeta de balance", BALANCE_ID)
    for i, (vid, texto) in enumerate(TARJETAS):
        v = leer(vid)
        v["position"].update(x=X0 + i * (ANCHO + HUECO), y=Y, width=ANCHO, height=ALTO)
        poner_leyenda(v, texto)
        guardar(vid, v)
        print(vid, "x", v["position"]["x"], "· leyenda:", texto)


if __name__ == "__main__":
    main()
