"""
generate_tickets_data.py — Datos sintéticos de Brújula Soporte IT (empresa ficticia).

Paso 2 (este archivo, por ahora): las dimensiones del modelo.
    calendario laboral de Madrid · departamentos · agentes y sus vacaciones · clientes y contratos
    · políticas de SLA · tramos de bonus/malus
Paso 3 (pendiente): los tickets, su historial de estados y el cálculo del SLA.

Todo sale de constantes visibles y de una semilla fija (SEED): correr el script dos veces produce
exactamente los mismos CSV. Necesita antes los festivos reales (01_etl/extract_festivos.py).

Salida: data/raw/dim_*.csv y data/raw/agente_ausencia.csv
Uso:    python 01_etl/generate_tickets_data.py
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd
from faker import Faker

from comun import DIR_RAW, config, configurar_log

log = configurar_log("generate_tickets_data")

# ---------------------------------------------------------------------------------------------
# Constantes del negocio (Ficha §0.2, §0.3 y §2.2)
# ---------------------------------------------------------------------------------------------
SEED = 42
FECHA_INICIO = date.fromisoformat(config("FECHA_INICIO"))
FECHA_FIN = date.fromisoformat(config("FECHA_FIN"))

DEPARTAMENTOS = [
    # id, nombre, rol, nº de agentes, nivel de soporte
    (1, "Service Desk N1", "Recepción, triaje y resolución de primer nivel", 12, "N1"),
    (2, "Soporte Aplicaciones N2", "Errores funcionales de las aplicaciones del cliente", 9, "N2"),
    (3, "Infraestructura", "Servidores, red, cloud y caídas de servicio", 6, "N2"),
    (4, "Desarrollo", "Bugs que requieren cambio de código", 5, "N3"),
    (5, "Seguridad", "Accesos, vulnerabilidades e incidentes de seguridad", 3, "N3"),
]

# nivel: (nº de clientes, cuota mensual mín-máx €, usuarios mín-máx, años de alta posibles)
NIVELES_CONTRATO = {
    "Gold": (8, (25_000, 40_000), (800, 3_000), (2015, 2022)),
    "Silver": (14, (8_000, 20_000), (200, 900), (2016, 2024)),
    "Bronze": (18, (2_000, 6_000), (30, 250), (2018, 2025)),
}

SECTORES = {  # sector: prefijo para el nombre ficticio
    "Banca": "Banca", "Seguros": "Seguros", "Retail": "Comercial", "Sanidad": "Clínicas",
    "Energía": "Energía", "Administración pública": "Consorcio", "Logística": "Transportes",
}

# La mayoría de clientes de un proveedor madrileño están en Madrid; el resto, en grandes polos.
COMUNIDADES = {
    "Comunidad de Madrid": 0.40, "Cataluña": 0.18, "Andalucía": 0.10,
    "Comunitat Valenciana": 0.10, "País Vasco": 0.08, "Castilla y León": 0.05,
    "Galicia": 0.05, "Aragón": 0.04,
}

# Matriz de SLA (Ficha §0.2). Minutos; P1 corre 24x7 y el resto en horario laboral (9 h/día).
H = 60
POLITICAS_SLA = [
    # tipo, prioridad, 1ª respuesta, resolución, reloj
    ("Incidencia", "P1", 15, 4 * H, "24x7"),
    ("Incidencia", "P2", 30, 8 * H, "laboral"),
    ("Incidencia", "P3", 2 * H, 18 * H, "laboral"),
    ("Incidencia", "P4", 4 * H, 36 * H, "laboral"),
    ("Petición", "P2", 2 * H, 18 * H, "laboral"),
    ("Petición", "P3", 4 * H, 36 * H, "laboral"),
    ("Petición", "P4", 8 * H, 72 * H, "laboral"),
    ("Tarea", "P2", 4 * H, 27 * H, "laboral"),
    ("Tarea", "P3", 8 * H, 54 * H, "laboral"),
    ("Tarea", "P4", 9 * H, 90 * H, "laboral"),
]

# Tramos de ajuste mensual sobre la cuota (Ficha §0.3). % de cumplimiento [desde, hasta).
TRAMOS = [
    # nivel, desde, hasta, tipo, % ajuste
    ("Gold", 98.0, 100.01, "bonus", 3.0), ("Gold", 95.0, 98.0, "neutro", 0.0),
    ("Gold", 92.0, 95.0, "malus", -5.0), ("Gold", 88.0, 92.0, "malus", -10.0),
    ("Gold", 0.0, 88.0, "malus", -15.0),
    ("Silver", 95.0, 100.01, "bonus", 2.0), ("Silver", 90.0, 95.0, "neutro", 0.0),
    ("Silver", 85.0, 90.0, "malus", -5.0), ("Silver", 0.0, 85.0, "malus", -10.0),
    ("Bronze", 92.0, 100.01, "bonus", 1.0), ("Bronze", 0.0, 92.0, "neutro", 0.0),
]

# Vacaciones (correlación 6): 22 días laborables por agente y año, concentrados en verano.
DIAS_VACACIONES = 22
PROB_MES_VERANO = {7: 0.35, 8: 0.45, 6: 0.10, 9: 0.10}  # mes del bloque largo de verano
PROB_NAVIDAD = 0.6
PROB_BAJA_MEDICA = 0.15  # por agente y año

rng = np.random.default_rng(SEED)
Faker.seed(SEED)
fake = Faker("es_ES")


# ---------------------------------------------------------------------------------------------
# Calendario
# ---------------------------------------------------------------------------------------------
def build_dim_tiempo() -> pd.DataFrame:
    """Calendario completo con lo que necesita el reloj de SLA y la correlación post-festivo."""
    ruta = DIR_RAW / "festivos_madrid.csv"
    if not ruta.exists():
        raise FileNotFoundError("Falta festivos_madrid.csv: ejecuta antes 01_etl/extract_festivos.py")
    festivos = pd.read_csv(ruta, parse_dates=["fecha"]).set_index("fecha")["nombre"]

    df = pd.DataFrame({"fecha": pd.date_range(FECHA_INICIO, FECHA_FIN, freq="D")})
    df["anio"] = df["fecha"].dt.year
    df["trimestre"] = df["fecha"].dt.quarter
    df["mes"] = df["fecha"].dt.month
    df["dia_semana"] = df["fecha"].dt.dayofweek + 1  # 1 = lunes … 7 = domingo
    df["es_fin_semana"] = df["dia_semana"] >= 6
    df["nombre_festivo"] = df["fecha"].map(festivos)
    df["es_festivo_madrid"] = df["nombre_festivo"].notna()
    df["es_laborable"] = ~df["es_fin_semana"] & ~df["es_festivo_madrid"]

    # Post-festivo: primer laborable tras un tramo no laborable que incluyó un festivo entre
    # semana (un fin de semana normal no cuenta: es la cola extra que deja el festivo).
    festivo_entre_semana = df["es_festivo_madrid"] & ~df["es_fin_semana"]
    post, tramo_con_festivo = [], False
    for laborable, fest in zip(df["es_laborable"], festivo_entre_semana):
        post.append(laborable and tramo_con_festivo)
        tramo_con_festivo = False if laborable else (tramo_con_festivo or fest)
    df["es_post_festivo"] = post

    # Puente: laborable encajado entre un festivo entre semana y el fin de semana.
    ant, sig = festivo_entre_semana.shift(1, fill_value=False), festivo_entre_semana.shift(-1, fill_value=False)
    df["es_puente"] = df["es_laborable"] & (
        (ant & (df["dia_semana"] == 5)) | (sig & (df["dia_semana"] == 1)))
    return df


# ---------------------------------------------------------------------------------------------
# Organización: departamentos, agentes y ausencias
# ---------------------------------------------------------------------------------------------
def build_dim_departamento() -> pd.DataFrame:
    return pd.DataFrame(DEPARTAMENTOS, columns=["departamento_id", "nombre", "rol",
                                                "n_agentes", "nivel_soporte"])


def build_dim_agente() -> pd.DataFrame:
    filas, n = [], 0
    for dep_id, _, _, n_agentes, nivel in DEPARTAMENTOS:
        for _ in range(n_agentes):
            n += 1
            # La mayoría ya estaba antes de 2024; unos pocos entran durante el período.
            if rng.random() < 0.88:
                alta = fake.date_between(date(2016, 1, 1), FECHA_INICIO - timedelta(days=1))
            else:
                alta = fake.date_between(FECHA_INICIO, date(FECHA_FIN.year, 6, 30))
            filas.append({
                "agente_id": f"AGT-{n:03d}", "nombre": f"{fake.first_name()} {fake.last_name()}",
                "departamento_id": dep_id, "nivel_soporte": nivel,
                "seniority": "senior" if rng.random() < 0.4 else "junior",
                "fecha_alta": alta,
            })
    return pd.DataFrame(filas)


def _bloque(laborables: list, inicio_idx: int, n: int, ocupados: set) -> list | None:
    """n días laborables seguidos desde inicio_idx, o None si se pisa con otra ausencia."""
    dias = laborables[inicio_idx:inicio_idx + n]
    if len(dias) < n or any(d in ocupados for d in dias):
        return None
    return dias


def build_agente_ausencia(agentes: pd.DataFrame, tiempo: pd.DataFrame) -> pd.DataFrame:
    """
    Vacaciones y bajas por agente y año. Es la palanca de la correlación 6: el bloque largo de
    verano cae sobre todo en agosto, así que la capacidad del equipo baja en ese mes.
    """
    filas = []
    for anio in range(FECHA_INICIO.year, FECHA_FIN.year + 1):
        lab = tiempo[tiempo["es_laborable"] & (tiempo["anio"] == anio)]["fecha"].dt.date.tolist()
        idx_por_mes = {m: [i for i, d in enumerate(lab) if d.month == m] for m in range(1, 13)}

        for ag in agentes.itertuples():
            disponibles = [d for d in lab if d >= ag.fecha_alta]
            if not disponibles:
                continue
            ocupados: set = set()
            # Recién llegados tienen vacaciones proporcionales a lo que les queda de año.
            cupo = round(DIAS_VACACIONES * len(disponibles) / len(lab))

            def registrar(dias, motivo):
                ocupados.update(dias)
                filas.append({"agente_id": ag.agente_id, "fecha_inicio": dias[0],
                              "fecha_fin": dias[-1], "dias_laborables": len(dias), "motivo": motivo})

            # 1. Bloque largo de verano (10 o 15 laborables).
            mes = rng.choice(list(PROB_MES_VERANO), p=list(PROB_MES_VERANO.values()))
            largo = min(int(rng.choice([10, 10, 15])), cupo)
            for _ in range(20):
                dias = _bloque(lab, int(rng.choice(idx_por_mes[mes])), largo, ocupados)
                if dias and dias[0] >= ag.fecha_alta:
                    registrar(dias, "vacaciones")
                    break

            # 2. Navidad: 3 a 5 laborables en la última quincena del año.
            restantes = cupo - len(ocupados)
            if rng.random() < PROB_NAVIDAD and restantes >= 3:
                n = int(min(rng.integers(3, 6), restantes))
                fin_anio = [i for i, d in enumerate(lab) if d >= date(anio, 12, 18)]
                dias = _bloque(lab, int(rng.choice(fin_anio[:max(1, len(fin_anio) - n + 1)])), n, ocupados)
                if dias and dias[0] >= ag.fecha_alta:
                    registrar(dias, "vacaciones")

            # 3. El resto, en días sueltos o puentes de 1 a 3 días repartidos por el año.
            intentos = 0
            while len(ocupados) < cupo and intentos < 200:
                intentos += 1
                n = int(min(rng.integers(1, 4), cupo - len(ocupados)))
                dias = _bloque(lab, int(rng.integers(0, len(lab))), n, ocupados)
                if dias and dias[0] >= ag.fecha_alta:
                    registrar(dias, "vacaciones")

            # 4. Baja médica ocasional (no cuenta como vacaciones).
            if rng.random() < PROB_BAJA_MEDICA:
                for _ in range(20):
                    dias = _bloque(lab, int(rng.integers(0, len(lab))), int(rng.integers(3, 11)), ocupados)
                    if dias and dias[0] >= ag.fecha_alta:
                        registrar(dias, "baja médica")
                        break

    df = pd.DataFrame(filas).sort_values(["agente_id", "fecha_inicio"]).reset_index(drop=True)
    df.insert(0, "ausencia_id", range(1, len(df) + 1))
    return df


# ---------------------------------------------------------------------------------------------
# Clientes, SLA y tramos
# ---------------------------------------------------------------------------------------------
def build_dim_cliente() -> pd.DataFrame:
    filas, n = [], 0
    comunidades, pesos = list(COMUNIDADES), list(COMUNIDADES.values())
    for nivel, (cantidad, (cuota_min, cuota_max), (usu_min, usu_max), (a_min, a_max)) in NIVELES_CONTRATO.items():
        for _ in range(cantidad):
            n += 1
            sector = rng.choice(list(SECTORES))
            alta = fake.date_between(date(a_min, 1, 1), min(date(a_max, 12, 31), FECHA_FIN))
            filas.append({
                "cliente_id": f"CLI-{n:03d}",
                "nombre": f"{SECTORES[sector]} {fake.last_name()} {rng.choice(['S.A.', 'S.L.'])}",
                "sector": sector,
                "comunidad_autonoma": rng.choice(comunidades, p=pesos),
                "nivel_contrato": nivel,
                # Cuota redondeada a 500 €, como en un contrato real.
                "cuota_mensual_eur": int(round(rng.uniform(cuota_min, cuota_max) / 500) * 500),
                "n_usuarios": int(rng.integers(usu_min, usu_max + 1)),
                "fecha_alta": alta,
            })
    return pd.DataFrame(filas)


def build_dim_sla() -> pd.DataFrame:
    df = pd.DataFrame(POLITICAS_SLA, columns=["tipo", "prioridad", "objetivo_respuesta_min",
                                              "objetivo_resolucion_min", "reloj"])
    df.insert(0, "sla_id", df["tipo"].str[:3].str.upper() + "-" + df["prioridad"])
    # Solo incidencias y peticiones cuentan para el bonus/malus de la factura (Ficha §0.3).
    df["computa_facturacion"] = df["tipo"].isin(["Incidencia", "Petición"])
    return df


def build_dim_tramo_ajuste() -> pd.DataFrame:
    df = pd.DataFrame(TRAMOS, columns=["nivel_contrato", "pct_desde", "pct_hasta", "tipo", "pct_ajuste"])
    df.insert(0, "tramo_id", range(1, len(df) + 1))
    return df


# ---------------------------------------------------------------------------------------------
# Resumen y salida
# ---------------------------------------------------------------------------------------------
def capacidad_mensual(agentes: pd.DataFrame, ausencias: pd.DataFrame, tiempo: pd.DataFrame) -> pd.Series:
    """% medio de agentes ausentes por mes (días laborables): la prueba de la correlación 6."""
    lab = tiempo[tiempo["es_laborable"]][["fecha", "mes"]].copy()
    lab["fecha"] = lab["fecha"].dt.date
    activos = lab["fecha"].map(lambda d: (agentes["fecha_alta"] <= d).sum())
    ausentes_dia: dict = {}
    for a in ausencias.itertuples():
        for d in pd.bdate_range(a.fecha_inicio, a.fecha_fin).date:
            ausentes_dia[d] = ausentes_dia.get(d, 0) + 1
    lab["pct_ausentes"] = lab["fecha"].map(lambda d: ausentes_dia.get(d, 0)) / activos * 100
    return lab.groupby("mes")["pct_ausentes"].mean().round(1)


def guardar(df: pd.DataFrame, nombre: str) -> None:
    df.to_csv(DIR_RAW / f"{nombre}.csv", index=False, date_format="%Y-%m-%d")
    log.info(f"  {nombre}.csv: {len(df):,} filas".replace(",", "."))


def main() -> None:
    log.info(f"Generando dimensiones (SEED={SEED}) entre {FECHA_INICIO} y {FECHA_FIN}")
    DIR_RAW.mkdir(parents=True, exist_ok=True)

    tiempo = build_dim_tiempo()
    departamentos = build_dim_departamento()
    agentes = build_dim_agente()
    ausencias = build_agente_ausencia(agentes, tiempo)
    clientes = build_dim_cliente()
    sla = build_dim_sla()
    tramos = build_dim_tramo_ajuste()

    for df, nombre in [(tiempo, "dim_tiempo"), (departamentos, "dim_departamento"),
                       (agentes, "dim_agente"), (ausencias, "agente_ausencia"),
                       (clientes, "dim_cliente"), (sla, "dim_sla"), (tramos, "dim_tramo_ajuste")]:
        guardar(df, nombre)

    log.info(f"Calendario: {tiempo['es_laborable'].sum()} laborables, "
             f"{tiempo['es_post_festivo'].sum()} post-festivo, {tiempo['es_puente'].sum()} puentes")
    log.info(f"Clientes por nivel: {clientes['nivel_contrato'].value_counts().to_dict()} · "
             f"altas en el período: {(clientes['fecha_alta'] >= FECHA_INICIO).sum()}")
    log.info(f"Agentes: {len(agentes)} · altas en el período: {(agentes['fecha_alta'] >= FECHA_INICIO).sum()}")
    cap = capacidad_mensual(agentes, ausencias, tiempo)
    log.info("% medio de agentes ausentes por mes: "
             + " · ".join(f"{m}:{v}%" for m, v in cap.items()))


if __name__ == "__main__":
    main()
