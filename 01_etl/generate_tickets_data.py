"""
generate_tickets_data.py — Datos sintéticos de Brújula Soporte IT (empresa ficticia).

Paso 2: las dimensiones del modelo.
    calendario laboral de Madrid y sprints · departamentos · agentes y sus vacaciones · clientes y contratos
    · políticas de SLA · tramos de bonus/penalización
Paso 3: los tickets, su historial de estados y la medición del SLA por sprint (Ficha §0.4).
    Cada ticket se planifica entero (respuesta, colas, trabajo por departamento, pausas) en minutos de
    reloj de SLA, se recorre en el tiempo real con su reloj (24x7 o laboral) y se corta en CORTE.

Todo sale de constantes visibles y de una semilla fija (SEED): correr el script dos veces produce
exactamente los mismos CSV. Necesita antes los festivos y el clima reales (01_etl/extract_*.py).

Salida: data/raw/dim_*.csv (incluida dim_sprint), data/raw/agente_ausencia.csv,
        data/raw/fact_ticket.csv y data/raw/fact_ticket_estado.csv
Uso:    python 01_etl/generate_tickets_data.py
"""

from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd
from faker import Faker

from comun import DIR_RAW, config, configurar_log
from reloj_sla import MIN_DIA, Reloj24x7, RelojLaboral

log = configurar_log("generate_tickets_data")

# ---------------------------------------------------------------------------------------------
# Constantes del negocio (Ficha §0.2, §0.3 y §2.2)
# ---------------------------------------------------------------------------------------------
SEED = 42
FECHA_INICIO = date.fromisoformat(config("FECHA_INICIO"))
FECHA_FIN = date.fromisoformat(config("FECHA_FIN"))
# Último año natural completo del período (2025): el período se alarga hasta el 2026-01-02 solo para
# cerrar el último sprint, y eso no debe mover las fechas de alta ni las vacaciones.
ULTIMO_ANIO_COMPLETO = FECHA_FIN.year if FECHA_FIN.month == 12 and FECHA_FIN.day == 31 else FECHA_FIN.year - 1

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
    ("Gold", 92.0, 95.0, "deficiente", -5.0), ("Gold", 88.0, 92.0, "deficiente", -10.0),
    ("Gold", 0.0, 88.0, "deficiente", -15.0),
    ("Silver", 95.0, 100.01, "bonus", 2.0), ("Silver", 90.0, 95.0, "neutro", 0.0),
    ("Silver", 85.0, 90.0, "deficiente", -5.0), ("Silver", 0.0, 85.0, "deficiente", -10.0),
    ("Bronze", 92.0, 100.01, "bonus", 1.0), ("Bronze", 0.0, 92.0, "neutro", 0.0),
]

# Vacaciones (correlación 6): 22 días laborables por agente y año, concentrados en verano.
DIAS_VACACIONES = 22
PROB_MES_VERANO = {7: 0.35, 8: 0.45, 6: 0.10, 9: 0.10}  # mes del bloque largo de verano
PROB_NAVIDAD = 0.6
PROB_BAJA_MEDICA = 0.15  # por agente y año

# Sprints: el SLA se mide y se factura por sprint. Duran 3 semanas (lunes a viernes de la 3ª) y van
# seguidos desde FECHA_INICIO. El fin de semana tras un sprint ya cuenta para el siguiente. Se numeran
# por el año en que empiezan (2024-01, 2024-02…): el último de un año puede acabar en enero del
# siguiente, y la numeración vuelve a 01 con el primer sprint que empieza en el año nuevo.
SPRINT_DIAS = 21

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

    df["sprint_id"] = df["fecha"].map(sprint_de_fecha)
    return df


def _sprints() -> list[tuple[str, date, date]]:
    """(sprint_id, lunes de inicio, viernes de fin) de todos los sprints que tocan el período."""
    assert FECHA_INICIO.weekday() == 0, "FECHA_INICIO tiene que ser lunes: ahí empieza el 1er sprint"
    sprints, lunes, anio, n = [], FECHA_INICIO, None, 0
    while lunes <= FECHA_FIN:
        n = n + 1 if lunes.year == anio else 1
        anio = lunes.year
        sprints.append((f"{anio}-{n:02d}", lunes, lunes + timedelta(days=SPRINT_DIAS - 3)))
        lunes += timedelta(days=SPRINT_DIAS)
    return sprints


_SPRINTS = _sprints()


