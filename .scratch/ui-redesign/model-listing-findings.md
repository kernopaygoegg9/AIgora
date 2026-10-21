# 調查：各 Adapter 如何列出可用模型

日期 2026-10-20。只看 CLI 的 help、本機目錄與 Ollama HTTP API，**沒有呼叫任何模型**，沒有花額度。

| Adapter | 版本 | 列出模型的方式 | 結論 |
|---|---|---|---|
| claude | Claude Code 2.1.286 | **沒有**列出模型的子指令（`claude --help` 的 Commands 只有 agents、auth、doctor、mcp、plugin 等）。`--model` 的說明是：可以給「最新模型的別名」，例如 `fable`、`opus`、`sonnet`，或是模型的完整名稱。 | 固定清單：`fable`、`opus`、`sonnet`、`haiku` 四個別名，另外允許自行輸入完整名稱（例如 `claude-opus-5-5`）。帳號方案不支援的模型要到發言時才會失敗（`failed`），沒有辦法事先檢查。 |
| codex | codex-cli 0.162.1 | `codex debug models`：「Render the raw model catalog as JSON」，約 1.5 秒，不需要網路以外的權限。輸出 `{"models": [...]}`，每筆有 `slug`、`display_name`、`description`、`visibility`（`list` / `hide`）、`priority`、`supported_in_api`、`default_reasoning_level` 等欄位。 | 呼叫 `codex debug models`，只取 `visibility == "list"` 的模型，依 `priority` 排序；`id = slug`、`label = display_name`。也允許自行輸入（目錄可能過時）。本機目前列出 GPT-6.1-Sol、GPT-6-Astra、GPT-6-Sol、GPT-6-Luna、GPT-5.6-Sol、GPT-5.6-Terra、GPT-5.6-Luna。**實作時要確認**：這個指令是否會讀取使用者的 `~/.codex/config.toml`（Adapter 執行發言時會忽略使用者設定），以及離線時的行為。 |
| ollama | 0.40.4 | `GET {base_url}/api/tags` 回傳 `{"models": [{"name", "model", "details": {"parameter_size", "family", ...}}]}`；Adapter 的可用性檢查本來就在呼叫它。 | 列出已安裝的模型：`id = name`、`label = name（parameter_size）`。不允許自行輸入（沒安裝的模型一定會失敗）。Ollama 沒在執行時回傳錯誤原因。 |
| fake | — | — | 從 participant 的 `options.models`（字串陣列，可省略）讀取，供 E2E 使用。 |
| gemini | — | — | 不在範圍內（v1 暫不使用，另有 session 處理），沿用預設：不提供清單、不允許自行輸入。 |

## 對設計的影響

- 列表的來源分成三種：固定清單（claude）、CLI 目錄（codex）、本機服務（ollama）。共通介面是 `list_models(participant) -> ModelChoices(models, free_text, error)`，不支援的 Adapter 預設回傳「沒有清單、不可自行輸入」。
- codex 與 ollama 的清單要花時間或可能失敗，所以結果快取 5 分鐘，失敗時在 UI 顯示原因，而且仍然可以用預設模型。
- 列模型和可用性檢查一樣，不能花額度。
