# Discussion engine

How a discussion runs, in `backend/aigora/discussion/`. Terms follow `GLOSSARY.md`; the rules come from `.scratch/aigora-v1/spec.md` (失敗與控制規則).

## Pieces

- `engine.py` `DiscussionEngine(question, settings, participants, mode, order, store, send, first_round=None, derived_from=None)`; `await run()`. The `DiscussionRecord` (`engine.record`) is the single state; `view()` builds the read-only `DiscussionView` handed to modes and judges.
- `interfaces.py`: `DiscussionMode`, `ConsensusJudge`, `SpeakingOrder` ABCs, `DiscussionView` / `RoundView`, and the decisions `ContinueRound | ExtraCalls | Finish` (optionally carrying a `JudgeReport` / `ConfirmationReport` for the engine to emit).
- Registries: `modes.py` `MODES` (`ask`, `consensus`), `judges.py` `JUDGES` (`stance_vote` = 方式 A, `jev` = 方式 B), `orders.py` `SPEAKING_ORDERS` (only `parallel`; `sequential` is listed but not implemented).
- `settings.py` `resolve_settings(StartSettings, ParticipantsConfig) -> DiscussionSettings`: fills defaults, rejects fewer than `MIN_PARTICIPANTS` (2), unknown or unavailable judges, and resolves per-participant `models` / `extra_participants`. Raises `SettingsError`.
- `prompt_builder.py` `build_prompt(view, pid, instructions)`: system prompt + question + all earlier turns, drafts and interjections + the mode's instructions.
- `store.py` `DiscussionStore`: `save` / `list` / `read`; files `<data dir>/<YYYYMMDD-HHMMSS-6hex>.json` (`AIGORA_DATA_DIR`).
- `derived.py`: ask → consensus. `load_source(store, id)` and `derived_engine(source=..., **kwargs)`, which passes the ask's round 1 as `first_round`.
- Socket handler `api/handlers/discussion_socket.py` runs `engine.run()` as a task and reads `interject` / `stop` meanwhile; a browser disconnect only cancels the task.

## One round

1. `_run_round`: every active participant's turn via `_run_call` (streams `turn_*`; timeout → `turn_failed` kind `timeout`; adapter `Failed` → `turn_failed`). Finished turns land in the record immediately.
2. `_hand_over_if_moderator_failed`: the moderator's own failed turn hands the role to the next active participant.
3. `_remove_failing`: a participant whose normal turns in the last `FAILED_ROUNDS_TO_REMOVE` (2) rounds all failed is removed (`participant_removed`). Extra-call failures never count. Under 2 active → finish `insufficient_participants`.
4. `mode.after_round(view, results)` returns a decision. `ExtraCalls` run through `_run_extra_calls` (moderator draft, summary, final result, confirmations) and the mode is asked again with their results; `_apply_reports` stores and emits judge / confirmation results.

Event order per round: turns → `confirmation_result` → `judge_result` → extra-call `turn_*` → `draft_created` → `round_completed` (→ `discussion_finished`).

## Consensus mode

- Round 1: free answers. From round 2: respond to the previous draft and end with a stance line (`stance.py` `parse_stance`).
- 方式 A (`stance_vote`): judged first each round from 2 on, on round N's stances against round N-1's draft. Reached → the voted draft is the result.
- 方式 B (`jev`): `JevJudge` asks TypeSafe for a consensus probability (`aigora/jev_client.py`; key from `env.py` `backend_env()`, never sent to the frontend). Over the threshold → a `confirmation` call to every participant; all agree → moderator writes `final_result`; otherwise disagreements carry into the next round (`pending_disagreements` = previous round only). A confirming round emits two `judge_result`s; the record keeps all in `round.judge_history` (`judge` = last). A Jev error counts as not reached.
- Not reached at `max_rounds` → moderator `no_consensus_summary`, else moderator `draft`.
- Moderator calls (`MODERATOR_PURPOSES`: draft, final_result, no_consensus_summary) that fail hand over the role and are retried once by each new moderator per round (`ConsensusMode._tried`). If every moderator fails `final_result`, the previous draft becomes the result.

## Interject and stop

- `engine.interject(text)` queues for the next round (`applies_to_round`), emits `interjection_queued`; rejected when blank, finished, or after `stop()`. Every later prompt includes it.
- `engine.stop()` cancels the inner task; each cancelled call gets `turn_failed` (reason `STOPPED_REASON`), normal turns keep their partial text as `failed`, then the record is saved with outcome `stopped`.