def sprint_de_fecha(fecha) -> str:
    """Sprint de un día. El sábado y el domingo tras el viernes de cierre van al sprint siguiente."""
    idx = ((fecha.date() if hasattr(fecha, "date") else fecha) - FECHA_INICIO).days + 2
    return _SPRINTS[idx // SPRINT_DIAS][0]


def build_dim_sprint(tiempo: pd.DataFrame) -> pd.DataFrame:
    df = pd.DataFrame(_SPRINTS, columns=["sprint_id", "fecha_inicio", "fecha_fin"])
    df["anio_sprint"] = df["sprint_id"].str[:4].astype(int)
    df["numero"] = df["sprint_id"].str[5:].astype(int)
    lab = tiempo[tiempo["es_laborable"]].groupby("sprint_id").size()
    df["dias_laborables"] = df["sprint_id"].map(lab).fillna(0).astype(int)
    # Completo = el período de datos cubre del lunes al viernes de cierre.
    df["es_completo"] = (df["fecha_inicio"] >= FECHA_INICIO) & (df["fecha_fin"] <= FECHA_FIN)
    return df[["sprint_id", "anio_sprint", "numero", "fecha_inicio", "fecha_fin",
               "dias_laborables", "es_completo"]]


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
                alta = fake.date_between(FECHA_INICIO, date(ULTIMO_ANIO_COMPLETO, 6, 30))
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
        # Las vacaciones se reparten por año natural: un año que el período solo cubre en parte
        # (2026: 1 y 2 de enero, para cerrar el último sprint) no tiene plan de vacaciones.
        if not (FECHA_INICIO <= date(anio, 1, 1) and date(anio, 12, 31) <= FECHA_FIN):
            continue
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
                # Cuota anual = mensual de referencia (redondeada a 500 €) × 12. Se factura por sprint:
                # cuota anual ÷ nº de sprints del año (Ficha §0.3).
                "cuota_anual_eur": int(round(rng.uniform(cuota_min, cuota_max) / 500) * 500) * 12,
                "n_usuarios": int(rng.integers(usu_min, usu_max + 1)),
                "fecha_alta": alta,
            })
    return pd.DataFrame(filas)


def build_dim_sla() -> pd.DataFrame:
    df = pd.DataFrame(POLITICAS_SLA, columns=["tipo", "prioridad", "objetivo_respuesta_min",
                                              "objetivo_resolucion_min", "reloj"])
    df.insert(0, "sla_id", df["tipo"].str[:3].str.upper() + "-" + df["prioridad"])
    # Solo incidencias y peticiones cuentan para el bonus/penalización de la factura (Ficha §0.3).
    df["computa_facturacion"] = df["tipo"].isin(["Incidencia", "Petición"])
    return df


def build_dim_tramo_ajuste() -> pd.DataFrame:
    df = pd.DataFrame(TRAMOS, columns=["nivel_contrato", "pct_desde", "pct_hasta", "tipo", "pct_ajuste"])
    df.insert(0, "tramo_id", range(1, len(df) + 1))
    return df


# ---------------------------------------------------------------------------------------------
# Tickets (Paso 3): llegadas, recorrido por departamentos, estados y medición por sprint
# ---------------------------------------------------------------------------------------------
TICKETS_OBJETIVO = 25_000
CORTE = datetime.combine(FECHA_FIN, time(18))  # fin del último sprint: lo que pasa después no se ve

# Parámetro 1 — mezcla tipo × prioridad: % del tipo y, dentro, % de cada prioridad.
MEZCLA = {
    "Incidencia": (0.55, {"P1": 0.03, "P2": 0.17, "P3": 0.50, "P4": 0.30}),
    "Petición": (0.35, {"P2": 0.15, "P3": 0.55, "P4": 0.30}),
    "Tarea": (0.10, {"P2": 0.20, "P3": 0.50, "P4": 0.30}),
}

# Llegadas. Los P2–P4 entran en días laborables; los P1, cualquier día y a cualquier hora.
PESO_HORA = {8: 4, 9: 13, 10: 15, 11: 13, 12: 11, 13: 8, 14: 7, 15: 9, 16: 9, 17: 7, 18: 4}
PESO_DIA_SEMANA = {1: 1.15, 2: 1.05, 3: 1.00, 4: 0.95, 5: 0.85}
PESO_MES = {8: 0.85, 12: 0.90}  # los clientes también se van de vacaciones, pero menos que el equipo
EXTRA_POST_FESTIVO = 1.40  # correlación 1: la cola que deja el festivo
# Correlación 2: en días de más de 35 °C entran incidencias extra que acaban en Infraestructura.
EXTRA_CALOR = {"P1": 0.15, "P2": 0.35}  # tickets extra esperados por día caluroso

# Parámetro 4 — escalados: nº de saltos (0, 1, 2, 3) y a qué departamento va cada salto.
PROB_SALTOS = [0.65, 0.25, 0.08, 0.02]
PRIMER_SALTO = {"Incidencia": {2: 0.50, 3: 0.35, 5: 0.15},
                "Petición": {5: 0.60, 3: 0.40},
                "Tarea": {3: 0.50, 4: 0.50}}
