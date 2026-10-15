"""
comun.py — Utilidades compartidas por los scripts del ETL.

Centraliza lo que todos los scripts necesitan igual: rutas, configuración del .env, logging y
peticiones HTTP robustas. Así cada extractor solo contiene su lógica propia.
"""

import logging
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
DIR_RAW = RAIZ / "data" / "raw"
DIR_MANUAL = RAIZ / "data" / "manual"
DIR_LOGS = RAIZ / "logs"

load_dotenv(RAIZ / ".env")

# Algunas APIs rechazan peticiones sin user-agent; identificarse es además una cortesía.
CABECERAS = {"User-Agent": "servicedesk-sla-analytics-spain/1.0 (portfolio de análisis de datos)"}


def config(clave: str) -> str:
    """Lee una variable del .env y falla con un mensaje claro si no existe."""
    valor = os.getenv(clave)
    if not valor:
        raise RuntimeError(f"Falta la variable {clave} en el .env (ver .env.example)")
    return valor


def configurar_log(nombre: str) -> logging.Logger:
    """Logger que escribe en logs/<nombre>.log y en consola."""
    sys.stdout.reconfigure(encoding="utf-8")
    DIR_LOGS.mkdir(exist_ok=True)
    log = logging.getLogger(nombre)
    log.setLevel(logging.INFO)
    if not log.handlers:
        formato = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S")
        archivo = logging.FileHandler(DIR_LOGS / f"{nombre}.log", encoding="utf-8")
        consola = logging.StreamHandler(sys.stdout)
        for h in (archivo, consola):
            h.setFormatter(formato)
            log.addHandler(h)
    return log


def get_json(url: str, log: logging.Logger, params: dict | None = None,
             reintentos: int = 3, espera_s: float = 2.0):
    """
    GET con timeout y reintentos con espera creciente.

    Solo se reintentan los fallos transitorios (red, timeout, errores 5xx o 429): un 4xx
    indica una petición mal formada y repetirla no lo arregla.
    """
    for intento in range(1, reintentos + 1):
        try:
            r = requests.get(url, params=params, headers=CABECERAS, timeout=30)
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"HTTP {r.status_code}", response=r)
            r.raise_for_status()
            datos = r.json()
            if not datos:
                raise ValueError(f"Respuesta vacía de {url}")
            return datos
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
            transitorio = not isinstance(e, requests.HTTPError) or e.response is None \
                or e.response.status_code == 429 or e.response.status_code >= 500
            if not transitorio or intento == reintentos:
                log.error(f"Fallo definitivo en {url}: {e}")
                raise
            pausa = espera_s * 2 ** (intento - 1)
            log.warning(f"Intento {intento}/{reintentos} fallido ({e}); reintento en {pausa:.0f} s")
            time.sleep(pausa)
