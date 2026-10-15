"""
verificar_entorno.py — Checkpoint de la Fase 0.5 (Brújula Soporte IT · Service Desk SLA Analytics).

Comprueba, de una sola vez, que todo lo que necesita el proyecto está instalado, conectado y
probado antes de escribir la primera línea del ETL. Imprime una fila por chequeo y termina con
código de salida 1 si algo falla, para que no haya dudas sobre si se puede avanzar.

Uso (con el .venv activado, desde la raíz del proyecto):
    python 00_setup/verificar_entorno.py
"""

import importlib
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PYTHON_MINIMO = (3, 11)

# El nombre con que se instala una librería no siempre coincide con el nombre con que se importa.
NOMBRE_IMPORT = {
    "faker": "faker",
    "python-dotenv": "dotenv",
    "sqlalchemy": "sqlalchemy",
    "psycopg2-binary": "psycopg2",
    "scikit-learn": "sklearn",
    "jupyter": "notebook",
}

# Los mensajes llevan emojis; se fuerza UTF-8 para que no falle si la salida se redirige a archivo.
sys.stdout.reconfigure(encoding="utf-8")

(RAIZ / "logs").mkdir(exist_ok=True)
logging.basicConfig(
    filename=RAIZ / "logs" / "verificar_entorno.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    encoding="utf-8",
)

resultados: list[bool] = []


def informar(ok: bool, mensaje: str) -> None:
    """Imprime y registra el resultado de un chequeo."""
    print(f"  {'✅' if ok else '❌'} {mensaje}")
    logging.log(logging.INFO if ok else logging.ERROR, mensaje)
    resultados.append(ok)


def chequear_python() -> None:
    v = sys.version_info
    informar(v[:2] >= PYTHON_MINIMO, f"Python {v.major}.{v.minor}.{v.micro} (mínimo {PYTHON_MINIMO[0]}.{PYTHON_MINIMO[1]})")


def chequear_venv() -> None:
    # Dentro de un venv, sys.prefix apunta al .venv y sys.base_prefix al Python del sistema.
    activo = sys.prefix != sys.base_prefix
    nombre = Path(sys.prefix).name if activo else "ninguno"
    informar(activo, f"Entorno virtual activo ({nombre})" if activo
             else "Entorno virtual NO activo: ejecuta .venv\\Scripts\\Activate.ps1")


def chequear_librerias() -> None:
    lineas = (RAIZ / "requirements.txt").read_text(encoding="utf-8").splitlines()
    paquetes = [l.split("==")[0].strip() for l in lineas if l.strip() and not l.startswith("#")]
    fallidas = []
    for paquete in paquetes:
        modulo = NOMBRE_IMPORT.get(paquete.lower(), paquete.lower())
        try:
            importlib.import_module(modulo)
        except Exception:
            fallidas.append(paquete)
    ok = not fallidas
    informar(ok, f"{len(paquetes) - len(fallidas)}/{len(paquetes)} librerías instaladas"
             + ("" if ok else f" — faltan: {', '.join(fallidas)}"))


def leer_claves(archivo: Path) -> dict[str, str]:
    claves = {}
    for linea in archivo.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#") and "=" in linea:
            clave, valor = linea.split("=", 1)
            claves[clave.strip()] = valor.strip()
    return claves


def chequear_env() -> bool:
    env = RAIZ / ".env"
    if not env.exists():
        informar(False, ".env no existe: copia .env.example como .env y complétalo")
        return False
    esperadas = leer_claves(RAIZ / ".env.example")
    reales = leer_claves(env)
    # Solo se informa el NOMBRE de las claves que faltan, nunca sus valores.
    faltan = [c for c in esperadas if not reales.get(c)]
    informar(not faltan, f".env completo ({len(esperadas)} claves)" if not faltan
             else f".env incompleto — sin valor: {', '.join(faltan)}")
    return not faltan


