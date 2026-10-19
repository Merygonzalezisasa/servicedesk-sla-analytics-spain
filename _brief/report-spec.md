# Report Spec — Brújula Soporte IT · SLA y facturación (v2)

> v2 (2026-10-19): la estudiante pide (1) una página filtrable por cliente, (2) una página de impacto
> general para el negocio, (3) filtro por sprint en todas las páginas, (4) gráficos más creativos y
> (5) métricas con más valor en el mercado del service desk.

## Report identity
- Report name: **Brujula SLA** (PBIP en `03_powerbi/`)
- Semantic model: nuevo, `Brujula SLA.SemanticModel`, Import desde PostgreSQL local
  (`localhost:5432`, base `servicedesk_sla`, esquema `servicedesk`; parámetros M `Servidor` y `Base de datos`)
- Audience: dirección general, Service Delivery y Finanzas (ficticia) + reclutadores del portfolio
- Primary purpose: impacto en el negocio, salud de la operación, causas y ficha de cada cliente
- Delivery target: **solo PBIP local** (sin publicar en Fabric)

## Investigación de mercado: métricas que más valor aportan
Fuentes: HDI (Rumburg, *The Seven Most Important Performance Indicators for the Service Desk*),
marco de benchmarking de MetricNet, guías de SLA para proveedores de servicios gestionados (N-able).

| Métrica de mercado | En el informe | Cálculo con nuestros datos |
|---|---|---|
| Cumplimiento del SLA y créditos de servicio (penalizaciones) | Pág. 1, 2, 4 | % de tickets computables cumplidos; € de penalización y bonus |
| Resolución en primer nivel (FLR) — HDI ~72 % | Pág. 2 | % de tickets resueltos por Service Desk N1 sin reasignar |
| Tasa de escalado | Pág. 2 | % de tickets con ≥ 1 reasignación |
| Tiempo medio de resolución (MTTR) y de 1ª respuesta | Pág. 2 | Minutos de reloj de SLA → horas / minutos |
| Backlog | Pág. 2 | Tickets abiertos al cierre del periodo |
| Carga por agente (aprox. a utilización) | Pág. 3 | Tickets por agente disponible y día |
| Ingresos en riesgo | Pág. 1 | Cuota de los cliente-sprints a < 1 punto de caer de tramo |
| Ingreso por ticket (sustituye a coste por ticket) | Pág. 1 | Cuota facturada ÷ tickets |
| CSAT, FCR (primer contacto), coste por ticket | **No disponibles** | No hay encuestas, contactos ni costes: se declara como limitación y mejora futura |

## User decisions and constraints
- Scope: **4 páginas** con navegación entre ellas.
- Interactivity: slicers **Año** y **Sprint** en todas las páginas, **sincronizados**; **Cliente** en la página 4. Filtro cruzado por defecto; árbol de descomposición para bajar a la causa.
- Design direction: sobrio corporativo, títulos-conclusión, gráficos variados (cascada, mapa de calor, árbol de descomposición, dispersión con tamaño, semáforo de sprints).
- Publishing: no. Credenciales de PostgreSQL: las introduce la estudiante en Power BI Desktop.
- Accessibility: WCAG AA, alt text, el color nunca es la única señal.

## Cambios previos en SQL (02_create_views.sql)
- `v_ticket_enriquecido` + `fecha_medicion` (día en que se conoce el resultado: resolución si cumple, vencimiento si incumple) + `penalizacion_atribuida_eur` (penalización oficial del cliente-sprint repartida entre sus incumplidos). Así el Pareto se calcula en DAX y responde a los filtros.
- Nueva `v_facturacion_sprint`: fact_facturacion_sprint + `puntos_sobre_tramo_inferior` + `objetivo_contractual` (para "ingresos en riesgo" y la ficha de cliente).

