# Progreso — Brújula Soporte IT · Service Desk SLA Analytics

## Estado actual
**Fase:** 2 (SQL) · **Paso:** 3 de 4 · **Última sesión:** 2026-10-16

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
      Bonus/penalización mensual en % de la factura por tramos → `fact_facturacion_mensual`
      (grano cliente × mes) y `dim_tramo_ajuste`. Bronze sin penalización. % mensual sin ponderar
      (como en la empresa de la estudiante); el punto ciego de los P1 pasa a ser un análisis.
- [x] Paso 5 — Arquitectura (FICHA §6) y stack (§7). Pregunta de control (extract antes que
      generate): bien el reloj de SLA; se completó la parte de las correlaciones.
- [x] Paso 6 — Identidad: Rosmary González · Brújula Soporte IT ·
      repo `servicedesk-sla-analytics-spain`. Alcance y limitaciones en FICHA §8. **Ficha aprobada.**

### Fase 0.5 — Entorno ✅ (2026-10-15)
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
- [x] Paso 5 — Repo en GitHub + primer commit · SETUP.md
  - [x] SETUP.md (instalación + 7 problemas resueltos), README.md provisional, LICENSE (MIT).
  - [x] .gitignore verificado: .env, .venv, logs y hechos ignorados; la PLANTILLA no se publica
        (material de terceros).
  - [x] Repo `Merygonzalezisasa/servicedesk-sla-analytics-spain` creado en la web (público, vacío).
  - [x] `git init -b main` + `git add .` → 14 archivos preparados; `.env`, `.venv` y la plantilla
        fuera (verificado con `git status`).
  - [x] Commit `fe84a24` + `git push -u origin main`. Verificado: 14 archivos en GitHub, sin `.env`.
  - Pregunta de control (¿por qué `git status` antes del commit?): no respondida → explicada.

### Fase 1 — ETL ✅ (2026-10-16)
- [x] Paso 1 — Extractores de las APIs
  - [x] `01_etl/comun.py`: rutas, .env, logging (logs/ + consola), GET con timeout y reintentos
        con espera creciente (solo fallos transitorios: red, timeout, 429, 5xx).
  - [x] `01_etl/extract_festivos.py` + `data/manual/festivos_madrid_correcciones.csv`
        → `data/raw/festivos_madrid.csv`: 30 festivos (15/año, 23 en día laborable).
        La API manda; el CSV manual solo añade: Santiago Apóstol 2024 y 2025 (verificado en los
        decretos de la Comunidad) y San Isidro + Almudena 2024 y 2025 (**pendientes de BOCM**).
  - [x] `01_etl/extract_clima.py` → `data/raw/clima_madrid.csv`: 731 días, 0 nulos,
        Tmax 4,4–40,7 °C, días > 35 °C: 41 (2024) y 43 (2025).
  - [x] Checkpoint: la estudiante corrió ambos scripts (12:54), mismo resultado → reproducible.
  - [x] Pregunta de control (ffill en temperatura, 0 en lluvia): respondida por relevancia de
        negocio; se explicó el motivo estadístico (la temperatura es continua y persistente; la
        lluvia es intermitente: 466 de 731 días sin lluvia).
  - [x] Commit `0332790` subido. (Incidencia: `git commit` sin mensaje abrió Vim → `:q!`;
        editor de git cambiado a VS Code con `core.editor "code --wait"`.)
- [x] Paso 2 — Generador: dimensiones (calendario, departamentos, agentes, vacaciones, clientes,
      SLA, tramos)
  - [x] `01_etl/generate_tickets_data.py` (SEED=42) → 7 CSV en data/raw: dim_tiempo (731; 500
        laborables, 19 post-festivo, 5 puentes), dim_departamento (5), dim_agente (35),
        agente_ausencia (405: 396 vacaciones + 9 bajas), dim_cliente (40; 7 altas en el período),
        dim_sla (10), dim_tramo_ajuste (11).
  - [x] Correlación 6 comprobada en los datos: agentes ausentes en agosto **32,3 %** (julio 19 %,
        diciembre 15 %, resto 2–6 %). Vacaciones: mediana 22 días laborables por agente y año.
  - [x] Reproducible: dos corridas → mismos hashes de los 7 CSV.
  - [x] Checkpoint de la estudiante (14:32): mismo resultado, agosto 32,3 % → reproducible en su
        ejecución.
  - [x] Pregunta de control (¿qué pasa sin SEED?): bien ("los datos serían aleatorios"); se añadió
        la consecuencia: los números del README no coincidirían con lo que obtiene quien lo clone.
  - [x] Commit `9126b28` subido.
