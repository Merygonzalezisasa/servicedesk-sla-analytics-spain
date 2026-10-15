"""
extract_festivos.py — Festivos que detienen el reloj de SLA en la sede de soporte (Madrid).

Fuente real: Nager.Date (festivos nacionales + Comunidad de Madrid). La API no trae los festivos
locales de Madrid capital y no siempre refleja los cambios autonómicos de cada año, así que se
completa con data/manual/festivos_madrid_correcciones.csv, contrastado con el BOCM.

Salida: data/raw/festivos_madrid.csv  (una fila por fecha festiva)
Uso:    python 01_etl/extract_festivos.py
"""

from datetime import date

import pandas as pd

from comun import DIR_MANUAL, DIR_RAW, config, configurar_log, get_json

log = configurar_log("extract_festivos")

# Madrid tiene 12 festivos nacionales/autonómicos + 2 locales. Si un año se sale de este rango,
# algo cambió en la API o falta una corrección manual.
FESTIVOS_ESPERADOS = range(13, 17)


def fetch_nager(anio: int, pais: str, comunidad: str) -> pd.DataFrame:
    """Festivos de un año que aplican a la comunidad: nacionales (sin counties) o de esa comunidad."""
    datos = get_json(f"{config('NAGER_URL')}/{anio}/{pais}", log)
    filas = []
    for f in datos:
        if not f["counties"]:
            ambito = "nacional"
        elif comunidad in f["counties"]:
            ambito = "autonomico"
        else:
            continue  # festivo de otra comunidad: no detiene el reloj en Madrid
        filas.append({"fecha": f["date"], "nombre": f["localName"], "ambito": ambito,
                      "fuente": "Nager.Date"})
    log.info(f"{anio}: {len(datos)} festivos en la API, {len(filas)} aplican a {comunidad}")
    return pd.DataFrame(filas)


def cargar_correcciones() -> pd.DataFrame:
    manual = pd.read_csv(DIR_MANUAL / "festivos_madrid_correcciones.csv")
    pendientes = (manual["verificado"] != "si").sum()
    if pendientes:
        log.warning(f"{pendientes} festivos manuales aún sin verificar en el BOCM")
    return manual.assign(fuente="manual (BOCM)")[["fecha", "nombre", "ambito", "fuente"]]


def validar(df: pd.DataFrame, inicio: date, fin: date) -> None:
    assert df["fecha"].notna().all(), "Hay festivos sin fecha"
    assert not df["fecha"].duplicated().any(), "Hay fechas de festivo duplicadas"
    fuera = df[(df["fecha"] < pd.Timestamp(inicio)) | (df["fecha"] > pd.Timestamp(fin))]
    assert fuera.empty, f"Festivos fuera del período: {fuera['fecha'].tolist()}"
    for anio, n in df.groupby(df["fecha"].dt.year).size().items():
        if n not in FESTIVOS_ESPERADOS:
            log.warning(f"{anio}: {n} festivos (lo esperado es 14). Revisar API y correcciones")


def main() -> None:
    inicio = date.fromisoformat(config("FECHA_INICIO"))
    fin = date.fromisoformat(config("FECHA_FIN"))
    pais, comunidad = config("PAIS_ISO2"), config("COMUNIDAD_ISO")
    log.info(f"Extrayendo festivos de {comunidad} entre {inicio} y {fin}")

    api = pd.concat([fetch_nager(a, pais, comunidad) for a in range(inicio.year, fin.year + 1)])
    manual = cargar_correcciones()

    # Si una fecha está en ambas fuentes, manda la API: la corrección manual solo añade lo que falta.
    nuevas = manual[~manual["fecha"].isin(api["fecha"])]
    log.info(f"Correcciones manuales: {len(manual)} filas, {len(nuevas)} fechas nuevas añadidas")

    df = pd.concat([api, nuevas], ignore_index=True)
    df["fecha"] = pd.to_datetime(df["fecha"], format="%Y-%m-%d")
    df = df[(df["fecha"].dt.date >= inicio) & (df["fecha"].dt.date <= fin)]
    # Un festivo en fin de semana no cambia el reloj de SLA (ya no era laborable), pero se conserva.
    df["es_fin_semana"] = df["fecha"].dt.dayofweek >= 5
    df = df.sort_values("fecha").reset_index(drop=True)

    validar(df, inicio, fin)

    DIR_RAW.mkdir(parents=True, exist_ok=True)
    salida = DIR_RAW / "festivos_madrid.csv"
    df.to_csv(salida, index=False, date_format="%Y-%m-%d")

    laborables = df[~df["es_fin_semana"]]
    resumen = laborables.groupby(laborables["fecha"].dt.year).size().to_dict()
    log.info(f"Guardado {salida.name}: {len(df)} festivos ({len(laborables)} en día laborable: {resumen})")


if __name__ == "__main__":
    main()