SIGUIENTE_SALTO = {2: {4: 0.75, 3: 0.25}, 3: {2: 0.50, 4: 0.30, 5: 0.20},
                   4: {2: 0.50, 3: 0.50}, 5: {3: 0.70, 2: 0.30}}

# Duraciones, en minutos de reloj de SLA: fracción del objetivo (mediana) × ruido lognormal × factores.
RESPUESTA_FRAC, RESPUESTA_SIGMA = 0.30, 0.70
TRABAJO_FRAC = {1: 0.30, 2: 0.27, 3: 0.25, 4: 0.36, 5: 0.27}  # Desarrollo, el más lento
# Solo el departamento que resuelve hace el trabajo completo: N1 hace el triaje antes de escalar y
# un departamento intermedio, el diagnóstico antes de pasarlo al siguiente.
TRIAJE_FRAC, DIAGNOSTICO_FRAC = 0.06, 0.10
TRABAJO_SIGMA = {1: 0.60, 2: 0.65, 3: 0.65, 4: 0.65, 5: 0.65}
COLA_FRAC = (0.04, 0.16)  # espera en la cola del nuevo departamento al reasignar (reloj corriendo)
FACTOR_NIVEL = {"Gold": 0.84, "Silver": 1.00, "Bronze": 1.10}  # correlación 5: Gold va primero
FACTOR_SENIORITY = {"senior": 0.90, "junior": 1.10}
ELASTICIDAD_CAPACIDAD = 0.8  # correlación 6: con menos agentes disponibles, todo va más lento
# Correlación 3: por encima del umbral de carga el tiempo crece de forma no lineal, con un tope (en
# los equipos pequeños, dos ausencias y un pico de entrada dispararían el factor sin límite).
SATURACION_UMBRAL, SATURACION_FUERZA, SATURACION_TOPE = 1.25, 0.6, 1.8
FACTOR_TOPE = 2.2  # tope de capacidad × saturación
FACTOR_POST_FESTIVO = 1.20  # el día post-festivo y el siguiente se trabaja con cola acumulada

# Parámetro 5 — pausas, cancelados y cierre.
PROB_PAUSA, PAUSA_MEDIANA, PAUSA_SIGMA = 0.30, 240, 1.1
PROB_PAUSA_P1, PAUSA_MEDIANA_P1 = 0.10, 45
PROB_CANCELADO = 0.03
DIAS_CIERRE = 3


def _elegir(pesos: dict):
    claves = list(pesos)
    p = np.array(list(pesos.values()), dtype=float)
    return claves[rng.choice(len(claves), p=p / p.sum())]


