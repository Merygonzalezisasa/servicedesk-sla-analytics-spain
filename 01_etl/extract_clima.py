"""
extract_clima.py — Clima diario real de la sede de soporte (Madrid), desde Open-Meteo.

Alimenta dim_clima_madrid y la correlación 2 de la Ficha (calor → incidencias de Infraestructura).
Open-Meteo devuelve la celda de rejilla más cercana a las coordenadas pedidas (~4 km), no una
estación concreta; para un efecto diario de calor es suficiente.

Salida: data/raw/clima_madrid.csv  (una fila por día del período)
Uso:    python 01_etl/extract_clima.py
"""

from datetime import date

import pandas as pd

from comun import DIR_RAW, config, configurar_log, get_json

log = configurar_log("extract_clima")

VARIABLES = ["temperature_2m_max", "temperature_2m_min", "precipitation_sum"]
UMBRAL_CALOR_C = 35.0  # Ficha §2.3: día caluroso si Tmax > 35 °C

# Rangos plausibles para Madrid. Un valor fuera indica un error de datos, no un récord.
RANGOS = {"temp_max": (-10, 47), "temp_min": (-15, 32), "precipitacion_mm": (0, 150)}


def fetch_clima(inicio: date, fin: date) -> pd.DataFrame:
    datos = get_json(config("OPEN_METEO_URL"), log, params={
        "latitude": config("SEDE_LAT"), "longitude": config("SEDE_LON"),
        "start_date": inicio.isoformat(), "end_date": fin.isoformat(),
        "daily": ",".join(VARIABLES), "timezone": "Europe/Madrid",
    })
    log.info(f"Celda devuelta: lat {datos['latitude']}, lon {datos['longitude']}, "
             f"elevación {datos['elevation']} m")
    d = datos["daily"]
    return pd.DataFrame({
        "fecha": pd.to_datetime(d["time"], format="%Y-%m-%d"),
        "temp_max": d["temperature_2m_max"],
        "temp_min": d["temperature_2m_min"],
        "precipitacion_mm": d["precipitation_sum"],
    })


def limpiar_y_validar(df: pd.DataFrame, inicio: date, fin: date) -> pd.DataFrame:
    # 1. Calendario completo: si la API se saltara un día, aparecería como hueco.
    calendario = pd.date_range(inicio, fin, freq="D")
    faltan = calendario.difference(df["fecha"])
    if len(faltan):
        log.warning(f"Faltan {len(faltan)} días en la respuesta; se rellenan")
    df = df.set_index("fecha").reindex(calendario).rename_axis("fecha")

    # 2. Nulos: la temperatura es continua, así que se rellena con el día anterior (forward fill).
    #    La lluvia no: un nulo de lluvia se deja en 0 y se registra.
    nulos = df.isna().sum()
    if nulos.any():
        log.warning(f"Nulos antes de limpiar: {nulos[nulos > 0].to_dict()}")
        df[["temp_max", "temp_min"]] = df[["temp_max", "temp_min"]].ffill().bfill()
        df["precipitacion_mm"] = df["precipitacion_mm"].fillna(0)

    # 3. Rangos plausibles y coherencia interna.
    for col, (minimo, maximo) in RANGOS.items():
        fuera = df[(df[col] < minimo) | (df[col] > maximo)]
        assert fuera.empty, f"{col} fuera de rango [{minimo}, {maximo}]: {fuera[col].to_dict()}"
    assert (df["temp_min"] <= df["temp_max"]).all(), "Hay días con temp_min > temp_max"
    assert df.notna().all().all(), "Quedan nulos tras la limpieza"

    df["es_dia_caluroso"] = df["temp_max"] > UMBRAL_CALOR_C
    return df.reset_index()


def main() -> None:
    inicio = date.fromisoformat(config("FECHA_INICIO"))
    fin = date.fromisoformat(config("FECHA_FIN"))
    log.info(f"Extrayendo clima de Madrid entre {inicio} y {fin}")

    df = limpiar_y_validar(fetch_clima(inicio, fin), inicio, fin)

    DIR_RAW.mkdir(parents=True, exist_ok=True)
    salida = DIR_RAW / "clima_madrid.csv"
    df.to_csv(salida, index=False, date_format="%Y-%m-%d")

    calurosos = df.groupby(df["fecha"].dt.year)["es_dia_caluroso"].sum().astype(int).to_dict()
    log.info(f"Guardado {salida.name}: {len(df)} días · Tmax {df['temp_max'].min()}–"
             f"{df['temp_max'].max()} °C · días > {UMBRAL_CALOR_C:.0f} °C por año: {calurosos}")


if __name__ == "__main__":
    main()
