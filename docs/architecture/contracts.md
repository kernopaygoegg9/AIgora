# Contracts between backend and frontend

Every shape below exists twice, Python and TypeScript. `backend/tests/test_ws_messages.py` compares the field sets of each pair, so change both sides together and run it.

| Shape | Python | TypeScript |
|---|---|---|
| WebSocket messages | `backend/aigora/api/messages.py` | `frontend/src/contracts/messages.ts` |
| HTTP responses | `backend/aigora/api/http_models.py` | `frontend/src/contracts/http.ts` |
| Discussion record | `backend/aigora/record.py` | `frontend/src/contracts/record.ts` |

## WebSocket

- `parse_client_message(dict)` validates client messages; `to_wire(model)` serialises server ones. Every server message carries `discussion_id` (null on an `error` before a discussion starts) and a per-connection `seq` from 1.
- `turn_*` messages carry `purpose` (`turn`, or an extra call: `draft`, `confirmation`, `final_result`, `no_consensus_summary`), so moderator calls stream like turns.
- `start` takes `StartSettings`; omitted fields come from `[defaults]` in `participants.toml`. `models` (participant id → model for this discussion) and `extra_participants` (ad-hoc participants, e.g. a second Claude) are optional; omitting both behaves like v1. `from_discussion_id` starts a consensus from a finished ask.
- `discussion_finished` has `outcome`, `reason`, and `result` (`kind`: answers / consensus / no_consensus).

## Record

- `SCHEMA_VERSION = 2` adds the resolved `models` / `extra_participants` and `judge_history`. History must keep reading schema 1 records.

## Frontend side

- Live state: `frontend/src/stores/discussion.ts` `useDiscussionStore().applyMessage(msg)` applies every server message.
- Socket: `frontend/src/api/discussionSocket.ts` `openDiscussionSocket(onMessage)` → `start / interject / stop / close`.
- The read-only record view (`components/history/RecordView.vue`) renders the record JSON directly and never touches the live store.

## Configuration

- `backend/aigora/config.py` `load_participants(path)`: ids unique, adapter registered, adapter `options` validated at load (`ConfigError(path, line, message)`). Several participants may share one adapter, each with its own `model` / `persona` / `avatar`.
- `backend/aigora/env.py` `backend_env()`: `.env` (`AIGORA_ENV_FILE`) overlaid by non-empty process env, re-read on every call. Secrets such as `TYPESAFE_API_KEY` stay in the backend; `/api/options` sends availability and a reason only.
