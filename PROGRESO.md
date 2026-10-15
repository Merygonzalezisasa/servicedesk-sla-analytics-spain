# Progreso — Brújula Soporte IT · Service Desk SLA Analytics

## Estado actual
**Fase:** 0.5 (Entorno) · **Paso:** 1 (diagnóstico) · **Última sesión:** 2026-10-15

## Bitácora
### Fase 0 — Decidir ✅ (2026-10-15)
- [x] Paso 0 — País: España (ES), moneda EUR, idioma español. Mercado: España + internacional.
      Prueba de la API de festivos (Nager.Date) OK desde la red corporativa: 32 festivos en 2025,
      12 aplican a Madrid. Faltan los locales → se complementan con un CSV manual (ver FICHA §0.1).
      Reglas del reloj de SLA: P1 24x7; P2–P4 L–V 09–18 sin festivos de Madrid.
      Pregunta de control respondida bien (1 h 30 min).
- [x] Paso 1 — Rubro: service desk B2B con SLA por contrato. Foco: cumplimiento de SLA.
      Justificación: experiencia diaria con Jira / Service Desk.
- [x] Paso 2 — Cruce (fuente interna + externa)
  - [x] Catálogo: 3 tipos (Incidencia, Petición, Tarea), matriz SLA tipo × prioridad,
        6 estados con pausa en "Esperando al cliente", 5 departamentos (FICHA §0.2).
  - [x] Clientes y contratos: Gold/Silver/Bronze, ~40 clientes (FICHA §0.3).
  - [x] Pregunta de control (pausa del reloj): 4 h + 3 h = 7 h de 18 h → cumple.
  - [x] 6 correlaciones intencionales (2 con fuente externa real), con la confusión entre calor y
        vacaciones documentada (FICHA §2.3).
  - [x] Período 2024–2025, ~25.000 tickets, ~40 clientes, ~35 agentes con vacaciones
        (dim_agente + agente_ausencia). Modelo dimensional esbozado (FICHA §2.2 y §3).
- [x] Paso 3 — Open-Meteo + Nager.Date aprobadas con los 4 chequeos. Verificado por la estudiante:
      731 días (2024-01-01 → 2025-12-31), 84 días > 35 °C. Respuesta cruda en FICHA §2.1.
      Pregunta de control (muestra pequeña): respondida a medias; matiz explicado (sin potencia
      estadística, un día atípico decide el resultado).
- [x] Paso 4 — 6 preguntas de negocio y 6 módulos (FICHA §4 y §5).
      Bonus/malus mensual en % de la factura por tramos → `fact_facturacion_mensual`
      (grano cliente × mes) y `dim_tramo_ajuste`. Bronze sin malus. % mensual sin ponderar
      (como en la empresa de la estudiante); el punto ciego de los P1 pasa a ser un análisis.
- [x] Paso 5 — Arquitectura (FICHA §6) y stack (§7). Pregunta de control (extract antes que
      generate): bien el reloj de SLA; se completó la parte de las correlaciones.
- [x] Paso 6 — Identidad: Rosmary González · Brújula Soporte IT ·
      repo `servicedesk-sla-analytics-spain`. Alcance y limitaciones en FICHA §8. **Ficha aprobada.**

### Fase 0.5 — Entorno 🚧
- [x] Paso 1 — Diagnóstico: Python 3.14.0, Git 2.55, VS Code 1.141, Power BI Desktop instalados.
      Faltan PostgreSQL y Docker. Usuario en el grupo Administradores; winget disponible.
      Decisión: **sin Docker** → instalador oficial PostgreSQL 16 (EDB) vía winget.
- [x] Paso 2 — PostgreSQL 16.15 + pgAdmin (`winget install -e --id PostgreSQL.PostgreSQL.16 --interactive`).
      Verificado: `psql (PostgreSQL) 16.15`, servicio `postgresql-x64-16` Running / Automatic, puerto 5432.
      Conflicto resuelto: había un PostgreSQL 18 previo (2026-08-28) también en el 5432 → la
      estudiante lo pasó a inicio **Manual** (`Set-Service postgresql-x64-18 -StartupType Manual`).
- [x] Paso 3 — Estructura, venv, requirements, .env
  - [x] Carpetas del Anexo B creadas (sin docker-compose: no se usa Docker), con `.gitkeep`.
  - [x] `.gitignore`, `.env.example`, `requirements.txt`.
  - [x] Python 3.12.10 instalado (`winget install -e --id Python.Python.3.12`), conviviendo con 3.14.
  - [x] `.venv` creado con `py -3.12 -m venv .venv` + `pip install -r requirements.txt`.
        Verificado: las 14 librerías importan y Prophet entrena un modelo de prueba.
        `requirements.txt` con versiones fijadas (pip freeze).
        Aviso inofensivo: "Importing plotly failed" (Prophet usa plotly solo para gráficos
        interactivos; usaremos matplotlib).
  - [x] Usuario `analista` (contraseña con `\password`) + base `servicedesk_sla` (owner analista).
        Incidencia: texto pegado de más en psql dejó el búfer a medias (`postgres-#`) → `\r` lo limpia.
  - [x] `.env` creado a partir de `.env.example` (DB_PASSWORD relleno, verificado sin leerlo).
  - [x] Pregunta de control (`.venv`): no la sabía → explicado de nuevo (aislar versiones por proyecto).
- [x] Paso 4 — `python 00_setup/verificar_entorno.py` → **9/9 en verde, ENTORNO LISTO**.
      Git: user.name "Rosmary González", user.email = dirección noreply de GitHub (privacidad).
      Arreglo: las tildes salían rotas (cp1252) → `encoding="utf-8"` en subprocess.
      Pregunta de control (¿por qué probar la API desde Python?): no la sabía → explicada
      (proxy, certificados y user-agent afectan a Python distinto que al navegador/PowerShell).
- [ ] Paso 5 — Repo en GitHub + primer commit · SETUP.md  ← ACÁ VOY
  - [x] SETUP.md (instalación + 7 problemas resueltos), README.md provisional, LICENSE (MIT).
  - [x] .gitignore verificado: .env, .venv, logs y hechos ignorados; la PLANTILLA no se publica
        (material de terceros).
  - [ ] Repo `Merygonzalezisasa/servicedesk-sla-analytics-spain` creado en la web (vacío).
  - [ ] git init + primer commit + push.

- [x] Proyecto movido fuera de OneDrive a `C:\Proyectos\servicedesk-sla-analytics-spain`
      (3 archivos, hash verificado). La estudiante tiene cuenta de GitHub.
- [x] Pregunta de control de la Fase 0 ("¿los datos son reales?"): respondida a medias ("no son
      reales"). Corregida: el negocio es sintético y declarado; el clima y los festivos son reales.

- [x] Pregunta de control del Paso 2 (¿por qué la contraseña va en `.env`?): bien respondida.
      Matiz añadido: el historial de git la conserva aunque se borre después.

## Dudas abiertas
- Tiempos concretos de la matriz SLA y de los tramos: abiertos a ajuste antes de la Fase 1.
- Fase 1: en PowerShell 5.1, `Invoke-RestMethod` entrega el array JSON como un solo objeto → hay que
  enumerarlo (`ForEach-Object`). En Python no pasa.

## Referencias
- Cómo calculan el SLA otros contratos (para business_case): pliego de la Junta de Andalucía
  (penalización = suma por indicador), ENSA Panamá (descuento sobre facturación mensual por
  prioridad), Sigma Tech (objetivo y rebate por prioridad).