def build_llegadas(tiempo: pd.DataFrame, clima: pd.DataFrame, clientes: pd.DataFrame,
                   sla: pd.DataFrame) -> pd.DataFrame:
    """Una fila por ticket: cuándo entra, de qué cliente y con qué política de SLA."""
    celdas = {(t, p): wt * wp for t, (wt, ps) in MEZCLA.items() for p, wp in ps.items()}
    sla_id = {(r.tipo, r.prioridad): r.sla_id for r in sla.itertuples()}
    cuota_p1 = sum(w for (_, p), w in celdas.items() if p == "P1")
    resto = {k: w for k, w in celdas.items() if k[1] != "P1"}

    # El volumen de cada día es proporcional a los usuarios de los clientes ya dados de alta.
    altas = pd.to_datetime(clientes["fecha_alta"]).dt.date
    usuarios = clientes["n_usuarios"].to_numpy()
    activos = {d.date(): (altas <= d.date()).to_numpy() for d in tiempo["fecha"]}
    usu_dia = tiempo["fecha"].map(lambda d: usuarios[activos[d.date()]].sum())

    lab = tiempo["es_laborable"]
    peso = (tiempo["dia_semana"].map(PESO_DIA_SEMANA).fillna(0) * tiempo["mes"].map(PESO_MES).fillna(1)
            * np.where(tiempo["es_post_festivo"], EXTRA_POST_FESTIVO, 1) * usu_dia * lab)
    lam_resto = peso / peso.sum() * TICKETS_OBJETIVO * (1 - cuota_p1)
    lam_p1 = usu_dia / usu_dia.sum() * TICKETS_OBJETIVO * cuota_p1
    caluroso = tiempo["fecha"].map(clima.set_index("fecha")["es_dia_caluroso"]).fillna(False)

    horas = np.array(list(PESO_HORA))
    p_hora = np.array(list(PESO_HORA.values()), dtype=float) / sum(PESO_HORA.values())
    filas = []

    def nuevos(dia, n, celda, horas_dia, calor=False):
        act = activos[dia]
        p_cli = np.where(act, usuarios, 0) / usuarios[act].sum()
        for _ in range(n):
            tipo, prio = celda() if callable(celda) else celda
            h, m = horas_dia(), int(rng.integers(0, 60))
            filas.append({"creacion": datetime.combine(dia, time(h, m)),
                          "cliente_id": clientes["cliente_id"].iat[rng.choice(len(usuarios), p=p_cli)],
                          "sla_id": sla_id[(tipo, prio)], "tipo": tipo, "prioridad": prio, "calor": calor})

    claves_resto = list(resto)
    p_resto = np.array(list(resto.values())) / sum(resto.values())
    celda_resto = lambda: claves_resto[rng.choice(len(claves_resto), p=p_resto)]  # noqa: E731
    hora_lab = lambda: int(rng.choice(horas, p=p_hora))  # noqa: E731
    hora_24 = lambda: int(rng.integers(0, 24))  # noqa: E731

    for i, d in enumerate(tiempo["fecha"].dt.date):
        nuevos(d, rng.poisson(lam_resto.iat[i]), celda_resto, hora_lab)
        nuevos(d, rng.poisson(lam_p1.iat[i]), ("Incidencia", "P1"), hora_24)
        if caluroso.iat[i]:
            nuevos(d, rng.poisson(EXTRA_CALOR["P1"]), ("Incidencia", "P1"), hora_24, calor=True)
            if lab.iat[i]:
                nuevos(d, rng.poisson(EXTRA_CALOR["P2"]), ("Incidencia", "P2"), hora_lab, calor=True)

    df = pd.DataFrame(filas)
    df = df[df["creacion"] < CORTE].sort_values("creacion", kind="stable").reset_index(drop=True)
    df.insert(0, "ticket_id", [f"TCK-{i:06d}" for i in range(1, len(df) + 1)])
    return df


def build_rutas(llegadas: pd.DataFrame) -> list[list[int]]:
    """Departamentos por los que pasa cada ticket. Todo entra por Service Desk N1 (id 1)."""
    rutas = []
    for t in llegadas.itertuples():
        if t.calor:  # las incidencias del calor acaban en Infraestructura
            rutas.append([1, 3])
            continue
        ruta = [1]
        saltos = int(rng.choice(len(PROB_SALTOS), p=PROB_SALTOS))
        if saltos:
            ruta.append(_elegir(PRIMER_SALTO[t.tipo]))
        for _ in range(saltos - 1):
            opciones = {d: p for d, p in SIGUIENTE_SALTO[ruta[-1]].items() if d not in ruta[-2:]}
            if not opciones:
                break
            ruta.append(_elegir(opciones))
        rutas.append(ruta)
    return rutas


class Plantilla:
    """Agentes disponibles por día y departamento, capacidad y saturación (correlaciones 3 y 6)."""

    def __init__(self, agentes, ausencias, tiempo, llegadas, rutas):
        self.agentes = agentes
        self.seniority = agentes.set_index("agente_id")["seniority"].to_dict()
        self.ausentes: dict = {}
        for a in ausencias.itertuples():
            for d in pd.bdate_range(a.fecha_inicio, a.fecha_fin).date:
                self.ausentes.setdefault(d, set()).add(a.agente_id)
        self._cache: dict = {}

        # Saturación: tickets que pasan por el departamento en los últimos 5 días por agente
        # disponible, comparado con lo normal en ese departamento.
        dias = tiempo["fecha"].dt.date
        conteo = pd.DataFrame(0, index=dias, columns=range(1, 6))
        for t, ruta in zip(llegadas["creacion"], rutas):
            for dep in set(ruta):
                conteo.at[t.date(), dep] += 1
        carga = conteo.rolling(5, min_periods=1).sum()
        for dep in carga.columns:
            carga[dep] = [carga.at[d, dep] / len(self.disponibles(d, dep)) for d in dias]
        normal = carga[tiempo["es_laborable"].to_numpy()].median()
        x = carga / normal
        self.saturacion = (1 + SATURACION_FUERZA * (x - SATURACION_UMBRAL).clip(lower=0) ** 1.5)             .clip(upper=SATURACION_TOPE)

    def disponibles(self, dia: date, dep: int) -> list[str]:
        if (dia, dep) not in self._cache:
            activos = self.agentes[(self.agentes["departamento_id"] == dep)
                                   & (self.agentes["fecha_alta"] <= dia)]["agente_id"].tolist()
            libres = [a for a in activos if a not in self.ausentes.get(dia, set())]
            self._cache[(dia, dep)] = (libres or activos, len(activos))
        return self._cache[(dia, dep)][0]

    def factor(self, dia: date, dep: int) -> float:
        libres = self.disponibles(dia, dep)
        capacidad = (self._cache[(dia, dep)][1] / len(libres)) ** ELASTICIDAD_CAPACIDAD
        sat = self.saturacion.at[dia, dep] if dia in self.saturacion.index else 1.0
        return min(capacidad * sat, FACTOR_TOPE)

    def agente(self, dia: date, dep: int) -> tuple[str, str]:
        libres = self.disponibles(dia, dep)
        ag = libres[int(rng.integers(0, len(libres)))]
        return ag, self.seniority[ag]