## Narrative
- Core story: Brújula pierde 287.037 € en dos años (−2,6 % de la cuota). Los Gold concentran la pérdida; N1 lidera por volumen; agosto y Navidad son los peores sprints; la causa principal es la falta de plantilla (r ≈ −0,9), con efectos de festivos y calor.
- Key questions answered: P1, P2, P3 y P6 de la Ficha (P4 y P5 en el notebook).

## Design identity
- Tone: **Sobrio corporativo de operaciones** — fondo gris claro, tarjetas blancas, azul marino principal, rojo solo para penalización, verde para bonus, ámbar para el contexto (ausencias, calor, festivos).
- Signature: **títulos-conclusión + barra superior común** (título · navegación · Año/Sprint) idéntica en las 4 páginas, y **semáforo de tramos** (rojo/gris/verde) reutilizado donde aparece el resultado de un sprint.

## Page plan
1. **Impacto en el negocio** — Executive Summary, variante B
   - KPI: Cuota facturada €, Penalización €, Bonus €, Balance €, % Ingresos perdidos, Ingresos en riesgo €.
   - Balance € por sprint (columnas rojo/verde) · Cascada del balance por nivel de contrato · Pareto de la penalización (departamento · tipo) · Penalización por comunidad autónoma.
2. **Operación del servicio** — Analytical Canvas, variante B
   - KPI: % Cumplimiento SLA (Δ vs año anterior), Resolución en primer nivel, % Escalados, MTTR (h), 1ª respuesta (min), Backlog al cierre.
   - Cumplimiento por nº de sprint 2024 vs 2025 · Mapa de calor departamento × prioridad · Árbol de descomposición de los incumplidos · Incumplimiento según nº de reasignaciones.
3. **¿Por qué?** — Analytical Canvas, variante B
   - Combo mensual % agentes ausentes vs % cumplimiento · Tarjeta r · Recomendación · Tickets por día según tipo de día · Incidencias Infra P1/P2 con/sin calor (jul–ago) · Dispersión de clientes.
4. **Ficha de cliente** — Comparative Benchmark, variante B (slicer de cliente)
   - KPI: Contrato y objetivo, % Cumplimiento vs objetivo, Balance €, Cuota facturada €, Cliente-sprints deficientes.
   - Semáforo de tramos por sprint · Cumplimiento por sprint vs objetivo · Incumplidos por departamento · Tickets por tipo y prioridad.

## Design system summary
- Theme: `assets/base.json` adaptado. Página `#F4F5F7`; visuales blancos con borde `#E1DFDD`.
- Colores: cumplimiento/balance `#1F3A5F`; penalización `#C0392B`; bonus `#1E7B5C`; contexto `#B7791F`; neutro `#7A8794`. Niveles: Gold `#B7791F`, Silver `#7A8794`, Bronze `#8C5A3C`. Semáforo: deficiente `#C0392B`, neutro `#D9DDE3`, bonus `#1E7B5C`.
- Typography: Segoe UI Semibold (título de página 20 pt, de visual 12 pt) + Segoe UI 10–11 pt; KPI 28 pt.
- Layout: FHD 1920×1080, rejilla 12×12, margen 32, gutter 24, snap 8. Barra superior en la fila 1.

## Model requirements
- Tablas: **Tickets** (v_ticket_enriquecido), **Facturación** (v_facturacion_sprint), **Calendario** (v_kpis_diarios + columnas de Power Query), **Sprint** (dim_sprint), **Cliente** (v_perfil_cliente), **Departamento**, **Política SLA**.
- Relaciones (1:N, unidireccionales): Sprint→Calendario (sprint_id); Calendario→Tickets por **fecha de medición** (activa) y por **fecha de creación** (inactiva, se usa con USERELATIONSHIP para el volumen de entrada); Cliente→Tickets; Cliente→Facturación; Sprint→Facturación; Departamento→Tickets; Política SLA→Tickets. Un único camino de filtro de Sprint a Tickets (vía Calendario) y otro a Facturación.
- Medidas (con formato es-ES, descripción y carpeta): ver contrato.

