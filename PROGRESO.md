# Progreso — Brújula Soporte IT · Service Desk SLA Analytics

## Estado actual
**Fase:** 4 cerrada (la 3 sigue abierta) · **Paso:** siguiente, cerrar la 3 o empezar la 5 · **Última sesión:** 2026-11-18

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

### Fase 2 — SQL ✅ (2026-10-19)
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
- [x] Paso 3 — `03_stored_procedures.sql`
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
  - [x] Commit `a368bff` subido.
- [x] Paso 4 — `04_sample_queries.sql`
  - [x] 11 consultas comentadas (pregunta + lectura con cifras) para las 6 preguntas: P1a cumplimiento
        tipo × prioridad × nivel; P1b clientes bajo objetivo (34 cliente-año; 7/8 Gold en 2025); P1c al
        borde < 1 punto (Gold 17,9 % de sprints); P2a balance (−287.037 €, −2,59 % de 11,08 M€); P2b Pareto;
        P2c punto ciego P1 (pequeño: 1/8 Gold, 2/13 Silver); P3a post-festivo 67,8 vs 55,5 lunes;
        P3b calor dentro de jul-ago 0,91 vs 0,39 con ausencias iguales; P4 agosto ~2 tickets/agente,
        79–83 %; P5 backlog por % SLA consumido; P6 perfiles por cuartiles (dinero en Gold "buen servicio").
  - [x] Todas probadas. Corregidas 2 lecturas que no cuadraban con los datos (P6 y P2c).
  - [x] Pregunta de control (¿por qué P3b compara solo dentro de jul-ago?): no la acertó — explicó el
        mecanismo del calor (servidores), no el diseño. Explicado: variable de confusión (calor y
        vacaciones coinciden; ejemplo helados/ahogamientos); dentro del verano las ausencias son iguales
        (17,8 % vs 17,0 %) → la diferencia 0,91 vs 0,39 es del calor. Repasar en la Fase 4.
  - [x] Ejecución de la estudiante + commit `bf81ee5`.

### Fase 3 — Power BI 🚧
- [x] Enfoque: la estudiante pide que el agente lo construya todo y le explique el proceso. Página a página.
- [x] Investigación de mercado (HDI 7 KPI, MetricNet, N-able): FLR, escalado, MTTR, 1ª respuesta, backlog,
      carga por agente, créditos de servicio, ingresos en riesgo. No disponibles: CSAT, FCR, coste por ticket.
- [x] Spec `_brief/report-spec.md` (v2, 4 páginas, filtro por sprint en todas). La estudiante aporta un ejemplo
      (cuadro de objetivos de su empresa; no se copian nombres ni marca) → página 1 = "Cumplimiento de objetivos".
- [x] SQL: `v_ticket_enriquecido` + fecha_medicion + penalizacion_atribuida_eur (suma 361.484 € = facturación);
      nueva `v_facturacion_sprint` (margen sobre tramo inferior). Sin commit todavía.
- [x] Modelo TMDL a mano (EULA del MCP de modelado no aceptada → Tier 2): 8 tablas, Sprint→Calendario→Tickets
      (fecha de medición; creación y salida inactivas), Objetivos KPI (tabla de configuración desconectada).
      Error en Desktop: sangría en model.tmdl línea 1 → corregido.
- [x] Página 1 (70 visuales, validación 0 errores): rail de 7 filtros, resumen y 15 KPI en 4 bloques.
      Cambio de la estudiante: solo dos estados (Cumplido / Incumplido) con un único objetivo por KPI.
- [x] Generadores guardados en `03_powerbi/_generadores/` (build_model.py, build_report.py).
- [x] Abierto en Desktop (2026-10-19): corregidas las medidas con error y las referencias del informe;
      corregido en `build_model.py` el orden de displayFolder, los comentarios de relaciones y las comillas
      de 'Facturación' (los arreglos a mano en el TMDL se perdían al regenerar).
