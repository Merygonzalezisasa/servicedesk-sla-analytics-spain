# Brújula Soporte IT — Service Desk SLA Analytics

> 🚧 **En construcción.** Fase actual: 1 (ETL). Este README se completa en la Fase 5.

Análisis end-to-end del **cumplimiento de SLA** de un service desk B2B en España: cuánta facturación
se pierde y se gana por el bonus/penalización de los contratos, y qué lo explica (carga de trabajo,
escalados, vacaciones de verano, festivos y calor).

**Stack:** Python · PostgreSQL · Power BI · Jupyter

## Origen de los datos

- **Sintéticos (generados):** tickets, clientes, agentes, vacaciones y contratos de la empresa
  ficticia *Brújula Soporte IT*. Se generan con reglas de SLA y patrones habituales en un service
  desk, con una semilla fija para que sean reproducibles.
- **Reales:** clima diario de Madrid ([Open-Meteo](https://open-meteo.com/)) y festivos nacionales y
  de la Comunidad de Madrid ([Nager.Date](https://date.nager.at/)).

*Brújula Soporte IT es una empresa ficticia y no representa a ninguna organización real.*

## Documentación del proyecto

- [FICHA.md](FICHA.md) — decisiones del proyecto: alcance, modelo de datos, preguntas de negocio
- [SETUP.md](SETUP.md) — cómo instalar y verificar el entorno
- [PROGRESO.md](PROGRESO.md) — bitácora de avance

## Autora

**Rosmary González** — Analista de datos · [GitHub](https://github.com/Merygonzalezisasa)