## Canonical design contract

```yaml
Design Brief:
  generated_by: powerbi-report-design
  contract_version: 1
  mode: greenfield
  design_identity:
    tone: "Sobrio corporativo de operaciones: gris claro, tarjetas blancas, azul marino principal; rojo solo penalización, verde bonus, ámbar contexto"
    signature: "Barra superior común (título-conclusión · navegación · Año/Sprint) en todas las páginas + semáforo de tramos rojo/gris/verde"
  archetype: Executive Summary
  color_map:
    - { measure: "Tickets[% Cumplimiento SLA]", color: "#1F3A5F", tint: "#DCE4EE" }
    - { measure: "Facturación[Balance €]", color: "#1F3A5F", tint: "#DCE4EE" }
    - { measure: "Facturación[Penalización €]", color: "#C0392B", tint: "#F6DCD9" }
    - { measure: "Tickets[Penalización atribuida €]", color: "#C0392B", tint: "#F6DCD9" }
    - { measure: "Facturación[Bonus €]", color: "#1E7B5C", tint: "#D7EEE5" }
    - { measure: "Facturación[Cuota facturada €]", color: "#7A8794", tint: "#E6E9ED" }
    - { measure: "Calendario[% Agentes ausentes]", color: "#B7791F", tint: "#F5E8D3" }
    - { measure: "Calendario[Incidencias Infra P1/P2 por día]", color: "#B7791F", tint: "#F5E8D3" }
    - { measure: "Tickets[Tickets por día laborable]", color: "#1F3A5F", tint: "#DCE4EE" }
    - { measure: "Tickets[Tickets incumplidos]", color: "#C0392B", tint: "#F6DCD9" }
  shared_header:
    regions: { header: [1, 1, 6, 2], nav: [6, 1, 9, 2], filters: [9, 1, 13, 2] }
    nav: { kind: pageNavigator, pages: ["Impacto en el negocio", "Operación del servicio", "¿Por qué?", "Ficha de cliente"] }
    slicers:
      - { id: year_slicer, field_bindings: "Sprint[Año]", slicer_type: dropdown, sync_group: "anio" }
      - { id: sprint_slicer, field_bindings: "Sprint[Sprint]", slicer_type: dropdown, multi_select: true, sync_group: "sprint" }
  pages:
    - name: "Impacto en el negocio"
      role: landing
      archetype: Executive
      layout_variant: B
      variant_rationale: "Seis KPI de dinero de importancia comparable: la tira de KPI es el mensaje; debajo, cuatro vistas del mismo dinero (tiempo, nivel, causa operativa, geografía)."
      page_background: "#F4F5F7"
      layout_contract:
        canvas: { width: 1920, height: 1080, margin: 32, gutter: 24, snap: 8 }
        grid:
          columns: 12
          rows: 12
          regions:
            header:    [1, 1, 6, 2]
            nav:       [6, 1, 9, 2]
            filters:   [9, 1, 13, 2]
            kpis:      [1, 2, 13, 4]
            trend:     [1, 4, 8, 8]
            waterfall: [8, 4, 13, 8]
            pareto:    [1, 8, 8, 13]
            region:    [8, 8, 13, 13]
        placements:
          - { id: page_title, region: header, kind: textbox, text: "Brújula pierde 287.037 € en dos años por SLA: el 2,6 % de lo que factura, casi todo en clientes Gold" }
          - { id: page_nav, region: nav, kind: pageNavigator }
          - { id: year_slicer, region: filters, kind: slicer, field_bindings: "Sprint[Año]", slicer_type: dropdown, slot: 1, of: 2 }
          - { id: sprint_slicer, region: filters, kind: slicer, field_bindings: "Sprint[Sprint]", slicer_type: dropdown, slot: 2, of: 2 }
          - { id: kpi_quota, region: kpis, kind: cardVisual, slot: 1, of: 6, purpose: "¿Cuánto se factura en cuota?", field_bindings: "Facturación[Cuota facturada €]", color_strategy: measure_match }
          - { id: kpi_penalty, region: kpis, kind: cardVisual, slot: 2, of: 6, purpose: "¿Cuánto se pierde en penalizaciones?", field_bindings: "Facturación[Penalización €]", color_strategy: measure_match }
          - { id: kpi_bonus, region: kpis, kind: cardVisual, slot: 3, of: 6, purpose: "¿Cuánto se gana en bonus?", field_bindings: "Facturación[Bonus €]", color_strategy: measure_match }
          - { id: kpi_balance, region: kpis, kind: cardVisual, slot: 4, of: 6, purpose: "¿Cuál es el balance neto?", field_bindings: { value: "Facturación[Balance €]", reference: "Facturación[Balance año anterior €]" }, insight_basis: "Comparación con el año anterior", color_strategy: measure_match }
          - { id: kpi_lost, region: kpis, kind: cardVisual, slot: 5, of: 6, purpose: "¿Qué parte de la facturación se pierde?", field_bindings: "Facturación[% Ingresos perdidos]", color_strategy: semantic }
          - { id: kpi_risk, region: kpis, kind: cardVisual, slot: 6, of: 6, purpose: "¿Cuánta cuota estuvo a menos de 1 punto de caer de tramo?", field_bindings: "Facturación[Ingresos en riesgo €]", insight_basis: "Cuota de cliente-sprints con < 1 punto de margen sobre el tramo inferior", color_strategy: semantic }
          - { id: balance_by_sprint, region: trend, kind: clusteredColumnChart, purpose: "¿En qué sprints se gana y en cuáles se pierde dinero?", field_bindings: { Category: "Sprint[Sprint]", Y: "Facturación[Balance €]" }, sort_policy: natural_order, color_strategy: semantic, title: "Los sprints de agosto y Navidad concentran las mayores pérdidas" }
          - { id: balance_waterfall, region: waterfall, kind: waterfallChart, purpose: "¿Qué nivel de contrato explica el balance?", field_bindings: { Category: "Cliente[Nivel de contrato]", Y: "Facturación[Balance €]" }, sort_policy: value_asc, color_strategy: semantic, title: "Gold explica dos tercios de la pérdida; Bronze nunca penaliza" }
          - { id: pareto_penalty, region: pareto, kind: lineClusteredColumnComboChart, purpose: "¿Qué departamento × tipo concentra el 80 % de la penalización?", field_bindings: { Category: "Tickets[Departamento · tipo]", ColumnY: "Tickets[Penalización atribuida €]", LineY: "Tickets[% Acumulado Pareto]" }, sort_policy: value_desc, color_strategy: measure_match, title: "Service Desk N1 acumula un tercio de la penalización por volumen, aunque es quien mejor cumple" }
          - { id: penalty_by_region, region: region, kind: barChart, purpose: "¿Dónde están los clientes que más penalizan?", field_bindings: { Category: "Cliente[Comunidad autónoma]", Y: "Facturación[Penalización €]" }, sort_policy: value_desc, color_strategy: gradient, title: "Madrid concentra el 42 % de la penalización" }
        space_audit: { content_cell_count: 132, placed_cell_count: 132, empty_cell_pct: 0, unplaced_regions: [], largest_region: { name: pareto, pct_of_content: 27 }, balance_rationale: "Tira de 6 KPI; tendencia y Pareto (las vistas con más categorías) reciben 7 columnas; cascada y comunidades, 5." }
    - name: "Operación del servicio"
      role: detail
      archetype: Analytical
      layout_variant: B
      variant_rationale: "Dos slicers compartidos en la barra superior; el contenido necesita el ancho completo para KPI de mercado, tendencia, mapa de calor y árbol."
      page_background: "#F4F5F7"
      layout_contract:
        canvas: { width: 1920, height: 1080, margin: 32, gutter: 24, snap: 8 }
        grid:
          columns: 12
          rows: 12
          regions:
            header:  [1, 1, 6, 2]
            nav:     [6, 1, 9, 2]
            filters: [9, 1, 13, 2]
            kpis:    [1, 2, 13, 4]
            trend:   [1, 4, 8, 8]
            heatmap: [8, 4, 13, 8]
            decomp:  [1, 8, 7, 13]
            escal:   [7, 8, 13, 13]
        placements:
          - { id: page_title, region: header, kind: textbox, text: "El 65 % se resuelve en primer nivel; los tickets escalados incumplen tres veces más" }
          - { id: page_nav, region: nav, kind: pageNavigator }
          - { id: year_slicer, region: filters, kind: slicer, field_bindings: "Sprint[Año]", slicer_type: dropdown, slot: 1, of: 2 }
          - { id: sprint_slicer, region: filters, kind: slicer, field_bindings: "Sprint[Sprint]", slicer_type: dropdown, slot: 2, of: 2 }
          - { id: kpi_compliance, region: kpis, kind: cardVisual, slot: 1, of: 6, purpose: "¿Qué % cumple el SLA y cómo cambia frente al año anterior?", field_bindings: { value: "Tickets[% Cumplimiento SLA]", reference: "Tickets[Variación cumplimiento (puntos)]" }, insight_basis: "Δ en puntos vs año anterior", color_strategy: measure_match }
          - { id: kpi_flr, region: kpis, kind: cardVisual, slot: 2, of: 6, purpose: "¿Qué % resuelve el primer nivel sin escalar? (HDI ~72 %)", field_bindings: "Tickets[Resolución en primer nivel]", color_strategy: none }
          - { id: kpi_escal, region: kpis, kind: cardVisual, slot: 3, of: 6, purpose: "¿Qué % se escala?", field_bindings: "Tickets[% Escalados]", color_strategy: none }
          - { id: kpi_mttr, region: kpis, kind: cardVisual, slot: 4, of: 6, purpose: "¿Cuánto se tarda de media en resolver (horas de reloj SLA)?", field_bindings: "Tickets[MTTR (h)]", color_strategy: none }
          - { id: kpi_frt, region: kpis, kind: cardVisual, slot: 5, of: 6, purpose: "¿Cuánto se tarda en dar la 1ª respuesta?", field_bindings: "Tickets[1ª respuesta media (min)]", color_strategy: none }
          - { id: kpi_backlog, region: kpis, kind: cardVisual, slot: 6, of: 6, purpose: "¿Cuántos tickets quedan abiertos al cierre del periodo?", field_bindings: "Calendario[Backlog al cierre]", color_strategy: none }
          - { id: compliance_trend, region: trend, kind: lineChart, purpose: "¿Cómo evoluciona el cumplimiento sprint a sprint, 2024 vs 2025?", field_bindings: { Category: "Sprint[Número]", Y: "Tickets[% Cumplimiento SLA]", Series: "Sprint[Año]" }, comparison_basis: "Año anterior y línea de referencia 95 % (objetivo Gold)", color_strategy: unique, title: "Agosto (sprints 10–12) es el peor tramo de cada año, y en 2025 cayó más (79 %)" }
          - { id: dept_priority_heatmap, region: heatmap, kind: pivotTable, purpose: "¿Qué departamento falla en qué prioridad?", field_bindings: { Rows: "Departamento[Departamento]", Columns: "Política SLA[Prioridad]", Values: "Tickets[% Cumplimiento SLA]" }, color_strategy: gradient, title: "Desarrollo es el punto débil en todas las prioridades" }
          - { id: breach_decomposition, region: decomp, kind: decompositionTreeVisual, purpose: "¿Dónde se concentran los incumplimientos? (nivel → departamento → prioridad → tipo)", field_bindings: { Analyze: "Tickets[Tickets incumplidos]", ExplainBy: ["Cliente[Nivel de contrato]", "Departamento[Departamento]", "Política SLA[Prioridad]", "Política SLA[Tipo]"] }, color_strategy: measure_match, title: "Explora los incumplidos: haz clic en + para bajar de nivel" }
          - { id: escalation_cost, region: escal, kind: clusteredColumnChart, purpose: "¿Cuánto sube el incumplimiento con cada reasignación?", field_bindings: { Category: "Tickets[Reasignaciones]", Y: "Tickets[% Incumplimiento]" }, sort_policy: category_asc, color_strategy: gradient, title: "Sin escalar incumple el 4 %; con 3 reasignaciones, casi la mitad" }
        space_audit: { content_cell_count: 132, placed_cell_count: 132, empty_cell_pct: 0, unplaced_regions: [], largest_region: { name: decomp, pct_of_content: 23 }, balance_rationale: "KPI de mercado arriba; tendencia y mapa de calor en paralelo; árbol y coste del escalado reparten la fila inferior a partes iguales." }
    - name: "¿Por qué?"
      role: detail
      archetype: Analytical
      layout_variant: B
      variant_rationale: "Mismos dos slicers compartidos; el héroe mensual necesita ancho y las tres pruebas compiten en importancia."
      page_background: "#F4F5F7"
      layout_contract:
        canvas: { width: 1920, height: 1080, margin: 32, gutter: 24, snap: 8 }
        grid:
          columns: 12
          rows: 12
          regions:
            header:   [1, 1, 6, 2]
            nav:      [6, 1, 9, 2]
            filters:  [9, 1, 13, 2]
            hero:     [1, 2, 9, 7]
            corr:     [9, 2, 13, 4]
            insight:  [9, 4, 13, 7]
            holidays: [1, 7, 5, 13]
            heat:     [5, 7, 9, 13]
            clients:  [9, 7, 13, 13]
        placements:
          - { id: page_title, region: header, kind: textbox, text: "Cuando falta un tercio del equipo, el cumplimiento cae: las vacaciones pesan más que el calor o los festivos" }
          - { id: page_nav, region: nav, kind: pageNavigator }
          - { id: year_slicer, region: filters, kind: slicer, field_bindings: "Sprint[Año]", slicer_type: dropdown, slot: 1, of: 2 }
          - { id: sprint_slicer, region: filters, kind: slicer, field_bindings: "Sprint[Sprint]", slicer_type: dropdown, slot: 2, of: 2 }
          - { id: absences_vs_compliance, region: hero, kind: lineClusteredColumnComboChart, purpose: "¿Se mueve el cumplimiento al ritmo de las ausencias, mes a mes?", field_bindings: { Category: "Calendario[Año-Mes]", ColumnY: "Calendario[% Agentes ausentes]", LineY: "Tickets[% Cumplimiento SLA]" }, sort_policy: natural_order, color_strategy: measure_match, title: "En agosto falta 1 de cada 3 agentes y el cumplimiento cae al 79–83 %" }
          - { id: correlation_card, region: corr, kind: cardVisual, purpose: "¿Qué tan fuerte es la relación ausencias–cumplimiento?", field_bindings: "Calendario[Correlación ausencias-cumplimiento]", insight_basis: "Coeficiente de Pearson mensual derivado; no repite cifras del gráfico", callout_value_basis: "Meses del contexto con ≥ 10 días laborables", color_strategy: semantic }
          - { id: recommendation, region: insight, kind: textbox, text: "Recomendación: limitar las vacaciones simultáneas para no bajar de ~28 agentes disponibles, reforzar el turno el día después de cada festivo y activar una guardia de Infraestructura los días de más de 35 °C.", insight_basis: "Síntesis de r ≈ −0,9, +22 % de tickets post-festivo vs lunes y ×2,3 incidencias de Infraestructura con calor" }
          - { id: holiday_effect, region: holidays, kind: columnChart, purpose: "¿Entran más tickets tras un festivo?", field_bindings: { Category: "Calendario[Tipo de día]", Y: "Tickets[Tickets por día laborable]" }, sort_policy: value_desc, color_strategy: measure_match, title: "Tras un festivo entran un 22 % más tickets que un lunes normal" }
          - { id: heat_effect, region: heat, kind: columnChart, purpose: "¿Suben las incidencias graves de Infraestructura con calor, con las mismas ausencias?", field_bindings: { Category: "Calendario[Día caluroso]", Y: "Calendario[Incidencias Infra P1/P2 por día]" }, visual_filter: "Calendario[Mes número] in (7, 8)", sort_policy: value_desc, color_strategy: measure_match, title: "Con más de 35 °C, más del doble de incidencias graves de Infraestructura (jul–ago)" }
          - { id: client_profiles, region: clients, kind: scatterChart, purpose: "¿Qué perfiles de cliente concentran la penalización?", field_bindings: { Details: "Cliente[Cliente]", X: "Tickets[Tickets creados]", Y: "Tickets[% Incumplimiento]", Size: "Facturación[Penalización €]", Legend: "Cliente[Nivel de contrato]" }, color_strategy: semantic, title: "Los Gold pierden más aunque cumplen mejor: su objetivo (95 %) es el más exigente" }
        space_audit: { content_cell_count: 132, placed_cell_count: 132, empty_cell_pct: 0, unplaced_regions: [], largest_region: { name: hero, pct_of_content: 30 }, balance_rationale: "Héroe con la causa principal (30 %); correlación y recomendación a su derecha; tres pruebas de igual tamaño abajo." }
    - name: "Ficha de cliente"
      role: detail
      archetype: Comparative
      layout_variant: B
      variant_rationale: "Se compara un cliente con su objetivo contractual; el slicer de cliente se añade a la barra superior."
      page_background: "#F4F5F7"
      layout_contract:
        canvas: { width: 1920, height: 1080, margin: 32, gutter: 24, snap: 8 }
        grid:
          columns: 12
          rows: 12
          regions:
            header:   [1, 1, 5, 2]
            nav:      [5, 1, 8, 2]
            filters:  [8, 1, 13, 2]
            kpis:     [1, 2, 13, 4]
            strip:    [1, 4, 13, 6]
            trend:    [1, 6, 7, 13]
            dept:     [7, 6, 13, 10]
            mix:      [7, 10, 13, 13]
        placements:
          - { id: page_title, region: header, kind: textbox, text: "Ficha de cliente: ¿cumple su contrato y cuánto nos cuesta?" }
          - { id: page_nav, region: nav, kind: pageNavigator }
          - { id: client_slicer, region: filters, kind: slicer, field_bindings: "Cliente[Cliente]", slicer_type: dropdown, search: true, slot: 1, of: 3 }
          - { id: year_slicer, region: filters, kind: slicer, field_bindings: "Sprint[Año]", slicer_type: dropdown, slot: 2, of: 3 }
          - { id: sprint_slicer, region: filters, kind: slicer, field_bindings: "Sprint[Sprint]", slicer_type: dropdown, slot: 3, of: 3 }
          - { id: kpi_contract, region: kpis, kind: cardVisual, slot: 1, of: 5, purpose: "¿Qué contrato tiene y qué objetivo debe cumplir?", field_bindings: "Cliente[Contrato y objetivo]", color_strategy: none }
          - { id: kpi_vs_target, region: kpis, kind: cardVisual, slot: 2, of: 5, purpose: "¿Cumple su objetivo?", field_bindings: { value: "Tickets[% Cumplimiento SLA]", reference: "Tickets[Diferencia vs objetivo (puntos)]" }, insight_basis: "Gap frente al objetivo contractual", color_strategy: measure_match }
          - { id: kpi_balance, region: kpis, kind: cardVisual, slot: 3, of: 5, purpose: "¿Cuánto ganamos o perdemos con él?", field_bindings: "Facturación[Balance €]", color_strategy: measure_match }
          - { id: kpi_quota, region: kpis, kind: cardVisual, slot: 4, of: 5, purpose: "¿Cuánto factura?", field_bindings: "Facturación[Cuota facturada €]", color_strategy: measure_match }
          - { id: kpi_deficient, region: kpis, kind: cardVisual, slot: 5, of: 5, purpose: "¿En cuántos sprints cayó a deficiente?", field_bindings: "Facturación[Cliente-sprints deficientes]", color_strategy: semantic }
          - { id: tramo_strip, region: strip, kind: pivotTable, purpose: "¿Qué tramo obtuvo en cada sprint?", field_bindings: { Rows: "Sprint[Año]", Columns: "Sprint[Número]", Values: "Facturación[% Cumplimiento facturado]" }, color_strategy: semantic, insight_basis: "Fondo de celda = color del tramo (medida Facturación[Color tramo])", title: "Semáforo de tramos por sprint (rojo = deficiente, gris = neutro, verde = bonus)" }
          - { id: client_trend, region: trend, kind: lineChart, purpose: "¿Cómo evoluciona su cumplimiento frente al objetivo?", field_bindings: { Category: "Sprint[Sprint]", Y: ["Tickets[% Cumplimiento SLA]", "Tickets[Objetivo contractual]"] }, comparison_basis: "Objetivo contractual del nivel", color_strategy: measure_match, title: "Cumplimiento por sprint frente a su objetivo contractual" }
          - { id: client_dept, region: dept, kind: barChart, purpose: "¿Qué departamentos le fallan?", field_bindings: { Category: "Departamento[Departamento]", Y: "Tickets[Tickets incumplidos]" }, sort_policy: value_desc, color_strategy: measure_match, title: "Dónde se pierden sus tickets" }
          - { id: client_mix, region: mix, kind: hundredPercentStackedBarChart, purpose: "¿Qué tipo y prioridad de tickets abre?", field_bindings: { Category: "Política SLA[Tipo]", Y: "Tickets[Tickets creados]", Legend: "Política SLA[Prioridad]" }, sort_policy: value_desc, color_strategy: unique, title: "Qué nos pide: tipo y prioridad de sus tickets" }
        space_audit: { content_cell_count: 132, placed_cell_count: 132, empty_cell_pct: 0, unplaced_regions: [], largest_region: { name: trend, pct_of_content: 32 }, balance_rationale: "KPI + semáforo dan el veredicto en dos filas; la tendencia frente al objetivo es la prueba principal; departamentos y mezcla de tickets explican el porqué." }
  interaction_pattern:
    drill_targets: []
    cross_filter_rules: "Filtro cruzado por defecto; slicers Año y Sprint sincronizados en las 4 páginas; Cliente solo en la ficha."
  accessibility:
    alt_text_strategy: "headline+trend: cada alt text repite la conclusión del visual"
    contrast_notes: "Rojo #C0392B y verde #1E7B5C sobre blanco cumplen AA; en el semáforo la celda muestra además el % (no solo el color)."
  theme:
    base: "assets/base.json adaptado"
    user_overrides: "ninguno"
```

## Implementation notes
- SQL: añadir `fecha_medicion` y `penalizacion_atribuida_eur` a `v_ticket_enriquecido` y crear `v_facturacion_sprint`; re-ejecutar 02_create_views.sql.
- Modelo: powerbi-modeling-mcp → TMDL en `03_powerbi/Brujula SLA.SemanticModel/definition`.
- Report: PBIR de las 4 páginas siguiendo el contrato; validar con powerbi-report-author.
- Validation: Desktop abre el `.pbip`; la estudiante introduce la contraseña de PostgreSQL y refresca; medidas cuadran con SQL (balance −287.037 €).
- Screenshots: 4 páginas → `03_powerbi/screenshots/`.
- Risks: credenciales (paso manual); el árbol de descomposición puede necesitar ajuste manual del orden de niveles; Azure Map no se usa.
