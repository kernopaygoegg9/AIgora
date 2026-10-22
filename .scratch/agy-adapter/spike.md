# Spike：Antigravity CLI（`agy`）能否成為 AIgora 參與者

Ticket：`issues/01-spike.md`。日期：2026-10-20。機器：Windows 11 Pro 10.0.26300。

## 進度

- **階段 1（桌面研究，已完成）**：官方文件 antigravity.google/docs、官方條款 antigravity.google/terms、GitHub issue #76 / #548。
- **階段 2（實機測試，未執行）**：`agy` 不在 PATH（`where agy` 找不到、bash `agy: command not found`）。安裝與登入由使用者決定；見文末「待使用者決定」。

## 結論先講

**用個人 Google 帳號：放棄（drop）。** 官方 FAQ 明文寫著，把 `agy` 包進第三方應用程式在消費者方案下不支援：

> "Wrapping agy inside third-party coding agents or applications … is not supported under consumer plans."
> — antigravity.google/docs/faq

條款第 6 條把「使用第三方軟體、工具或服務存取本服務」列為違約，可停權（antigravity.google/terms）。AIgora 正是包住 `agy` 的第三方應用程式，所以這和 ADR 0001「沿用使用者已登入的訂閱帳號」的前提直接衝突，風險是使用者的 Google 帳號被停權。技術上能不能隔離都不改變這個結論。

**用 API key（`GEMINI_API_KEY` + `modelProvider: "gemini"`）：技術上可能，但目前不建議做。** FAQ 對第三方工具建議改用 Gemini Enterprise 或 Google AI Studio API key，所以 API key 路線不在上述限制內（API key 走 Gemini API 條款，本 spike 未逐條查證）。但：
1. 這等於要使用者另外申請 API key、按用量付費，失去 ADR 0001 選 CLI 的主要理由；若要走 API key，直接呼叫 Gemini API 可能比驅動一個 coding agent 更簡單、更好隔離（但那違反 ADR 0001，需要新 ADR）。
2. 隔離需要的「忽略使用者設定」沒有官方旗標或環境變數，只能靠把 `HOME`/`USERPROFILE` 指向暫存資料夾（未驗證）。
3. 尚未實測 Windows pipe 輸出、canary、取消。

建議：**現在不做 Adapter。** 如果使用者願意用 AI Studio API key 試，再做階段 2 的實測（約 4 次很短的模型呼叫）。

## 各問題

### 1. Headless 輸出（stdout 為 pipe）

文件結果（antigravity.google/docs/cli/headless）：
- `agy -p "<prompt>" --output-format stream-json`；`--input-format stream-json` 可從 stdin 讀 prompt（每行 `{"event":"user","message":{"content":"..."}}`，關閉 stdin 即結束、exit 0）。另有 `--model`、`--effort`、`--print-timeout`（預設 5m）。
- 回覆在 stdout；錯誤、認證提示、權限通知在 stderr。
- stream-json 是 NDJSON，三種事件：
  - `init`（一次）：`cwd`、`tools`、`permission_mode`、`model`… — **`tools` 欄位可用來在執行時驗證工具清單**，Adapter 可在看到非預期工具時直接中止。
  - `step_update`：`step_type`（`user_input` / `agent_response` / `tool` / `checkpoint`）、`state`（`ACTIVE` / `DONE`）、`text_delta`、`tool_name`、`tool_info`（`name`、`parameters`、`output`、`error`）、`subagent_info`。串流文字 = `agent_response` 的 `ACTIVE` 事件的 `text_delta`。
  - `result`（一次）：與 `--output-format json` 的 envelope 相同：`status`（`SUCCESS` / `ERROR` / `CANCELED` / `INTERRUPTED` / …）、`response`、`error`、`usage`。**沒有獨立的 error 事件**，失敗是 `status: ERROR`。
- 未登入時在非互動環境回 `authentication required` 錯誤，不會卡住（文件未給 exit code）。

上游 issue #76（Windows pipe 空 stdout、exit 0）：2026-07-12 由維護者以 1.1.1 關閉。修正：1.0.15 修 Windows 寫到 `CONOUT$` 的問題；1.1.1 讓伺服器錯誤（如 quota）寫 stderr 並回非零，且 prompt 由旗標傳入時不再讀 stdin。討論串建議 `stdin=DEVNULL`。macOS 1.0.16 仍有人回報 exit 0 無輸出，原因推測是被吞掉的伺服器錯誤。

**未實測**：asyncio subprocess（stdout PIPE、`CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW`）是否真的收到輸出。

### 2. 只留網路工具

