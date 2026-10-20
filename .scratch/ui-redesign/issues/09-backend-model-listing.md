# 09: 後端：各 Adapter 列出可用模型

Status: ready-for-agent

Blocked by: —

**What to build:** 每個 Adapter 都能列出可選的模型，`GET /api/participants` 為每個參與者帶出模型清單、是否可以自行輸入，以及載入失敗的原因。不呼叫任何模型，也不花額度。見 spec「參與者與模型選擇」的「列出模型」段落，以及 `model-listing-findings.md`。

**Scope:**
- `backend/aigora/adapters/base.py`：新增 `ModelOption`、`ModelChoices` 與 `Adapter.list_models()`（預設回傳「沒有清單、不可自行輸入」）。
- `backend/aigora/adapters/claude.py`、`codex.py`、`ollama.py`、`fake.py`：**只能新增** `list_models`（fake 另外在 `validate_options` 中接受 `models`）。不能修改隔離參數、`run_turn` 或可用性檢查；不能碰 `gemini.py` 與 `registry.py`。
- `backend/aigora/participant_info.py`、`backend/aigora/api/handlers/participants.py`、`backend/aigora/api/http_models.py`（`ParticipantInfo` 新增 `models`、`free_text_model`、`models_error`）、`frontend/src/contracts/http.ts`（同步）。
- `frontend/e2e/participants.e2e.toml`：替 Fake A、Fake B 加上 `options.models`（供 11 使用）。
- `participants.example.toml`：註解說明在介面上可以換模型。
- 測試：`backend/tests/` 中新增或擴充 adapter、participants 相關的測試；`real_ai` 標記的真實 CLI 測試（claude 不需要，codex 與 ollama 各一個）。
- 不修改 `messages.py`、`messages.ts`、`settings.py`、`discussion_socket.py`、`record.py`（屬於 10），也不修改任何前端元件。

- [ ] claude：固定清單 `fable`、`opus`、`sonnet`、`haiku`，`free_text = true`
- [ ] codex：執行 `codex debug models`，取 `visibility == "list"` 的模型並依 `priority` 排序，`free_text = true`；確認並在 Comments 記下這個指令是否讀取使用者的 `~/.codex/config.toml`，以及沒有網路時的行為；CLI 不存在、逾時（10 秒）、輸出無法解析時都要回傳 `error`
- [ ] ollama：`GET /api/tags`，label 包含 `parameter_size`，`free_text = false`；Ollama 沒在執行時回傳 `error`
- [ ] fake：讀 `options.models`，`free_text = false`
- [ ] 依（Adapter、options）快取 5 分鐘；不可用的參與者回傳空清單，不執行列模型
- [ ] `GET /api/participants` 中列模型和可用性檢查一起同時執行，任何一個 Adapter 出錯都不會讓整個端點失敗
- [ ] `tests/test_ws_messages.py` 的 Python／TypeScript 契約比對通過
- [ ] `uv run --directory backend pytest`、`npm run typecheck --prefix frontend` 與全部 E2E 通過

## Comments
