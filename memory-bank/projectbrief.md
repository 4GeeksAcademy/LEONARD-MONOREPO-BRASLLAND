# Project Brief — Brasaland Digital

Sources: `CONTEXT.md`, `Context-company.md`, `company-choice.md`.

## The company
Brasaland is a grilled-food restaurant chain founded in 2008 in Medellín, Colombia. It has 14 company-owned
restaurants in Colombia (`COL-01`..`COL-10`) and Florida (`FLA-01`..`FLA-04`), about 115 employees and about
USD 6M annual revenue. HQ is in Medellín; Miami hosts a commercial and operations office. CEO: Mariana Restrepo.

Areas and leads: Restaurant Operations (Felipe Guerrero), Procurement and Suppliers (Lucía Fernández, ~20
suppliers), Marketing and Digital Experience (Camila Ospina), People and Culture (Ashley Turner), Technology
(CTO Nicolás Park). This repo is built as the Brasaland Digital internal team.

## The problem
Each location runs its own kitchen, staff and supply orders with little visibility from HQ. Concretely
(per the briefing and `company-choice.md`): ingredient orders run through WhatsApp, POS systems are
disconnected, there is no central API, incidents are logged in a shared spreadsheet, leadership decides from
delayed PDF reports, procurement negotiates per market without consolidated spend data, and the customer side
has little data (website without online ordering, weak app rating, low-adoption physical loyalty card).

## Objectives of this repo
1. Replace the incident spreadsheet with validated data and an operations view (incident analyzer,
   incident manager in the backoffice).
2. Centralise supplier data (supplier directory) and ingredient inventory (inbound/outbound orders).
3. Give staff authenticated access to internal tools (auth with password recovery).
4. Provide a public corporate site and an internal backoffice, each with its own layout.
5. Keep the work reproducible for agents: memory bank, `AGENTS.md`, rules and skills (Milestone 4).

## Domain vocabulary (use these terms)
- Incident categories: `CUSTOMER_COMPLAINT`, `EQUIPMENT`, `SUPPLY`, `FOOD_QUALITY`, `STAFF`.
- Incident status: `OPEN`, `CLOSED`, `DISCARDED`. `CLOSED` requires `satisfaction_score` 1–5.
- IDs: incident `BRS-XXXXXX`, customer `CLI-XXXXXX`, reporter `MGR-XX`, location `COL-01`..`FLA-04`.
- Reference dataset: `incidents-brasaland.csv` (100 rows, 96 valid, average score 3.46).
