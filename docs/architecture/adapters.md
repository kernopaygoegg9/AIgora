# Adapters

An adapter drives one AI CLI (ADR 0001) and removes every local tool except web search (ADR 0002). The exact flags live in each module's docstring; this page holds what the code does not confess.

## Interface

`backend/aigora/adapters/base.py`: `Adapter` with `capabilities(participant)`, `async check_availability(participant)` (must not spend quota), `async run_turn(request)` (async generator: `Delta`* then exactly one `Completed` or `Failed`; expected errors are yielded as `Failed`, never raised), `async list_models(participant)` (no quota; returns `ModelChoices`), optional `validate_options(options)`. Failure kinds are in `aigora/domain.py`.

A new adapter is a module `adapters/<id>.py` with a module-level `create_adapter()`, plus its identifier in `adapters/registry.py`. `adapters/fake.py` is the reference implementation (options table in its docstring).

## Subprocess rules

- Pass the prompt on stdin: npm `.cmd` shims on Windows break quoting and command-line length.
- Cancellation must kill the whole process tree: `adapters/subprocesses.py` `process_group_options()` + `kill_tree(proc)` (`taskkill /T /F` on Windows, process group elsewhere). `proc.kill()` alone leaves the shim's node child running.

## Per adapter

- **claude**: availability via `claude auth status --json`. The child env drops nested-session variables (`CLAUDECODE`). Model list is a fixed alias list plus free text (the CLI cannot list models).
- **codex**: availability via `codex login status`; models via `codex debug models`. Web search is `-c web_search="live"` because `codex exec` has no `--search`. Never disable the `code_mode_host` feature: web search stops working.
- **ollama**: local HTTP API (`/api/generate`, `/api/tags`), no web access. `model` is required; test seam `OllamaAdapter(transport=httpx.MockTransport(...))`.
- **gemini**: deferred from v1. Google rejects personal sign-in, and the isolation policy failed against the real CLI; the open bugs are in `.scratch/aigora-v1/issues/14-adapter-gemini.md`. Keep it disabled until its canary passes.
- **agy (Antigravity CLI)**: not an adapter. Its terms forbid wrapping it with a consumer plan; see `.scratch/agy-adapter/spike.md` before reconsidering.

## Real-CLI tests

Each adapter has a real-CLI test file (`tests/test_<id>_adapter_real.py`, `tests/test_ollama_real.py`; marked `real_ai`, skipped by default): a canary (a random file outside the workspace must not appear in the output) and smoke tests (stance line, web search with a URL). A canary is only meaningful when the turn ended in `Completed`; a CLI that fails to start produces no output and passes vacuously. Rerun them after every CLI upgrade.

## TypeSafe (Jev)

Not a CLI (ADR 0001 exception). PyPI `typesafe-sdk` (not `typesafe` or `typesafe-ai`); docs index https://docs.typesafe.ai/llms.txt. Client in `aigora/jev_client.py`.
