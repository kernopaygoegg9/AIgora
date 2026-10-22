# Testing seams and gotchas

Commands are in `AGENTS.md`; this page is where to plug in.

## Backend (`backend/tests/`)

- `conftest.py`: fixtures `client`, `data_dir`, `write_participants(toml)`, `cli_processes`; helpers `fake_participant(id, name, **options)`, `run_discussion(client, question, settings)`.
- Mid-discussion client messages: `receive_until(ws, received, predicate)` in `test_interject_and_stop.py`.
- Fake Adapter options drive scenarios (delays, failures per round, `cancel_log` to observe cancellation); see `adapters/fake.py`.
- CLI adapters: inject a scripted fake CLI (`fake_claude_cli.py`, `fake_codex_cli.py`, `fake_gemini_cli.py`) via the adapter's `command=[sys.executable, script]`. To prove a tree kill, have the fake spawn a grandchild that writes a heartbeat file and assert the heartbeat stops. Fixtures that run a fake CLI depend on `cli_processes` (conftest): the fakes record every pid they start in `AIGORA_TEST_PID_DIR`, and teardown ends any still running, even when the test failed. The reaper lives in `process_reaper.py` (`reap_cli_processes(pid_dir)`, `alive(pid)`, `recorded_pids(pid_dir)`). A new fake CLI imports `record_pid` / `start_heartbeat` from `fake_cli_support.py` (it runs as a script, so its own folder is on `sys.path`) and calls `record_pid` for itself and each child.
- Jev: monkeypatch `aigora.discussion.judges.create_jev_client`; `test_consensus_jev.py` has fixtures `env_file` and `fake_jev`.
- `create_app(frontend_dist=None)` keeps tests independent of a built `frontend/dist`.

## Frontend E2E (`frontend/e2e/`)

- Playwright starts its own backend and Vite with `participants.e2e.toml` (Fake participants only: `fake-slow`, `fake-offline`, `fake-echo`, `fake-sleepy`, `fake-down`, `fake-flaky`, …). `playwright.config.ts` picks two free ports (unless `AIGORA_E2E_BACKEND_PORT` / `AIGORA_E2E_FRONTEND_PORT` are set) and a fresh temp records folder (`aigora-e2e-*`, removed by `e2e/global-teardown.ts` after the run unless `AIGORA_E2E_DATA_DIR` was set), and writes them back to `process.env` so the workers, which reload the config, see the same values. Parallel runs do not collide. In CI it also writes the html report to `playwright-report/`.
- Store tests (`discussion-store.spec.ts`) run in Node without a page.
- Judge B UI is tested with `page.routeWebSocket` because the E2E backend has no TypeSafe key.
- Earlier tests leave records in history, so match nav links with `exact: true`.

## Vue gotcha

vue-router reuses the `DiscussionPage` instance between `/` and `/discussions/:id`; `onMounted` does not rerun. React to `props.id` with `watch(..., { immediate: true })`.