def simular_ticket(t, ruta, nivel, pol, plantilla, relojes, post_festivo) -> list[list]:
    """Plan completo de estados del ticket: [estado, departamento, agente, minutos de reloj, pausa]."""
    dia = t.creacion.date()
    R, T = pol.objetivo_respuesta_min, pol.objetivo_resolucion_min
    k = FACTOR_NIVEL[nivel] * (FACTOR_POST_FESTIVO if dia in post_festivo else 1)
    lognormal = lambda s: float(rng.lognormal(0, s))  # noqa: E731

    r = R * RESPUESTA_FRAC * lognormal(RESPUESTA_SIGMA) * k * plantilla.factor(dia, 1)
    estados = [["Abierto", 1, None, max(1, round(r)), False]]
    for i, dep in enumerate(ruta):
        f = plantilla.factor(dia, dep) * k
        if i > 0:
            estados.append(["Abierto", dep, None, max(1, round(T * rng.uniform(*COLA_FRAC) * f)), False])
        ag, sen = plantilla.agente(dia, dep)
        if i == len(ruta) - 1:
            frac = TRABAJO_FRAC[dep]
        else:
            frac = TRIAJE_FRAC if i == 0 else DIAGNOSTICO_FRAC
        w = T * frac * lognormal(TRABAJO_SIGMA[dep]) * f * FACTOR_SENIORITY[sen]
        estados.append(["En curso", dep, ag, max(1, round(w)), False])

    # Pausas "Esperando al cliente": parten un tramo "En curso" en dos.
    es_p1 = pol.reloj == "24x7"
    if rng.random() < (PROB_PAUSA_P1 if es_p1 else PROB_PAUSA):
        for _ in range(1 if rng.random() < 0.8 else 2):
            idx = [i for i, e in enumerate(estados) if e[0] == "En curso" and e[3] >= 2]
            if not idx:
                break
            i = idx[int(rng.integers(0, len(idx)))]
            est, dep, ag, w, _ = estados[i]
            a = max(1, int(w * rng.uniform(0.2, 0.8)))
            pausa = max(5, round((PAUSA_MEDIANA_P1 if es_p1 else PAUSA_MEDIANA) * lognormal(PAUSA_SIGMA)))
            estados[i:i + 1] = [[est, dep, ag, a, False], ["Esperando al cliente", dep, ag, pausa, True],
                                [est, dep, ag, w - a, False]]

    if rng.random() < PROB_CANCELADO:  # se cancela en algún punto del camino
        i = int(rng.integers(0, len(estados)))
        estados[i][3] = max(1, int(estados[i][3] * rng.uniform(0.1, 0.9)))
        dep, ag = estados[i][1], estados[i][2]
        return estados[:i + 1] + [["Cancelado", dep, ag, None, False]]
    dep, ag = estados[-1][1], estados[-1][2]
    return estados + [["Resuelto", dep, ag, None, False], ["Cerrado", dep, ag, None, False]]