- [x] Paso 3 — Tickets, historial de estados y cálculo del SLA
      Los 5 parámetros de negocio se validaron con la estudiante el 2026-10-16 (abajo).
  - [x] Parámetro 1 — Mezcla tipo × prioridad (validado 2026-10-16): Incidencia 55 % (P1 3 · P2 17 ·
        P3 50 · P4 30), Petición 35 % (P2 15 · P3 55 · P4 30), Tarea 10 % (P2 20 · P3 50 · P4 30).
        ≈ 413 P1 en 2 años (~1 cada 2 días); 90 % de los tickets computan en facturación.
  - [x] Parámetro 2 — Reparto del volumen entre clientes (validado): proporcional a n_usuarios
        (Gold ~77 tickets/mes, Silver ~23, Bronze ~6), sin mínimo; los clientes dados de alta en el
        período solo abren tickets desde su fecha_alta. La inestabilidad del % con pocos tickets
        (1 fallo = Bronze pierde el bonus) se deja a propósito como hallazgo.
  - [x] Cambio de nombre: en `dim_tramo_ajuste.tipo`, "malus" pasa a ser **"deficiente"**
        (bonus / neutro / deficiente). Regenerado: solo cambia ese CSV (los otros 8, mismo hash).
        Vocabulario unificado en todo el proyecto (FICHA, README, código): "malus" → **penalización**
        para el importe en € (p. ej. `v_pareto_penalizacion`) y **deficiente** para el tramo.
  - [x] **Medición por sprint** en lugar de por mes (FICHA §0.4): sprints de 3 semanas (lun → vie),
        `AAAA-NN` por año de inicio, fin de semana al sprint siguiente, regla de las dos fechas
        (✅ en el sprint de resolución, ❌ en el del vencimiento, abiertos en plazo = arrastre),
        cuota por sprint equivalente a la anual.
  - [x] Período ampliado a **2026-01-02** (FECHA_FIN en .env y .env.example) para cerrar el sprint
        2025-17. Festivos (aviso solo en años completos) y clima re-extraídos (733 días); vacaciones
        solo en años completos. Nueva `dim_sprint.csv` (35 sprints: 18 + 17, 12–15 laborables) y
        columna `sprint_id` en dim_tiempo. Reproducible (dos corridas, mismos hashes).
        Fallo detectado y corregido: las altas de agentes se sorteaban hasta junio de FECHA_FIN.year
        (ahora 2026) → `ULTIMO_ANIO_COMPLETO`. Con el arreglo, dim_agente y agente_ausencia son
        idénticos a los del commit 9126b28 (405 ausencias, agosto 32,3 %): el checkpoint sigue valiendo.
  - [x] Liquidación (opción A): tramo calculado en cada sprint, importes sumados y liquidados al
        cierre del año (el sprint cuenta en el año de su nombre). `dim_cliente.cuota_anual_eur`
        (= mensual de referencia × 12) sustituye a cuota_mensual_eur; cuota_sprint = anual ÷ nº de
        sprints del año (18 / 17). Modelo: `fact_facturacion_sprint` (cliente × sprint),
        `sp_calcular_facturacion_sprint`, vistas `v_cumplimiento_sprint` y `v_liquidacion_anual`.
  - [x] Parámetro 3 — Calibración del cumplimiento de resolución por sprint (validado): Gold ~94 %,
        Silver ~90 %, Bronze ~86 %; 1ª respuesta ~95 %. No se fija a mano: sale de las reglas
        (escalados, verano, festivos, saturación, prioridad Gold) ajustadas hasta acercarse.
        Balance anual esperado negativo, concentrado en Gold y Silver.
  - [x] Parámetro 4 — Escalados (validado): todo entra por N1; 65 % se resuelve en N1, 25 % 1 escalado,
        10 % 2+. Primer destino — Incidencia: N2 50 · Infra 35 · Seguridad 15; Petición: Seguridad 60 ·
        Infra 40; Tarea: Infra 50 · Desarrollo 50. Desarrollo casi siempre como 2º salto desde N2.
        Cada reasignación = 1–4 h lab. de cola con el reloj corriendo (→ ~3× incumplimiento).
        El ticket se atribuye al departamento que resuelve; el historial guarda el tiempo en cada uno.
        Calor > 35 °C: más P1/P2 de Infraestructura (entran por N1 y se escalan a Infra).
  - [x] Parámetro 5 — Pausas, cancelados, cierre y corte (validado): 30 % pasa por "Esperando al
        cliente" (mediana ~4 h lab., cola larga), pausa solo el reloj de resolución (no la 1ª
        respuesta); 3 % cancelados (fuera del % y de la factura); Resuelto → Cerrado automático a los
        3 días laborables, sin reaperturas; corte 2026-01-02 18:00: vencidos = ❌ en 2025-17,
        en plazo = "en curso" (backlog, fuera de la factura).
  - [x] `01_etl/reloj_sla.py`: reloj 24x7 y laboral (posición en minutos de reloj); autotest con el
        ejemplo de control de §0.1 (1 h 30 min) OK. No corrige el cambio de hora (declarado).
  - [x] Generador de tickets en `generate_tickets_data.py` → `fact_ticket.csv` (25.300) y
        `fact_ticket_estado.csv` (140.602). Plan por ticket en minutos de reloj → tiempo real → corte.
        Calibrado (2026-10-16): resolución Gold 94,3 % · Silver 90,2 % · Bronze 86,1 %; 1ª respuesta
        94,9 %; escalados x3,4; Desarrollo el peor (67 %); jul-ago 84,8 % vs resto 93,6 %; post-festivo
        68 vs 50 tickets/día; Infra P1/P2 en días > 35 °C 0,82 vs 0,43/día; 29 % con pausa; 712
        cancelados; backlog al corte 143 (124 en plazo + 19 vencidos). Tramos cliente × sprint: Gold
        43 % deficiente; balance −133.003 € (2024) y −154.034 € (2025).
        Ajustes de calibración: tope a la saturación (en equipos de 3–5 agentes se disparaba ×12) y
        solo el departamento que resuelve hace el trabajo completo (triaje en N1, diagnóstico en los
        intermedios). 11 comprobaciones de coherencia OK. Reproducible (mismos hashes en 2 corridas).
  - [x] Pregunta de control (TCK-000636 sin la pausa de 3 h 39 min, ¿cumple?): a medias. Bien el
        sprint de apertura (2024-01) vs medición (2024-02). Mal: dijo que sí cumpliría → explicado que
        la pausa no consume SLA: seguiría en 1.082 min (> 1.080), solo se resolvería antes en el
        calendario. La causa de un incumplimiento está en trabajo y colas, no en la espera del cliente.
  - [x] Checkpoint de la estudiante (14:07): resultados idénticos (25.300 tickets, Gold 94,3 %,
        agosto 32,3 %, balance −133.003 / −154.034 €) → reproducible en su ejecución.
  - [x] Commit `827d23a` subido (13 archivos; fact_*.csv y .env fuera, verificado con git status).
