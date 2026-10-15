# Setup — Brújula Soporte IT · Service Desk SLA Analytics

Cómo se instaló y verificó el entorno (Fase 0.5), comando por comando, para poder repetirlo en otra
máquina. Instalado el 2026-10-15 en **Windows 11 Enterprise** (portátil corporativo, usuario en el
grupo de Administradores).

## 1. Qué se instaló

| Herramienta | Versión | Cómo | Notas |
|---|---|---|---|
| Python | 3.12.10 | `winget install -e --id Python.Python.3.12` | Convive con un 3.14 previo. Se usa 3.12 porque Prophet necesita una versión con soporte maduro |
| PostgreSQL | 16.15 | `winget install -e --id PostgreSQL.PostgreSQL.16 --interactive` | Instalador oficial (EDB). Componentes: Server + pgAdmin 4 + Command Line Tools. Puerto 5432 |
| pgAdmin 4 | (incluido) | Con PostgreSQL | Cliente SQL gráfico |
| Git | 2.55 | Ya instalado | |
| VS Code | 1.141 | Ya instalado | Extensiones Python, Pylance y Jupyter |
| Power BI Desktop | — | Ya instalado | |
| Docker | — | **No se usa** | Decisión: no instalar Docker en el equipo corporativo |

## 2. Entorno virtual y librerías

Desde la raíz del proyecto:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

En VS Code: `Ctrl + Shift + P` → **Python: Select Interpreter** → `.venv`. Las terminales nuevas se
activan solas (aparece `(.venv)` en el prompt).

## 3. Base de datos

El proyecto **no** usa el superusuario `postgres`, sino un usuario propio dueño de su base:

```powershell
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -h localhost
```

```sql
CREATE ROLE analista LOGIN;
\password analista
CREATE DATABASE servicedesk_sla OWNER analista ENCODING 'UTF8';
\q
```

`\password` pide la contraseña sin mostrarla y sin dejarla en el historial de psql.

## 4. Variables de entorno

```powershell
Copy-Item .env.example .env
code .env      # completar DB_PASSWORD con la contraseña de analista
```

`.env` está en `.gitignore`: nunca se sube. `.env.example` sí, sin valores secretos.

## 5. Git

```powershell
git config --global user.name  "Rosmary González"
git config --global user.email "<id>+<usuario>@users.noreply.github.com"
```

Se usa la dirección **noreply** de GitHub para no publicar el correo personal en el historial.

## 6. Checkpoint

```powershell
python 00_setup\verificar_entorno.py
```

Resultado el 2026-10-15: **9/9 en verde — ENTORNO LISTO.**

## 7. Problemas encontrados y cómo se resolvieron

| Problema | Causa | Solución |
|---|---|---|
| Ya había un **PostgreSQL 18** (servicio detenido) también en el puerto 5432 | Instalación previa, no usada | `Set-Service postgresql-x64-18 -StartupType Manual` (PowerShell como administrador) para que no compita por el puerto al reiniciar |
| En PowerShell 5.1, `Invoke-RestMethod ... \| Select-Object` daba una tabla vacía | PS 5.1 entrega el array JSON como un solo objeto | Enumerarlo con `ForEach-Object { $_ }`. En Python no ocurre |
| `\password` → "Las contraseñas no coinciden" | La contraseña no se ve al escribirla | Pegarla dos veces con clic derecho |
| psql: error de sintaxis al crear el rol | Se pegó texto de más y el búfer quedó a medias (prompt `postgres-#`) | `\r` limpia el búfer; ejecutar cada comando solo cuando el prompt es `postgres=#` |
| Tildes rotas en la salida del script ("GonzÃ¡lez") | Windows leía la salida de git como cp1252 | `encoding="utf-8"` en `subprocess.run` |
| Aviso "Importing plotly failed" al importar Prophet | Prophet usa plotly solo para gráficos interactivos | Inofensivo: los gráficos se hacen con matplotlib |
| La carpeta del proyecto estaba en OneDrive | `.venv` y datos generan miles de archivos que sincronizar | Proyecto movido a `C:\Proyectos\` ; el respaldo es GitHub |
