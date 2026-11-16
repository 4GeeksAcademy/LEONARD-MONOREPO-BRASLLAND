# Progress

Last updated on branch `milestone-4`.

## Done (present in the repo)
- Milestone 1: static corporate landing (`index.html`), application form (`application.html`, `validation.js`), navigator (`project-shell.html`).
- Milestone 2: TypeScript business logic in `components/milestone2/src`.
- Milestone 3: `uis/talent-pipeline-tracker` (Next.js), with auth screens and password recovery.
- Supplier directory (TinyDB), auth with password recovery, incident analyzer (`packages/incident_analysis`) and centralized incident manager.
- Milestone 5: inventory on Supabase + SQLModel with backoffice inventory view.

## In progress — Milestone 4
- [x] Branch `milestone-4` created.
- [x] `memory-bank/` (this folder).
- [ ] Root `AGENTS.md` (4+ step pre-commit workflow).
- [ ] `.agents/rules/` with at least one rule and explicit scope.
- [ ] Own skill in `.agents/skills/<name>/SKILL.md`.
- [ ] `uis/website` (Next.js + TypeScript, Milestone 1 sections as typed components).
- [ ] `uis/backoffice` own layout + Milestone 2 output on screen, imported from `components/milestone2`.
- [ ] PR with website and backoffice screenshots and link to `AGENTS.md`.

## Outstanding after Milestone 4 (in order)
1. Backend Architecture Proposal: `docs/ARCHITECTURE_PROPOSAL.md` (does not exist yet).
2. Containerization (compose exists but is incomplete/undocumented; `infra/` has only READMEs).
3. Frontend Performance Audit.

## Known gaps (documented, not scheduled for Milestone 4)
- Two persistence models (TinyDB and Supabase).
- No CORS middleware in `services/`.
- Inconsistent route prefixes.
- Several backend test files fall outside pytest `testpaths`.
- `services/admin-api` is a stub.
