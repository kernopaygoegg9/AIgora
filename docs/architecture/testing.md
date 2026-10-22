# Testing seams and gotchas

Commands are in `AGENTS.md`; this page is where to plug in.

## Backend (`backend/tests/`)

- `conftest.py`: fixtures `client`, `data_dir`, `write_participants(toml)`; helpers `fake_participant(id, name, **options)`, `run_discussion(client, question, settings)`.
- Mid-discussion client messages: `receive_until(ws, received, predicate)` in `test_interject_and_stop.py`.
- Fake Adapter options drive scenarios (delays, failures per round, `cancel_log` to observe cancellation); see `adapters/fake.py`.
- CLI adapters: inject a scripted fake CLI (`fake_claude_cli.py`, `fake_codex_cli.py`, `fake_gemini_cli.py`) via the adapter's `command=[sys.executable, script]`. To prove a tree kill, have the fake spawn a grandchild that writes a heartbeat file and assert the heartbeat stops.
- Jev: monkeypatch `aigora.discussion.judges.create_jev_client`; `test_consensus_jev.py` has fixtures `env_file` and `fake_jev`.
- `create_app(frontend_dist=None)` keeps tests independent of a built `frontend/dist`.

## Frontend E2E (`frontend/e2e/`)

- Playwright starts its own backend on :8766 and Vite on :5174 with `participants.e2e.toml` (Fake participants only: `fake-slow`, `fake-offline`, `fake-echo`, `fake-sleepy`, `fake-down`, `fake-flaky`, …). Two runs at once collide on those ports.
- Store tests (`discussion-store.spec.ts`) run in Node without a page.
- Judge B UI is tested with `page.routeWebSocket` because the E2E backend has no TypeSafe key.
- Earlier tests leave records in history, so match nav links with `exact: true`.

## Vue gotcha

vue-router reuses the `DiscussionPage` instance between `/` and `/discussions/:id`; `onMounted` does not rerun. React to `props.id` with `watch(..., { immediate: true })`.
