# AIgora

## Layout

- `backend/`: Python (uv, FastAPI). Package `aigora`; tests in `backend/tests/`.
- `frontend/`: Vue + Vite + TypeScript (Pinia, Vue Router). Playwright E2E in `frontend/e2e/`.
- `participants.example.toml`, `.env.example`: copy to `participants.toml` / `.env` (both git-ignored). Discussion records go to `data/discussions/` (git-ignored).
- Hot files and their owners: `.scratch/aigora-v1/tickets-overview.md`.

## Commands

Run from the repo root unless noted.

- Install: `uv sync --directory backend` and `npm install --prefix frontend`, then once `cd frontend && npx playwright install chromium`.
- Start (backend :8765 + Vite dev server :5173, one command): `npm run dev --prefix frontend`, then open http://127.0.0.1:5173. Vite proxies `/api` and `/ws` to the backend.
- Backend only: `uv run --directory backend aigora`. It also serves `frontend/dist` after `npm run build --prefix frontend`.
- Backend tests: `uv run --directory backend pytest`. Tests that call a real AI CLI or the real TypeSafe API are marked `real_ai` and skipped by default; run them only when asked or after a CLI upgrade: `uv run --directory backend pytest -m real_ai`.
- Frontend type check: `npm run typecheck --prefix frontend`.
- E2E: `cd frontend && npx playwright test`. Starts its own backend (:8766, Fake Adapter participants from `frontend/e2e/participants.e2e.toml`) and Vite (:5174).
- Backend env vars: `TYPESAFE_API_KEY`, `AIGORA_HOST`, `AIGORA_PORT`, `AIGORA_PARTICIPANTS_FILE`, `AIGORA_DATA_DIR`, `AIGORA_ENV_FILE` (path of the `.env` to read; default repo-root `.env`).

## Agent skills

### Issue tracker

Issues and specs are local markdown files under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Uses the five default triage labels (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