- [x] KPI de dos estados (Cumplido / Incumplido) con un único objetivo por KPI (decisión de la estudiante).
- [x] Todas las medidas en una tabla **Medidas**, ordenadas por carpetas (01 Volumen … 05 Facturación).
- [x] **Tope por cliente y sprint** (2026-10-20, FICHA §0.3): el ajuste queda entre −3,5 % y +3 % de la cuota
      del sprint (`v_cumplimiento_sprint.pct_ajuste`; `pct_ajuste_tramo` guarda el del tramo). Penalización
      2024–2025: de 361.484 € a ~142.513 € (del 3,3 % al 1,3 % de lo facturado).
      ⚠ Las cifras de las Fases 1–2 de esta bitácora (balance −133.003 / −154.034 €, Pareto 361.484 €) son
      **sin tope**; las del informe ya van con tope.
- [x] Aclarado con la estudiante: solo el KPI 6 (% SLA de resolución) penaliza o bonifica en la factura, y solo
      en Gold y Silver (Bronze sin penalización). En la página 1 el KPI 6 va destacado (borde azul y tarjeta
      con el impacto en €).
- [x] Páginas construidas (iteradas con capturas y ejemplos de la estudiante, que retoca en Desktop):
  - [x] **Inicio** (portada, 2026-11-17): banner con la marca y 5 tarjetas con icono que navegan a cada página.
  - [x] **Cumplimiento de KPIs**: 15 KPI en 4 bloques con objetivo visible, caja verde/roja de estado,
        barra de cumplidos/incumplidos en la cabecera.
  - [x] **Detalle de indicadores** (2026-11-15): matriz KPI → tipo (Incidencia / Petición / Tarea) con
        objetivo, tickets, computables, valor medido, tiempo medio, % cumplimiento, penalizado y bonificado;
        botones por bloque de KPI (tabla de parámetros).
  - [x] **Evolución del cumplimiento** (2026-10-20): cumplidos / incumplidos por sprint + gráficos de SLA y
        operaciones.
  - [x] **Resultado económico del sprint**: 4 tarjetas (facturado, bonificación, penalización, balance con
        variación frente al sprint anterior), barras divergentes bonificación / penalización y matriz de
        clientes Gold y Silver (umbral, % SLA, tickets, ✓ / ✗).
  - [x] **Impacto económico acumulado** (2026-11-18): 4 tarjetas con leyenda (facturación, bonificación,
        penalización y balance neto en verde / rojo), evolución por sprint y **Pareto** de penalización por
        cliente (columnas y líneas nativo, línea del 80 %): 14 de 22 clientes suman el 80 %.
  - [x] **Riesgo por cliente** y **Tickets por departamento** (incidencias / peticiones / tareas por
        departamento, % sobre su tipo y % facturable).
- [x] Diseño común (2026-11-16 → 18): cinta azul con icono y título en todas las páginas, pestañas entre
      las 5 páginas principales, panel de filtros a la izquierda, botones **← Atrás** y **⌂ Inicio**.
      Las páginas de análisis quedan ocultas: se navega desde la portada.
- [x] Visuales de AppSource probados: se quedan «Line & Stacked Column with Table» (evolución económica).
      «Pareto Chart Pro» se sustituyó por el gráfico nativo (no se podía controlar su formato). Página de
      Deneb preparada (`add_pagina_deneb.py`), sin aplicar.
- [x] Generadores: `build_model.py` (modelo, fiable) y scripts `add_*.py` por página en
      `03_powerbi/_generadores/`. `build_report.py` ya **no** reproduce las páginas rediseñadas en Desktop:
      no regenerar el informe entero.
- [x] Explicaciones dadas a la estudiante: KPI uno a uno con filtros, tabla Objetivos KPI, niveles de contrato,
      tipo y prioridad, MTTR, ritmo de cierre, backlog, por qué el sprint 2025-17 sale tan mal, importancia del
      Pareto (80 % = 59.205 € en 2025 concentrado en 14 clientes).
- Desviación de la plantilla (decisión consciente): la Parte 6 pide 2 páginas y 6–7 visuales por página; el
  informe tiene 8 páginas con navegación (la estudiante prefirió un informe completo tipo producto).