沒有 `--allowed-tools` / `--tools` 類旗標（headless、settings、permissions 頁都沒有）。可用的機制：

- 權限規則 `permissions.{allow,deny,ask}`，格式 `action(target)`，優先順序 Deny > Ask > Allow（antigravity.google/docs/permissions）。識別名：`read_file`、`write_file`、`read_url`（web fetch）、`execute_url`（瀏覽器操作）、`command`、`unsandboxed`、`mcp(server/tool)`。**文件沒有 web search 與 subagent 的識別名**，所以這兩個無法用規則控制或確認。
- settings：`toolPermission`（`request-review` 預設 / `proceed-in-sandbox` / `strict` / `always-proceed`）、`allowNonWorkspaceAccess`（預設 false）、`enableTerminalSandbox`。
- headless 不能互動，需要核准的工具會被 soft-deny（繼續執行、exit 0、通知寫 stderr）；**工作資料夾內的檔案讀寫預設自動允許**（AIgora 的工作資料夾是空的暫存資料夾，可接受）；`read_url`、`execute_url`、`mcp` 預設 ask → headless 會被拒，意味著 **web fetch 預設也會被拒**，必須 allow `read_url(*)`。
- **風險：headless 繼承使用者設定的權限模式。** 若使用者 settings 是 `toolPermission: "always-proceed"` 或 `allowNonWorkspaceAccess: true`，Adapter 的隔離就破了，所以一定要不讀使用者設定（見問題 3）。

候選組合（未驗證）：

```json
{
  "toolPermission": "strict",
  "allowNonWorkspaceAccess": false,
  "enableTerminalSandbox": true,
  "enableTelemetry": false,
  "permissions": {
    "deny": ["command(*)", "unsandboxed(*)", "execute_url(*)", "mcp(*)", "write_file(*)", "read_file(*)"],
    "allow": ["read_url(*)"]
  }
}
```

（`read_file(*)` deny 也會擋掉工作資料夾內的讀取，這是想要的；但它是否也擋到內部需要的東西要實測。）

Issue #548（`--print` 忽略 `permissions.allow`，仍 open）：在 1.1.27 不再卡住而是 auto-deny；`read_file(*)`、`mcp(...)` 規則在 headless 有效，Windows 上 `command(...)` 窄規則曾被忽略、`command(*)` 有效；hook 回 `deny` 會被遵守。對 AIgora 而言 **deny 比 allow 重要，deny 看起來有被遵守**，但 `read_url(*)` 的 allow 是否生效決定 web fetch 能不能用。

Web search 在 headless 能否運作：**文件未說明，未實測。**

### 3. 忽略使用者設定

**沒有官方的「忽略使用者設定」旗標、設定路徑覆寫或 admin/system policy 檔**（settings 頁：Env vars for settings path — not documented；permissions 頁沒有 system/admin 層級）。`agy` 會載入：
- 規則（antigravity.google/docs/rules）：全域 `~/.gemini/AGENTS.md`、`~/.gemini/GEMINI.md`、`~/.gemini/config/{AGENTS,GEMINI}.md`、`~/.gemini/config/rules/*.md`、`~/.gemini/antigravity-cli/rules/*.md`；工作資料夾往上到 workspace root 的 `AGENTS.md` / `GEMINI.md` / `.agents/rules/*.md`。沒有關閉開關。
- MCP（docs/mcp）：`~/.gemini/config/mcp_config.json`、`.agents/mcp_config.json`；只能逐一 `disabled: true`。
- Skills：`~/.gemini/antigravity-cli/skills/`、`.agents/skills/`；外掛：`~/.gemini/antigravity-cli/plugins/`；hooks。
- 權限：`~/.gemini/antigravity-cli/settings.json`，以及 #548 提到的 `~/.gemini/config/config.json`（`userSettings.globalPermissionGrants.allow`）與 `~/.gemini/config/projects/<id>.json`——**使用者在這些檔案的 allow 會疊加進來**。

唯一可能的方法：每次發言把 `HOME` 與 `USERPROFILE`（Windows）指向工作資料夾外的暫存 home，只放 AIgora 的 `.gemini/antigravity-cli/settings.json`。登入權杖存在 OS keyring（Windows Credential Manager），理論上不受 home 影響；API key 走環境變數。**未驗證**：`agy` 是否以 `USERPROFILE`/`HOME` 決定 `~`、改 home 後 keyring 登入是否仍有效、首次啟動的遷移/onboarding 是否在空 home 觸發互動。另需 `AGY_CLI_DISABLE_AUTO_UPDATE=true`（docs/cli/troubleshooting）。