def chequear_postgres() -> None:
    import os

    from dotenv import load_dotenv
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import URL

    load_dotenv(RAIZ / ".env")
    # URL.create escapa la contraseña: así no fallan contraseñas con @, : o /.
    url = URL.create(
        "postgresql+psycopg2",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME"),
    )
    try:
        motor = create_engine(url)
        with motor.connect() as conexion:
            version = conexion.execute(text("SHOW server_version")).scalar()
            usuario, base = conexion.execute(text("SELECT current_user, current_database()")).one()
        informar(True, f"PostgreSQL {version} — conexión OK como {usuario} a {base}")
    except Exception as e:
        informar(False, f"PostgreSQL — no conecta: {str(e).splitlines()[0]}")
        informar(False, "Permisos de escritura — no se pudo probar (sin conexión)")
        return

    # Tabla normal (no temporal): prueba que el usuario puede crear objetos en la base.
    try:
        with motor.begin() as conexion:
            conexion.execute(text("CREATE TABLE _verificacion_entorno (id int)"))
            conexion.execute(text("INSERT INTO _verificacion_entorno VALUES (1)"))
            conexion.execute(text("DROP TABLE _verificacion_entorno"))
        informar(True, "Permisos de escritura OK (crear, insertar y borrar una tabla)")
    except Exception as e:
        informar(False, f"Permisos de escritura — fallan: {str(e).splitlines()[0]}")


def chequear_apis() -> None:
    import os

    import requests
    from dotenv import load_dotenv

    load_dotenv(RAIZ / ".env")
    inicio, fin = os.getenv("FECHA_INICIO"), os.getenv("FECHA_FIN")

    # Clima: se pide el período completo y se exige un dato por día.
    try:
        r = requests.get(os.getenv("OPEN_METEO_URL"), timeout=30, params={
            "latitude": os.getenv("SEDE_LAT"), "longitude": os.getenv("SEDE_LON"),
            "start_date": inicio, "end_date": fin,
            "daily": "temperature_2m_max", "timezone": "Europe/Madrid",
        })
        r.raise_for_status()
        dias = len(r.json()["daily"]["time"])
        esperados = (datetime.fromisoformat(fin) - datetime.fromisoformat(inicio)).days + 1
        informar(dias == esperados, f"API Open-Meteo — {dias}/{esperados} días entre {inicio} y {fin}")
    except Exception as e:
        informar(False, f"API Open-Meteo — falla: {e}")

    # Festivos: se cuentan los que aplican a la sede (nacionales + comunidad de Madrid).
    try:
        comunidad = os.getenv("COMUNIDAD_ISO")
        conteos = []
        for anio in range(int(inicio[:4]), int(fin[:4]) + 1):
            r = requests.get(f"{os.getenv('NAGER_URL')}/{anio}/{os.getenv('PAIS_ISO2')}", timeout=30)
            r.raise_for_status()
            sede = [f for f in r.json() if not f["counties"] or comunidad in f["counties"]]
            conteos.append(f"{len(sede)} en {anio}")
        informar(all(int(c.split()[0]) > 0 for c in conteos),
                 f"API Nager.Date — festivos de {comunidad}: {', '.join(conteos)}")
    except Exception as e:
        informar(False, f"API Nager.Date — falla: {e}")


def chequear_git() -> None:
    def config(clave: str) -> str:
        try:
            # git devuelve UTF-8; sin indicarlo, Windows lo lee como cp1252 y rompe las tildes.
            return subprocess.run(["git", "config", "--global", clave],
                                  capture_output=True, text=True, encoding="utf-8").stdout.strip()
        except FileNotFoundError:
            return ""

    nombre, correo = config("user.name"), config("user.email")
    ok = bool(nombre and correo)
    informar(ok, f"Git configurado ({nombre})" if ok
             else "Git sin configurar: falta user.name o user.email")


def main() -> int:
    print("\nVerificación del entorno — Brújula Soporte IT\n")
    logging.info("Inicio de la verificación")
    chequear_python()
    chequear_venv()
    chequear_librerias()
    if chequear_env():
        chequear_postgres()
    else:
        informar(False, "PostgreSQL — no se prueba sin un .env completo")
        informar(False, "Permisos de escritura — no se prueban sin un .env completo")
    chequear_apis()
    chequear_git()

    correctos = sum(resultados)
    print(f"\n  {correctos}/{len(resultados)} chequeos en verde.")
    if all(resultados):
        print("  → ENTORNO LISTO. Puedes avanzar a la Fase 1.\n")
        logging.info("Entorno listo")
        return 0
    print("  → Hay que corregir lo marcado con ❌ antes de seguir.\n")
    logging.error("Entorno con fallos")
    return 1


if __name__ == "__main__":
    sys.exit(main())