**Pendiente para cerrar la Fase 3 (Definition of Done):**
- [ ] **Página de análisis estratégico ("¿por qué?")**: el cruce con el contexto externo (calor > 35 °C,
      post-festivo, vacaciones de agosto) todavía no está en el informe. Rematar con la frase accionable.
      **Pospuesta por la estudiante (2026-11-18)**: se publica lo hecho y se retoma más adelante.
      Propuesta guardada: página «Factores de contexto» (6.ª pestaña y 6.ª tarjeta de la portada; filtros
      Año y Nivel de contrato): ① líneas por mes, área % agentes ausentes + línea % cumplimiento;
      ② tarjeta r ausencias ↔ cumplimiento; ③ recomendación; ④ barras horizontales tickets por día
      laborable según tipo de día; ⑤ columnas Infra P1/P2 por día > 35 °C vs ≤ 35 °C solo jul–ago;
      ⑥ dispersión de clientes (tickets × % incumplimiento, tamaño = penalización). Medidas nuevas:
      Tickets por día laborable, Incidencias Infra P1/P2 por día, Correlación ausencias-cumplimiento.
- [ ] `03_powerbi/measures_documentation.md`: documentar las 106 medidas por familia (una frase cada una).
- [x] Capturas PNG de las 8 páginas en `03_powerbi/screenshots/` (2026-11-19, `powerbi-desktop screenshot-all`
      con Desktop abierto, recortadas al lienzo).
- [ ] Comprobar que el informe responde visualmente al menos 3 preguntas de la Ficha (P1 cumplimiento,
      P2 balance / Pareto, P5 backlog ya cubiertas; falta P3 / P4 contexto externo).
- [ ] **Commit y publicación** (Fase 3 en curso, sin cerrar): desde `af67fd6` (2026-10-19) nada está
      subido: informe, modelo, generadores, FICHA (tope) y `02_sql/02_create_views.sql` (tope).
      ✅ Hecho el 2026-11-18: commit `3f73b14` subido (con el PBIX actualizado).
- [ ] Re-ejecutar `02_create_views.sql` + `sp_calcular_facturacion_anio` con el tope y revisar
      `verificar_carga.py` / las cifras de control (ahora con tope).
- [ ] Decidir: ¿Objetivos KPI a PostgreSQL (CSV de configuración)?

### Fase 4 — Análisis en Python 🚧 (empezada el 2026-11-18, con la Fase 3 aún abierta)
Plan aprobado: `04_analysis/eda_completo.ipynb`, bloques 0 · 0.1 · 1 descriptivo · 2 estacionalidad ·
3 Pareto · 4 contexto externo · 5 perfiles (K-Means) · 6 previsión (Prophet) · 7 riesgo (logística) ·
8 hallazgos. Bloque a bloque: el agente lo escribe, la estudiante lo ejecuta y pega la salida.
- [x] Bloques 0 y 0.1 escritos y probados en kernel limpio: 0 duplicados; todos los nulos los explica el
      estado del ticket (cancelados, abiertos, cumplidos); 12 reglas de valores imposibles con 0 filas;
      penalización cuadrada en 4 vistas (142.513 € con tope); balance −31.743 € (2024) / −36.322 € (2025);
      240 tickets sin agente (228 cancelados antes de asignar + 12 abiertos). PNG `00_calidad_datos.png`.
- [x] Ejecución de la estudiante (bloque 0: 5 vistas, mismas filas que la prueba).
- [x] Pregunta de control (¿`fecha_incumplimiento` vacía en el 92 % es un problema?): bien — "si no se
      incumplieron, está bien que esté en blanco". Matiz añadido: un nulo con significado se valida en
      las dos direcciones (los 1.912 incumplidos tienen fecha, los 22.552 cumplidos y los 836 sin medir no)
      y no se rellena con una fecha inventada.
- [x] Cuadres de la estudiante: 142.513 € en las 4 vistas, balance −31.743 / −36.322 €. Lectura del 0.1
      escrita en el cuaderno (datos aptos sin limpieza adicional).