def build_tickets(llegadas, rutas, clientes, sla, plantilla, tiempo) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Recorre el plan de cada ticket con su reloj, corta en CORTE y mide el SLA por sprint."""
    laborables = set(tiempo.loc[tiempo["es_laborable"], "fecha"].dt.date)
    # Margen tras el corte (laborable = L–V) para que los tickets abiertos puedan "seguir" en el plan.
    margen = FECHA_FIN + timedelta(days=400)
    laborables |= {d for d in pd.bdate_range(FECHA_FIN + timedelta(days=1), margen).date}
    relojes = {"laboral": RelojLaboral(laborables, FECHA_INICIO, margen), "24x7": Reloj24x7(FECHA_INICIO)}
    lab = relojes["laboral"]
    pos_festivo = tiempo.loc[tiempo["es_post_festivo"], "fecha"].dt.date
    lab_ord = sorted(d for d in laborables if d <= FECHA_FIN)
    siguiente = {d: lab_ord[i + 1] for i, d in enumerate(lab_ord[:-1])}
    post_festivo = set(pos_festivo) | {siguiente[d] for d in pos_festivo if d in siguiente}

    nivel = clientes.set_index("cliente_id")["nivel_contrato"].to_dict()
    politicas = {r.sla_id: r for r in sla.itertuples()}
    tickets, historial = [], []

    for t, ruta in zip(llegadas.itertuples(), rutas):
        pol = politicas[t.sla_id]
        reloj = relojes[pol.reloj]
        T = pol.objetivo_resolucion_min
        plan = simular_ticket(t, ruta, nivel[t.cliente_id], pol, plantilla, relojes, post_festivo)

        # Recorrido en el tiempo real: cada estado empieza donde acabó el anterior.
        p, inicio, consumido, p_venc = reloj.pos(t.creacion), t.creacion, 0, None
        filas = []
        for estado, dep, ag, minutos, pausa in plan:
            if estado == "Resuelto":
                fin = lab.sumar(inicio, DIAS_CIERRE * MIN_DIA)  # cierre automático, en días laborables
            elif minutos is None:
                fin = None
            else:
                if not pausa:
                    if p_venc is None and consumido + minutos > T:
                        p_venc = p + (T - consumido)
                    consumido += minutos
                p += minutos
                fin = max(inicio, reloj.instante(p))
            filas.append([estado, dep, ag, inicio, fin, pausa, minutos, p - (minutos or 0) if minutos else None])
            if fin is not None:
                inicio = fin

        # Corte: lo que empieza después de CORTE no existe; el estado en curso queda sin fin.
        filas = [f for f in filas if f[3] < CORTE]
        if filas[-1][4] is None or filas[-1][4] > CORTE:
            filas[-1][4] = None
        actual = filas[-1]
        momento = {f[0]: f[3] for f in filas}  # inicio de cada estado (el último que aparezca)
        f_respuesta = filas[0][4]
        f_resolucion, f_cierre, f_cancel = momento.get("Resuelto"), momento.get("Cerrado"), momento.get("Cancelado")
        f_venc = reloj.instante(p_venc) if p_venc is not None else None

        # Minutos de SLA consumidos (sin pausas) hasta la resolución o, si sigue abierto, hasta el corte.
        p_corte = reloj.pos(CORTE)
        min_resol = sum(min(f[7] + f[6], p_corte) - f[7] for f in filas
                        if f[6] is not None and not f[5])
        min_pausa = sum(min(f[7] + f[6], p_corte) - f[7] for f in filas if f[6] is not None and f[5])

        if f_cancel is not None:
            estado_sla = "cancelado"
        elif f_resolucion is not None:
            estado_sla = "cumplido" if f_venc is None else "incumplido"
        else:
            estado_sla = "incumplido" if f_venc is not None and f_venc <= CORTE else "en curso"

        if estado_sla == "cumplido":
            sprint_medicion = sprint_de_fecha(f_resolucion.date())
        elif estado_sla == "incumplido":
            sprint_medicion = sprint_de_fecha(f_venc.date())
        else:
            sprint_medicion = None

        agentes_vistos = [f[2] for f in filas if f[2] is not None]
        tickets.append({
            "ticket_id": t.ticket_id, "cliente_id": t.cliente_id, "sla_id": t.sla_id,
            "departamento_id": actual[1], "agente_id": agentes_vistos[-1] if agentes_vistos else None,
            "fecha_creacion": t.creacion,
            "fecha_primera_respuesta": f_respuesta,
            "fecha_resolucion": f_resolucion, "fecha_cierre": f_cierre, "fecha_cancelacion": f_cancel,
            "fecha_incumplimiento": f_venc if estado_sla == "incumplido" else None,
            "estado_actual": actual[0], "estado_sla": estado_sla,
            "n_reasignaciones": sum(1 for f in filas if f[0] == "Abierto") - 1,
            "min_respuesta_sla": plan[0][3] if f_respuesta is not None else None,
            "min_resolucion_sla": min_resol if estado_sla != "cancelado" else None,
            "min_pausa": min_pausa,
            "cumple_respuesta": (plan[0][3] <= pol.objetivo_respuesta_min) if f_respuesta is not None else None,
            "cumple_resolucion": {"cumplido": True, "incumplido": False}.get(estado_sla),
            "computa_facturacion": bool(pol.computa_facturacion) and estado_sla in ("cumplido", "incumplido"),
            "sprint_apertura": sprint_de_fecha(t.creacion.date()),
            "sprint_medicion": sprint_medicion,
        })
        for n, (estado, dep, ag, ini, fin, pausa, minutos, _) in enumerate(filas, start=1):
            historial.append({"ticket_id": t.ticket_id, "secuencia": n, "estado": estado,
                              "departamento_id": dep, "agente_id": ag, "inicio": ini, "fin": fin,
                              "pausa_reloj": pausa})

    tickets, historial = pd.DataFrame(tickets), pd.DataFrame(historial)
    for col in [c for c in tickets.columns if c.startswith("fecha_")]:
        tickets[col] = pd.to_datetime(tickets[col])
    for col in ["inicio", "fin"]:
        historial[col] = pd.to_datetime(historial[col])
    for col in ["min_respuesta_sla", "min_resolucion_sla"]:
        tickets[col] = tickets[col].astype("Int64")
    return tickets, historial


def resumen_tickets(tk, historial, clientes, sla, tramos, tiempo, clima, rutas) -> None:
    """Comprobaciones: los 5 parámetros y las 6 correlaciones tienen que verse en los datos."""
    pct = lambda s: f"{s.mean() * 100:.1f} %"  # noqa: E731
    tk = tk.merge(clientes[["cliente_id", "nivel_contrato", "cuota_anual_eur"]], on="cliente_id") \
           .merge(sla[["sla_id", "tipo", "prioridad"]], on="sla_id")
    log.info(f"Tickets: {len(tk):,} · historial: {len(historial):,} filas".replace(",", "."))
    log.info("Tipo: " + " · ".join(f"{k} {v:.1%}" for k, v in tk["tipo"].value_counts(normalize=True).items())
             + f" · P1: {(tk['prioridad'] == 'P1').sum()}")
    log.info("Estado del SLA: " + str(tk["estado_sla"].value_counts().to_dict())
             + f" · con pausa: {pct(tk['min_pausa'] > 0)}")
    log.info("Estado al corte: " + str(tk["estado_actual"].value_counts().to_dict()))

    medidos = tk[tk["estado_sla"].isin(["cumplido", "incumplido"])]
    comp = medidos[medidos["computa_facturacion"]]
    log.info("Cumplimiento de resolución (computables) por nivel: "
             + " · ".join(f"{n} {v:.1%}" for n, v in comp.groupby("nivel_contrato")["cumple_resolucion"].mean().items()))
    log.info(f"Cumplimiento de 1ª respuesta: {pct(tk['cumple_respuesta'].dropna().astype(bool))}")
    esc = medidos.assign(escalado=medidos["n_reasignaciones"] > 0).groupby("escalado")["cumple_resolucion"].mean()
    log.info(f"Incumplimiento sin escalar {1 - esc[False]:.1%} vs escalados {1 - esc[True]:.1%} "
             f"(x{(1 - esc[True]) / (1 - esc[False]):.1f}) · saltos: "
             + str(pd.Series([len(r) - 1 for r in rutas]).value_counts(normalize=True).sort_index().round(3).to_dict()))
    log.info("Cumplimiento por departamento que resuelve: "
             + " · ".join(f"{d}: {v:.1%}" for d, v in medidos.groupby("departamento_id")["cumple_resolucion"].mean().items()))
    mes = medidos["fecha_creacion"].dt.month
    log.info(f"Cumplimiento julio-agosto {pct(medidos.loc[mes.isin([7, 8]), 'cumple_resolucion'].astype(bool))} "
             f"vs resto {pct(medidos.loc[~mes.isin([7, 8]), 'cumple_resolucion'].astype(bool))}")

    por_dia = tk.groupby(tk["fecha_creacion"].dt.normalize()).size()
    t = tiempo.set_index("fecha")
    lab = t[t["es_laborable"]].assign(n=por_dia).fillna({"n": 0})
    log.info(f"Tickets por laborable: post-festivo {lab.loc[lab['es_post_festivo'], 'n'].mean():.0f} vs "
             f"normal {lab.loc[~lab['es_post_festivo'], 'n'].mean():.0f}")
    infra = tk[(tk["departamento_id"] == 3) & tk["prioridad"].isin(["P1", "P2"]) & (tk["tipo"] == "Incidencia")]
    infra_dia = infra.groupby(infra["fecha_creacion"].dt.normalize()).size()
    verano = clima[clima["fecha"].dt.month.isin([6, 7, 8])].set_index("fecha").assign(n=infra_dia).fillna({"n": 0})
    log.info(f"Incidencias P1/P2 de Infraestructura por día en verano: >35 °C "
             f"{verano.loc[verano['es_dia_caluroso'], 'n'].mean():.2f} vs resto {verano.loc[~verano['es_dia_caluroso'], 'n'].mean():.2f}")

    # Facturación por sprint (la versión oficial se calculará en SQL, Fase 2): ensayo para calibrar.
    n_sprints = pd.Series([s[0][:4] for s in _SPRINTS]).value_counts()
    fs = comp.groupby(["cliente_id", "nivel_contrato", "cuota_anual_eur", "sprint_medicion"]).agg(
        n=("cumple_resolucion", "size"), ok=("cumple_resolucion", "sum")).reset_index()
    fs["pct"] = fs["ok"] / fs["n"] * 100
    fs["anio"] = fs["sprint_medicion"].str[:4]
    fs["cuota_sprint"] = fs["cuota_anual_eur"] / fs["anio"].map(n_sprints)

    def tramo(r):
        m = tramos[(tramos["nivel_contrato"] == r.nivel_contrato) & (tramos["pct_desde"] <= r.pct)
                   & (r.pct < tramos["pct_hasta"])].iloc[0]
        return pd.Series({"tipo": m["tipo"], "ajuste": r.cuota_sprint * m["pct_ajuste"] / 100})
    fs[["tipo", "ajuste"]] = fs.apply(tramo, axis=1)
    log.info("Tramos por nivel (cliente × sprint): " + str(
        fs.groupby("nivel_contrato")["tipo"].value_counts(normalize=True).round(2).unstack(fill_value=0).to_dict("index")))
    bal = fs.groupby(["anio", "nivel_contrato"])["ajuste"].sum().round(0).unstack()
    log.info("Balance bonus − penalización (€) por año y nivel: " + str(bal.to_dict("index"))
             + " · total por año: " + str(bal.sum(axis=1).round(0).to_dict()))


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
    formato = "%Y-%m-%d %H:%M" if nombre.startswith("fact_") else "%Y-%m-%d"  # los hechos llevan hora
    df.to_csv(DIR_RAW / f"{nombre}.csv", index=False, date_format=formato)
    log.info(f"  {nombre}.csv: {len(df):,} filas".replace(",", "."))


def main() -> None:
    log.info(f"Generando dimensiones (SEED={SEED}) entre {FECHA_INICIO} y {FECHA_FIN}")
    DIR_RAW.mkdir(parents=True, exist_ok=True)

    tiempo = build_dim_tiempo()
    sprints = build_dim_sprint(tiempo)
    departamentos = build_dim_departamento()
    agentes = build_dim_agente()
    ausencias = build_agente_ausencia(agentes, tiempo)
    clientes = build_dim_cliente()
    sla = build_dim_sla()
    tramos = build_dim_tramo_ajuste()

    for df, nombre in [(tiempo, "dim_tiempo"), (sprints, "dim_sprint"), (departamentos, "dim_departamento"),
                       (agentes, "dim_agente"), (ausencias, "agente_ausencia"),
                       (clientes, "dim_cliente"), (sla, "dim_sla"), (tramos, "dim_tramo_ajuste")]:
        guardar(df, nombre)

    log.info(f"Calendario: {tiempo['es_laborable'].sum()} laborables, "
             f"{tiempo['es_post_festivo'].sum()} post-festivo, {tiempo['es_puente'].sum()} puentes")
    incompletos = sprints.loc[~sprints["es_completo"], "sprint_id"].tolist()
    log.info(f"Sprints: {len(sprints)} ({sprints['anio_sprint'].value_counts().sort_index().to_dict()}) · "
             f"{sprints['dias_laborables'].min()}–{sprints['dias_laborables'].max()} laborables · "
             f"incompletos: {incompletos or 'ninguno'}")
    log.info(f"Clientes por nivel: {clientes['nivel_contrato'].value_counts().to_dict()} · "
             f"altas en el período: {(clientes['fecha_alta'] >= FECHA_INICIO).sum()}")
    log.info(f"Agentes: {len(agentes)} · altas en el período: {(agentes['fecha_alta'] >= FECHA_INICIO).sum()}")
    cap = capacidad_mensual(agentes, ausencias, tiempo)
    log.info("% medio de agentes ausentes por mes: "
             + " · ".join(f"{m}:{v}%" for m, v in cap.items()))

    log.info(f"Generando tickets (corte {CORTE:%Y-%m-%d %H:%M})")
    clima = pd.read_csv(DIR_RAW / "clima_madrid.csv", parse_dates=["fecha"])
    llegadas = build_llegadas(tiempo, clima, clientes, sla)
    rutas = build_rutas(llegadas)
    plantilla = Plantilla(agentes, ausencias, tiempo, llegadas, rutas)
    tickets, historial = build_tickets(llegadas, rutas, clientes, sla, plantilla, tiempo)
    guardar(tickets, "fact_ticket")
    guardar(historial, "fact_ticket_estado")
    resumen_tickets(tickets, historial, clientes, sla, tramos, tiempo, clima, rutas)


if __name__ == "__main__":
    main()
