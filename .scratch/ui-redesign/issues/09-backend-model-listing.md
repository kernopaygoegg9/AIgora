# 09: 後端：各 Adapter 列出可用模型

Status: resolved

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

- [x] claude：固定清單 `fable`、`opus`、`sonnet`、`haiku`，`free_text = true`
- [x] codex：執行 `codex debug models`，取 `visibility == "list"` 的模型並依 `priority` 排序，`free_text = true`；確認並在 Comments 記下這個指令是否讀取使用者的 `~/.codex/config.toml`，以及沒有網路時的行為；CLI 不存在、逾時（10 秒）、輸出無法解析時都要回傳 `error`
- [x] ollama：`GET /api/tags`，label 包含 `parameter_size`，`free_text = false`；Ollama 沒在執行時回傳 `error`
- [x] fake：讀 `options.models`，`free_text = false`
- [x] 依（Adapter、options）快取 5 分鐘；不可用的參與者回傳空清單，不執行列模型
- [x] `GET /api/participants` 中列模型和可用性檢查一起同時執行，任何一個 Adapter 出錯都不會讓整個端點失敗
- [x] `tests/test_ws_messages.py` 的 Python／TypeScript 契約比對通過
- [x] `uv run --directory backend pytest`、`npm run typecheck --prefix frontend` 與全部 E2E 通過

## Comments

### 2026-10-20 實作紀錄（ticket 09 session）

**`codex debug models` 的行為**（codex-cli 0.162.1，本機實測，沒有呼叫模型）：

- **會讀取使用者的 `~/.codex/config.toml`**（實際是 `$CODEX_HOME/config.toml`）。`--help` 寫明 `-c` 是覆寫「原本會從 `~/.codex/config.toml` 載入的值」；把 `CODEX_HOME` 指到一個 config 語法錯誤的資料夾時，指令 exit 1，stderr 是 TOML 解析錯誤。這個子指令**不支援** `--ignore-user-config`（exit 2，unexpected argument）。只有 `--bundled` 不受壞 config 影響，但它也跳過線上更新。
  - 決定：照原樣執行 `codex debug models`。config 壞掉時回傳 `models_error`（帶 stderr 最後 300 字），而且仍然可以自行輸入模型。發言時 Adapter 仍然用 `--ignore-user-config`，所以隔離不受影響；列模型只讀目錄，不呼叫模型、不花額度。
- **離線時**：把 `~/.codex/models_cache.json` 暫時移走，並把 `HTTP(S)_PROXY` 指到無效位址模擬離線，指令約 5 秒後 exit 0，退回 CLI 內建的目錄（內容和線上目錄稍有不同，例如多了 `gpt-5.5`、排序不同）。有 `models_cache.json` 時直接用快取（約 1.3 秒）。所以 10 秒逾時足夠涵蓋離線的情況。測試後已把快取檔放回原處。

**實作決定**：

- 快取在 `participant_info.model_choices_of`（因為 `get_adapter()` 每次建立新的 Adapter），key 是（adapter id、`options` 的 JSON），5 分鐘。**只快取沒有 `error` 的結果**，這樣啟動 Ollama 或修好 codex config 後，下一次請求就會看到清單。
- `GET /api/participants`：每個參與者的列模型和可用性檢查同時啟動；可用性檢查結果是不可用時，取消還在執行的列模型（codex 的子程序會被 `kill_tree`），回傳 `models = []`、`free_text_model = false`、`models_error = null`。所有參與者之間也是同時查詢。任何 Adapter 的 `list_models` 拋出例外都轉成 `models_error`，端點不會失敗。
- codex 出錯時 `free_text = true` 不變（仍然可以自行輸入）；ollama 一律 `free_text = false`，label 是 `name (parameter_size)`，沒有 `parameter_size` 時只有 name。
- fake 的 `options.models`：字串陣列，`validate_options` 檢查型別；`id = label = 字串`。
- 測試：`test_participant_models.py`（API 層：清單、不可用、錯誤與例外、快取 5 分鐘、和可用性檢查同時執行）、各 Adapter 的 `list_models` 單元測試（codex 用 `fake_codex_cli.py` 新增的 `debug_models` 情境）、`real_ai`：`test_codex_adapter_real.py`、`test_ollama_real.py` 各一個（本機已跑過，都通過）。
- 驗證：`uv run --directory backend pytest` 264 passed；`npm run typecheck --prefix frontend` 通過；`npx playwright test` 33 passed；`pytest -m real_ai -k model_list` 2 passed。