- [x] Bloque 1 (descriptivo, P1) escrito y probado: % de SLA consumido por prioridad (mediana ~40–44 %,
      p95 ~110–115 %); incumplimiento P1 6,9 % · P2 7,2 % · P3 8,1 % · P4 7,8 %; atípicos IQR 4–6 %,
      con el doble de escalados (≈ 65 % vs 33 %) → adelanta la correlación 4. Clientes-año bajo objetivo:
      Gold 4/8 (2024) y 7/8 (2025). Sprints deficientes: Gold 43 %, Silver 39 %; al borde (< 1 punto):
      Gold 18 %. PNG `01_distribucion.png`.
- [x] Pregunta de control (¿por qué % de SLA consumido y no horas?): bien en lo principal ("ya calcula
      para cada prioridad su valor de medición"). Matiz: no es "más confiable" sino **comparable** —
      normaliza cada ticket contra su propio objetivo (100 % = el límite para todos); en horas un P4
      siempre parecería peor aunque cumpla. Las horas siguen sirviendo para planificar (MTTR).
- [x] Salida del bloque 1 de la estudiante: coincide con la prueba. Lectura del bloque 1 escrita.
- [x] Bloque 2 (estacionalidad, P3) escrito y probado: volumen plano todo el año (~50 tickets/día
      laborable) salvo agosto (44,7), y aun así agosto es el peor mes (80,8 % de cumplimiento con 32 % de
      ausentes; jul 89,6 %, dic 90,6 %). Lunes 55,5 → viernes 42,2 tickets/día. Post-festivo: 68,9 tickets
      vs 55,5 un lunes (+24 %, Mann-Whitney p = 3·10⁻⁵, n = 19 días) y los tickets creados ese día cumplen
      87,0 % vs 93,1 %. PNG `02_estacionalidad.png`.
- [x] Ejecución de la estudiante (gráfico OK) + pregunta de control del bloque 2: bien — "es una cuestión
      de capacidad". Matiz en la lectura: en agosto coinciden vacaciones y calor; se separan en el bloque 4.
- [x] Bloque 3 (Pareto ABC, P2) escrito y probado: cuota 10.973.784 €, bonus 74.447 € (0,68 %),
      penalización 142.513 € (1,30 %), balance −68.066 € (−0,62 %). Sin 80/20 clásico: 7 de 10
      departamento × tipo y 14 de 22 clientes (8 Gold + 6 Silver) suman el 80 %. N1: 4,3 % de
      incumplimiento pero 36,6 % de la penalización (volumen); Desarrollo 32,7 % pero 14,8 %. Tareas fuera
      (no facturan). PNG `03_pareto.png`.
- [x] Ejecución de la estudiante (gráfico OK) + pregunta de control del bloque 3: a medias. Mal la causa
      («N1 tiene más P1»): sus P1 solo suman 1.255 € de 52.194 € (2 %); la causa es el **volumen**
      (65 % de los tickets → 686 incumplidos con un 4,3 %). Bien el «importe» para decidir la inversión;
      matiz: tasa = dónde está roto el proceso, importe = dónde está el dinero; 1 punto en N1 ≈ 160 tickets/año.
- [x] Bloque 4 (contexto externo, P3) escrito y probado: todo el año, días > 35 °C cumplen 87,5 % vs
      92,8 % (con confusión: 21,5 % vs 7,4 % ausentes). Solo jul–ago (ausencias iguales 25,4 / 25,6 %):
      Infra P1/P2 1,13 vs 0,55 por día (×2, p = 0,003) pero cumplimiento 85,7 vs 85,3 % (sin efecto).
      Mes a mes: r ausencias = −0,92, r calor = −0,67; regresión con las dos (R² 0,85): ausencias −0,48 puntos
      por punto (p < 0,001), calor +0,03 (p = 0,31, no significativo). PNG `04_contexto_externo.png`.
- [x] Pregunta de control del bloque 4: bien la conclusión («los días de calor no mejoran el cumplimiento;
      falta personal»). Corregido: «con menos personal se abren menos incidencias» — los tickets los abren
      los clientes y con calor entran **más** incidencias de Infra. No dijo explícitamente qué resultado
      creer → explicado (jul–ago, mismas ausencias) y por qué el aire acondicionado no mejora el SLA.
- [x] Bloque 5 (perfiles, P6) escrito y probado. Decisión: K-Means solo con variables de uso (tamaño,
      tickets/100 usuarios, % P1, % escalados, % incumplimiento), sin penalización ni nivel (sería circular).
      k = 3 (codo en 3; silueta 0,33 vs 0,35 con k = 2 → estructura débil, se dice). Grupos: «Mayores, cumplen
      mejor» (26: 8 Gold, 13 Silver, 5 Bronze), «Medianos, cumplen peor» (9: 8 Bronze, 1 Silver), «Pequeños con
      muchos P1» (5 Bronze, 4,2 % P1, 17,8 % incumplimiento). Hallazgo: 5 Bronze con tamaño de Silver
      (152–238 usuarios; Silver empieza en 200) y su servicio → candidatos a subir de nivel. PNG `05_clusters.png`.
- [x] Ejecución de la estudiante (gráfico OK) + pregunta de control del bloque 5: a medias — dato correcto
      («no todos los contratos penalizan») sin la consecuencia: con la penalización, K-Means solo redescubre
      el contrato (comprobado: grupos = Bronze / Bronze / Gold+Silver), y el nivel se deja fuera para poder
      comparar uso vs contrato. Lectura del bloque 5 escrita.
- [x] Bloque 6 (previsión, P4) escrito y probado: Prophet sobre días laborables con post-festivos como
      eventos. Validación jul–dic 2025: error medio 5,9 tickets/día (MAPE 11,6 %), 91 % de días dentro del
      IC 95 %. T1 2026: 3.400 tickets (IC 2.520–4.276; sin festivos de 2026, no están en los datos).
      Cumplimiento = 128,4 − 22,1 × carga (R² 0,67) → carga máx. 1,60 tickets/agente disponible/día para un
      93 %. Agosto 2026: 49,3 tickets/día → 31 agentes disponibles de 35 → máx. 4 de vacaciones a la vez
      (ago 2025: 10,4 fuera, 79,0 %). Tabla de sensibilidad 90–94 %. PNG `06_forecast.png`.
      Pendiente menor: aún salen avisos de Prophet/plotly en la salida (cosmético).
- [x] (2026-11-19) Ejecución de la estudiante del bloque 6 + pregunta de control: a medias — respondió para qué
      sirve prever («prepararnos y actuar»), no por qué validar con datos no vistos. Explicado: sobreajuste;
      ocultar un periodo simula el uso real y da el error esperable (±6 tickets/día). Lectura del 6 escrita;
      avisos de Prophet/cmdstanpy silenciados (`cmdstanpy.disable_logging()`).
- [x] Bloque 7 (riesgo, P5) escrito y probado: logística con variables conocidas con el ticket abierto (sin
      fuga). Entreno 2024 (11.964), prueba 2025 (12.492): AUC 0,80; el 10 % de más riesgo contiene el 44,5 %
      de los incumplidos. Odds: cada reasignación ×2,97, post-festivo ×1,99, Gold 0,29, Silver 0,58,
      senior 0,54 (⚠ efecto inyectado, marcado como tal), calor 1,16 y tipo ≈ 1 (sin efecto claro).
      Abiertos en plazo al corte: 124; 7.546 € en juego, 987 € de penalización esperada; los 15 primeros
      concentran el 57 %. PNG `07_riesgo.png`.
- [x] Pregunta de control del bloque 7: bien lo principal («solo se conoce cuando el ticket ya se cerró» →
      fuga de información). Corregido otra vez el error recurrente «solo penalizan los P1 de Gold y Bronze»:
      penaliza la resolución de todas las incidencias y peticiones de **Gold y Silver**; Bronze nunca; los P1
      son 1.985 € de 142.513 € (1,4 %). ⚠ Repasar este punto: ya salió en la Fase 3 y en el bloque 3.
      Lectura del bloque 7 escrita.
- [x] Bloque 8 (hallazgos) en el cuaderno + `05_docs/insights_findings.md` (resumen ejecutivo, 7 hallazgos
      dato / interpretación / acción con sus PNG, y apartado de honestidad: efectos inyectados, resultados
      débiles y límites). Hallazgos: ① plantilla, no calor; ② cupo de 4 vacaciones en agosto; ③ reasignación
      ×3; ④ N1 cumple mejor y penaliza más (contraintuitivo); ⑤ Gold no llega al 95 %; ⑥ post-festivo +24 %;
      ⑦ 5 Bronze con servicio de Silver.
- [x] Cuaderno completo en kernel limpio: 62 celdas, 0 errores, 0 avisos; 8 PNG en `outputs/`.

**Definition of Done de la Fase 4:**
- [x] El cuaderno corre de arriba abajo sin errores en un kernel limpio.
- [x] Cada bloque tiene su celda de lectura que interpreta el resultado.
- [x] PNG en `outputs/` con la paleta del proyecto (150 ppp).
- [x] `insights_findings.md` con 7 hallazgos en formato dato / interpretación / acción.
- [x] Al menos un hallazgo contraintuitivo o negativo (④ N1; calor sin efecto; perfiles débiles).
- [x] Commit `3257f74` subido (2026-11-19) con el cuaderno ejecutado en limpio. **Fase 4 cerrada.**
- [x] (2026-11-19) Textos del cuaderno sustituidos por la versión revisada por la estudiante (23 celdas de
      explicación, lenguaje más formal; sin las preguntas de control, que quedan en esta bitácora). Código y
      salidas sin cambios. Corregidas 2 erratas («una grupo», «:» sobrante).

**Siguiente:** cerrar la Fase 3 (página «Factores de contexto», measures_documentation.md, capturas) y Fase 5 (README, business_case.md, data_dictionary.md).

### Fase 5 — Documentación y vitrina 🚧 (empezada el 2026-11-19)
Plan: ① capturas · ② README completo · ③ `business_case.md` · ④ `data_dictionary.md` · ⑤ prueba de clonar
como un tercero · ⑥ (opcional) página web en GitHub Pages.
- [x] Historial de git revisado: sin `.env` ni contraseñas; LICENSE MIT.
- [x] Capturas de las 8 páginas (cierra también ese punto de la Fase 3).
- [x] README completo (2026-11-19): badges, tabla pregunta → técnica → resultado con cifras, 6 hallazgos,
      capturas, modelo en estrella (12 tablas, 7 vistas, 30 índices, 3 procedimientos, 1 función),
      estructura, puesta en marcha en 6 pasos, actualización periódica, herramientas, autora (LinkedIn y
      GitHub) y declaración de datos sintéticos / reales. Enlaces comprobados.
- [x] `data_dictionary.md` generado desde la base con `05_docs/generar_data_dictionary.py` (19 tablas y
      vistas, 251 columnas con tipo, clave, descripción y ejemplo real; se regenera si cambia el esquema).
- [x] `business_case.md`: organización, contratos y tramos, desafío, 6 preguntas, solución, resultado en
      una línea y alcance y limitaciones (qué no se puede concluir). Enlaces de los 3 documentos comprobados.
- [x] (2026-11-20) Commit de la Fase 5 subido: README, capturas, `05_docs` y el PBIX actualizado.
- [ ] Prueba de clonar como un tercero  ← ACÁ VOY

## Dudas abiertas
- Tiempos concretos de la matriz SLA y de los tramos: abiertos a ajuste antes de la Fase 1.
- Fase 1: en PowerShell 5.1, `Invoke-RestMethod` entrega el array JSON como un solo objeto → hay que
  enumerarlo (`ForEach-Object`). En Python no pasa.

## Referencias
- Cómo calculan el SLA otros contratos (para business_case): pliego de la Junta de Andalucía
  (penalización = suma por indicador), ENSA Panamá (descuento sobre facturación mensual por
  prioridad), Sigma Tech (objetivo y rebate por prioridad).