### 4. Canary / smoke

未執行（未安裝）。執行時要照 Gemini ticket（`.scratch/aigora-v1/issues/14-adapter-gemini.md` comment 5）的教訓：CLI 啟動失敗或 `result.status != SUCCESS` 必須算失敗/skip，不能算 canary 通過；同時檢查 `init.tools` 與 stderr 的權限通知，確認是「被拒」而不是「沒跑起來」。

### 5. 取消

未執行。`kill_tree`（`taskkill /F /T`）應可涵蓋；Windows 安裝的是原生 `agy.exe`（`%LOCALAPPDATA%\agy\bin`），不是 npm shim。要確認 `agy` 是否另起背景 daemon / language server（#76 提到 shutdown 時 "Waiting for migrations to complete"），以及被殺後是否留下 lock 讓下次啟動卡住。

### 6. 認證與條款

- 個人帳號：`agy` 首次執行開瀏覽器登入，token 存 OS keyring（docs/install?tab=cli）。**條款不允許第三方應用程式包裝使用（見結論）。**
- API key：`~/.gemini/antigravity-cli/settings.json` 設 `"modelProvider": "gemini"` 且設環境變數 `GEMINI_API_KEY`；只設環境變數無效；不讀 `GOOGLE_API_KEY`、不讀 `.env`；啟動只檢查非空，錯的 key 在第一次對話才失敗。可用 `GOOGLE_GEMINI_BASE_URL` 換端點。
- ADC：`AGY_ADC_AUTH=true` + `gcloud auth application-default login`（Google Cloud 專案）。
- 可用性檢查（不花 quota）：文件沒有 `agy auth status` 之類的非互動指令。**未知。**
- 未知：API key 路線下 web search 是否可用、是否計費；Gemini API 條款對此用法的細節（未逐條查證）。

## 阻礙總表

| # | 阻礙 | 嚴重度 | 狀態 |
|---|---|---|---|
| B1 | 消費者方案不支援把 agy 包進第三方應用（FAQ、條款第 6 條，可停權） | 致命（個人帳號路線） | 官方明文 |
| B2 | 沒有忽略使用者設定的旗標/路徑覆寫；使用者的 allow、規則、MCP、skills 會載入 | 高 | 只能靠改 HOME，未驗證 |
| B3 | 沒有 web search / subagent 的權限識別名，無法確認它們被限制 | 中 | 未實測 |
| B4 | Windows pipe 輸出（#76） | 中 | 上游稱 1.1.1 已修，未實測 |
| B5 | `permissions.allow` 在 `-p` 不可靠（#548，open） | 中（影響 web fetch） | 未實測 |
| B6 | 無不花 quota 的登入狀態檢查 | 低 | 未知 |

## 建議

**Drop 個人帳號路線；API key 路線暫不建 Adapter（wait）。** 若使用者要 Gemini 參與者，有兩條路，都需使用者決定：
- A. 用 AI Studio API key + `agy`：先跑階段 2 實測（HOME 覆寫、pipe、canary、smoke、取消）；全部通過才寫 spec 與 tickets。
- B. 用 AI Studio API key 直接呼叫 Gemini API（含 Google Search grounding）：沒有本機工具，隔離最乾淨，但違反 ADR 0001，需要新 ADR。

因為建議不是「現在做」，本 spike 未起草 `spec.md` / tickets。

## 待使用者決定

1. 是否接受「個人 Google 帳號不能用於 AIgora 的 agy 參與者」？
2. 要不要走 API key（需申請 Google AI Studio API key、按用量付費）？若要，選 A（agy）或 B（直接 API，新 ADR）？
3. 若選 A：請安裝並設定 `agy`，我再做階段 2 實測。

## 來源

- 安裝、登入、API key：https://antigravity.google/docs/getting-started?tab=cli 、https://antigravity.google/docs/install?tab=cli
- Headless：https://antigravity.google/docs/cli/headless
- 權限：https://antigravity.google/docs/permissions
- 設定：https://antigravity.google/docs/settings 、https://antigravity.google/docs/cli/reference
- 規則：https://antigravity.google/docs/rules ；MCP：https://antigravity.google/docs/mcp ；遷移：https://antigravity.google/docs/cli/gcli-migration
- 自動更新：https://antigravity.google/docs/cli/troubleshooting/
- 條款：https://antigravity.google/terms ；FAQ：https://antigravity.google/docs/faq
- Issues：https://github.com/google-antigravity/antigravity-cli/issues/76 、https://github.com/google-antigravity/antigravity-cli/issues/548
