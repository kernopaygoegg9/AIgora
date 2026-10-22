# 03: 真實 Adapter 測試共用 helper

**Type:** 程式（tdd）

**What to build:** 真實 Adapter 的 canary 只有在發言以 `Completed` 結束時才算通過；四個 Adapter 的真實測試共用同一套檢查。

**Scope:**
- 新增 `backend/tests/real_adapter.py`（`run_real_turn`、`assert_canary_not_leaked`，見 spec）。
- 用 Fake Adapter 為 helper 寫一般測試（非 `real_ai`）：`Completed` 時回傳文字；`Failed` 結尾時測試失敗；不可用時 skip。
- `test_claude_adapter_real.py`、`test_codex_adapter_real.py`、`test_gemini_adapter_real.py`、`test_ollama_real.py` 改用 helper。
- `docs/architecture/adapters.md`「Real-CLI tests」段改指向 helper。

**Blocked by:** 01

**Status:** resolved

- [x] helper 的一般測試涵蓋：完成、`Failed` 結尾、不可用三種情況，且在 `check:fast` 中執行
- [x] gemini 的 canary 在 CLI 失敗時不再通過（以 helper 測試證明；不必跑真實 gemini）
- [x] 四個真實測試檔都改用 helper；`uv run --directory backend pytest -m real_ai --collect-only` 收集到的測試數量與改動前相同
- [x] 不執行任何 `real_ai` 測試（不花額度）

## Comments

- 2026-10-22 merged (`check:fast` green, 300 passed; `real_ai --collect-only` 14 before and after). Helper tests in `backend/tests/test_real_adapter_helper.py`.
