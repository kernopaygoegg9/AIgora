# AIgora

## Layout

- `backend/`: Python (uv, FastAPI). Package `aigora`; tests in `backend/tests/`.
- `frontend/`: Vue + Vite + TypeScript (Pinia, Vue Router). Playwright E2E in `frontend/e2e/`.
- `participants.example.toml`, `.env.example`: copy to `participants.toml` / `.env` (both git-ignored). Discussion records go to `data/discussions/` (git-ignored).
- Hot files and their owners: `.scratch/aigora-v1/tickets-overview.md`.
- Architecture notes in `docs/architecture/`: read the matching page before changing the discussion engine (`discussion-engine.md`), a backend↔frontend shape (`contracts.md`), an adapter (`adapters.md`), or test setup (`testing.md`).

## Commands

Run from the repo root unless noted.

- Install: `uv sync --directory backend` and `npm install --prefix frontend`, then once `cd frontend && npx playwright install chromium`.
- Check everything: `npm run check --prefix frontend` (lint, format check, backend pytest, typecheck, build, E2E; stops at the first failure). Run it before reporting work as done.
- Fast check for the TDD loop: `npm run check:fast --prefix frontend` (same without build and E2E).
- CI: `.github/workflows/check.yml` runs the same `npm run check --prefix frontend` on every pull request and every push to `master` (ubuntu, no secrets; Playwright results uploaded as an artifact on failure).
- Lint: `npm run lint --prefix frontend` (ESLint + ruff). Auto-format: `npm run format --prefix frontend` (Prettier, ruff import sort, `ruff format`). Config: `frontend/eslint.config.js`, `frontend/.prettierrc.json`, `[tool.ruff]` in `backend/pyproject.toml`.
- Individual steps below are for running one part on its own.
- Start (backend :8765 + Vite dev server :5173, one command): `npm run dev --prefix frontend`, then open http://127.0.0.1:5173. Vite proxies `/api` and `/ws` to the backend. To move the backend off 8765, set `AIGORA_PORT` in the shell (e.g. `AIGORA_PORT=8775 npm run dev --prefix frontend`); the backend and the Vite proxy both read it. If 5173 is taken, Vite picks the next free port and prints it.
- Backend only: `uv run --directory backend aigora`. It also serves `frontend/dist` after `npm run build --prefix frontend`.
- Backend tests: `uv run --directory backend pytest`. Tests that call a real AI CLI or the real TypeSafe API are marked `real_ai` and skipped by default; run them only when asked or after a CLI upgrade (ADR 0002: each adapter has an isolation canary). All: `uv run --directory backend pytest -m real_ai`. Per adapter (a CLI that is not installed or not logged in is skipped):
  - claude: `uv run --directory backend pytest -m real_ai tests/test_claude_adapter_real.py`
  - codex: `uv run --directory backend pytest -m real_ai tests/test_codex_adapter_real.py`
  - gemini: deferred from v1, see ticket 14 (`.scratch/aigora-v1/issues/14-adapter-gemini.md`)
  - ollama: `uv run --directory backend pytest -m real_ai tests/test_ollama_real.py` (local, no quota; env `AIGORA_TEST_OLLAMA_MODEL`, `AIGORA_TEST_OLLAMA_URL`; default = first installed model at http://127.0.0.1:11434)
  - Jev (TypeSafe): `uv run --directory backend pytest -m real_ai tests/test_jev_client.py` (skipped without `TYPESAFE_API_KEY` in `.env`)
- Frontend type check: `npm run typecheck --prefix frontend`. Production build: `npm run build --prefix frontend` (output `frontend/dist`, served by the backend).
- E2E: `cd frontend && npx playwright test`. Starts its own backend (Fake Adapter participants from `frontend/e2e/participants.e2e.toml`, records in a fresh temp folder) and Vite on free ports picked per run, so several runs can go at once. Pin the ports with `AIGORA_E2E_BACKEND_PORT` / `AIGORA_E2E_FRONTEND_PORT`.
- Assets: app icon / favicons in `assets/brand/` (Vite `publicDir`, served at the site root); avatars in `assets/avatars/`, served by `GET /api/avatars/{file}` (unknown file -> `default.png`).
- Backend env vars: `TYPESAFE_API_KEY`, `AIGORA_HOST`, `AIGORA_PORT`, `AIGORA_PARTICIPANTS_FILE`, `AIGORA_DATA_DIR`, `AIGORA_ENV_FILE` (path of the `.env` to read; default repo-root `.env`).

## User-only actions

Global installs (`npm install -g`, system packages), `git push`, and creating or configuring remote repositories are done by the user. When a task reaches one, stop and report the exact command for the user to run.

## implement-spec: extra rules

- Implementers commit after the first green test and after every green test after that. A usage-limit pause can delete a worktree that has no commits, losing the work.
- The orchestrator merges an implementer's branch with `bash scripts/merge-ticket.sh <branch> --feature <slug> --ticket <NN>`, run on the integration branch with a clean working tree. It merges with `--no-ff`, runs the hot-file check and `npm run check --prefix frontend`, and keeps the merge commit only if both pass. Exit 0: merged and checked. Exit 1: hot-file or check failure; the branch is reset to its pre-merge commit. Exit 2: usage error, dirty tree, or another merge failure. Exit 3: conflict; the merge is aborted. Dispatch a merger subagent only on exit 3. `AIGORA_MERGE_CHECK_CMD` overrides the check command (for example `npm run check:fast --prefix frontend` for a quick dry run).

## Agent skills

### Issue tracker

Issues and specs are local markdown files under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Uses the five default triage labels (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