- [x] Paso 4 — Carga a PostgreSQL con upsert (`load_to_postgres.py`)
  - [x] `01_etl/load_to_postgres.py`: esquema `raw` (zona de aterrizaje; el modelo va en DB_SCHEMA en
        la Fase 2), 12 tablas con tipos y PK, COPY a tabla temporal + INSERT … ON CONFLICT DO UPDATE
        (solo si algo cambió), todo en una transacción (rollback si falla). Avisa de filas que ya no
        están en el CSV (no las borra). 167.940 filas.
  - [x] Pruebas: 1ª corrida = todo nuevo; 2ª = todo "sin cambios" (no duplica); tras cambiar a mano
        TCK-000636 y borrar TAR-P4 en la base → 1 actualizada + 1 nueva, base restaurada.
  - [x] Pregunta de control (¿upsert vs borrar y recargar?): bien en lo principal ("mientras se
        borra, quien consulte no ve datos"). Matiz: dentro de una transacción también se evita;
        añadido: carga incremental, no pierde historia, no rompe vistas dependientes, log de cambios.
  - [x] Checkpoint de la estudiante: 2ª corrida con todas las tablas "sin cambios" → upsert idempotente.
  - [x] Commit `676bb71` subido.
- [x] Paso 5 — Verificación de la carga (`verificar_carga.py`)
  - [x] `01_etl/verificar_carga.py`: 12 comprobaciones de integridad (claves ajenas, nulos, calendario
        ↔ sprints ↔ clima ↔ festivos) + 8 de reglas de negocio (catálogo de estados, P1 solo
        incidencias, orden de fechas, corte, historial encadenado, cumplido ↔ minutos, regla de las
        dos fechas, qué computa en la factura) + cifras de control SQL (base) vs pandas (CSV):
        filas, cumplimiento por nivel, estados del SLA, suma de minutos. Sale con código 1 si falla.
  - [x] Todo en verde. Prueba de sabotaje (TCK-000636 con cliente CLI-999 y "cumplido"): detectado
        por 3 vías; el upsert lo repara (1 actualizada) y vuelve a verde.
  - [x] Pregunta de control (¿para qué el sabotaje?): al principio no la entendió → reformulada con la
        alarma de humo. Respuesta bien: "para confirmar que el verificador está encendido". Matiz:
        y que cada comprobación detecta lo que dice detectar (probar que una prueba puede fallar).
  - [x] Checkpoint de la estudiante: termina con "CARGA VERIFICADA".
  - [x] Commit de cierre de la Fase 1: `cbfb674`.

- [x] Proyecto movido fuera de OneDrive a `C:\Proyectos\servicedesk-sla-analytics-spain`
      (3 archivos, hash verificado). La estudiante tiene cuenta de GitHub.
- [x] Pregunta de control de la Fase 0 ("¿los datos son reales?"): respondida a medias ("no son
      reales"). Corregida: el negocio es sintético y declarado; el clima y los festivos son reales.

- [x] Pregunta de control del Paso 2 (¿por qué la contraseña va en `.env`?): bien respondida.
      Matiz añadido: el historial de git la conserva aunque se borre después.

### Fase 2 — SQL 🚧
Plan (Parte 5 de la plantilla): 4 archivos en 02_sql/, uno por uno; la estudiante los ejecuta en su base.
Decisión: `raw` = zona de aterrizaje (acepta lo que traen los CSV); `servicedesk` = modelo con FKs y
CHECKs (la base rechaza lo que no cumple las reglas del negocio).
- [x] Paso 1 — `01_create_schema.sql`
  - [x] Esquema estrella `servicedesk`: 9 dimensiones/tablas puente + fact_ticket, fact_ticket_estado y
        fact_facturacion_sprint (vacía, la llena el SP). PKs, FKs, ~40 CHECKs (P1 solo incidencias,
        regla de las dos fechas, orden de fechas, tramos con signo correcto…), 15 índices, comentarios.
        dim_sprint.n_sprints_anio (18 / 17) para la cuota por sprint. Carga desde raw + ANALYZE.
  - [x] Probado: crea desde cero sin errores ni avisos; 0 filas distintas entre raw y el modelo.
  - [x] Explicado a petición de la estudiante: restricciones de dim_sprint (UNIQUE, CHECK de +18 días e
        isodow), COMMENT ON, fact_facturacion_sprint y el SP, índices (simples, compuestos, parcial),
        orden de carga por FKs, count(*) OVER, COMMIT/ANALYZE. Comentario de dim_agente corregido
        ("~20 % más rápido" → "tarda ~18 % menos": factores 0,90 vs 1,10).
  - [x] Pregunta de control (¿fact_ticket antes que dim_cliente?): bien. Matiz: falla siempre (FK)
        y la transacción deshace todo el script.
  - [x] Efecto senior/junior en la FICHA: la estudiante decide que NO (se verá en Power BI).
        ⚠ Fase 4: si sale que los senior cumplen más, es un efecto inyectado (factor 0,90 vs 1,10),
        no un hallazgo; decirlo así en insights.
  - [x] Incidencia en la ejecución de la estudiante: ERROR agente_ausencia_motivo_check con
        'baja médica'. Causa: psql en PowerShell usa WIN1252 y leyó mal las tildes del .sql (UTF-8),
        así que el CHECK quedó como 'baja mÃ©dica'. Arreglo: `\encoding UTF8` al inicio del script.
        Reproducido y verificado con ambas codificaciones. La transacción deshizo todo (base intacta).
  - [x] Ejecución de la estudiante (tras el arreglo): todos los INSERT OK + COMMIT. Las tildes salen
        mal en su consola (solo visual). psql pagina la salida ("-- Más --": espacio / q).
  - [x] Prueba del UPDATE rechazado (INC-P1 → Petición): ERROR 23514, la base lo rechaza.
        Pregunta de control (¿qué regla te protegió?): mal — dijo "nomenclatura del código INC-P1".
        Era "P1 solo existe para incidencias" (§0.2); se le explicó leyendo la fila que falla.
        Mejora: las 3 reglas de dim_sla tienen nombre (p1_solo_incidencias, p1_reloj_24x7,
        tareas_no_facturan) → el error ya dice qué regla se rompió.
  - [x] Commit `ca6a805` subido.
- [x] Paso 2 — `02_create_views.sql`
  - [x] 6 vistas: v_ticket_enriquecido (25.300), v_kpis_diarios (733: entradas, salidas, backlog,
        cumplimiento por día de medición, festivos, clima, % agentes ausentes), v_cumplimiento_sprint
        (1.235 cliente × sprint, EN VIVO: %, tramo, €, puntos sobre el tramo inferior, P1 incumplidos),
        v_liquidacion_anual (OFICIAL, lee fact_facturacion_sprint → vacía hasta el SP), 
        v_pareto_penalizacion (dep × tipo, reparto de la penalización entre incumplidos, ABC),
        v_perfil_cliente (40, para clustering).
  - [x] Cuadre con Python: balance −133.003 € (2024) / −154.034 € (2025) idéntico; backlog final 143.
        Todas las vistas < 25 ms (DoD: < 2 s).
  - [ ] Hallazgo para la Fase 4: el Pareto pone a Service Desk N1 primero (36 % de la penalización)
        aunque es el que mejor cumple (95,7 %) → efecto volumen; tasa ≠ importe.
  - [x] Explicado a petición: para qué sirven las vistas (una sola definición de cada cifra,
        simplificar a Power BI, siempre al día, aislar el modelo; analogía de las recetas).
  - [x] Pregunta de control (¿por qué N1 lidera la penalización si cumple mejor?): planteó 3 hipótesis
        (tickets con impacto, vacaciones, tendencia), ninguna la principal. Explicado: efecto volumen
        (N1: 14.389 medidos, 624 incumplidos vs Desarrollo 708 / 263) → tasa ≠ importe.
        Sus hipótesis quedan como preguntas para la Fase 4 (¿N1 empeora más en agosto?).
        Aclarado después: el 36 % es de la penalización total (361.484 €, todos los clientes, 2 años;
        balance −287.037 = −361.484 + 74.447 de bonus) y cómo se reparte (cliente × sprint → a partes
        iguales entre sus incumplidos → departamento; regla de atribución, hay alternativas).
        La estudiante lo reformula bien: "más importe por más volumen, aunque su % es el más bajo".
  - [x] Ejecución de la estudiante (tabla de 6 vistas; psql pagina → -P pager=off) + commit `ef2fee3`.
- [ ] Paso 3 — `03_stored_procedures.sql`  ← ACÁ VOY
  - [x] sp_calcular_facturacion_sprint(sprint, forzar): congela v_cumplimiento_sprint en
        fact_facturacion_sprint (todos los clientes con contrato; sin tickets = neutro, 0 €); no rehace un
        sprint ya facturado salvo p_forzar; valida que exista y esté completo. sp_calcular_facturacion_anio.
        fn_reporte_sprint (13 indicadores, € oficiales o provisionales). sp_refrescar_contexto (upsert clima).
  - [x] Probado: antes 0 filas en v_liquidacion_anual; después 2024 −133.003 € / 2025 −154.034 € (=Python).
        2ª llamada no recalcula; sprint inexistente → error claro. Peores sprints: agosto y Navidad.
        Tabla vaciada (TRUNCATE) para que la estudiante haga el antes/después.
  - [x] Incidencia de la estudiante en pgAdmin: ERROR 42P01 "no existe la relación dim_sprint". Causa:
        las rutinas usan nombres sin esquema y pgAdmin busca en public. Arreglo: cada rutina fija
        `SET search_path = servicedesk, public`. Probado con search_path = public. Tabla vaciada otra vez.
  - [x] Demostración de la estudiante en pgAdmin: la pestaña antigua seguía fallando (sesión con error
        previo) → en un Query Tool nuevo, OK: "ya facturado, no se recalcula", años 2024 y 2025
        facturados, fn_reporte_sprint('2024-11') con 13 indicadores. El árbol de pgAdmin necesita
        Refresh para ver funciones/procedimientos creados desde psql.
  - [x] Pregunta de control (¿por qué no recalcular un sprint facturado?): muy bien, desde su experiencia
        (facturación anual): una cifra facturada debe estar cerrada; solo se rectifica si hay error.
        Añadido: p_forzar = rectificación consciente; calculado_en deja rastro; en real, guardar versiones.
  - [ ] Commit.
- [ ] Paso 4 — `04_sample_queries.sql`

## Dudas abiertas
- Tiempos concretos de la matriz SLA y de los tramos: abiertos a ajuste antes de la Fase 1.
- Fase 1: en PowerShell 5.1, `Invoke-RestMethod` entrega el array JSON como un solo objeto → hay que
  enumerarlo (`ForEach-Object`). En Python no pasa.

## Referencias
- Cómo calculan el SLA otros contratos (para business_case): pliego de la Junta de Andalucía
  (penalización = suma por indicador), ENSA Panamá (descuento sobre facturación mensual por
  prioridad), Sigma Tech (objetivo y rebate por prioridad).
