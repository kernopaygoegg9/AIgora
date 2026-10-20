# 以移除本機工具隔離參與者，而不是靠 OS sandbox

參與者不能讀取工作資料夾以外的檔案。實測發現 Codex 的 `--sandbox read-only` 只禁止寫入，仍能讀取整台電腦的檔案，而且各 CLI 都沒有「只允許讀取某個資料夾」的設定；Claude 的 `--tools` 也不會擋掉 claude.ai connector 等 MCP 工具。
因此每個 Adapter 必須把 CLI 的本機工具（shell、檔案讀寫、MCP、外掛、hooks 等）全部關掉，只留下上網查資料的工具，並忽略使用者自己的 CLI 設定檔。

## Consequences

- Adapter 的啟動參數會很長（例如 Codex 要 `--disable` 十幾個 feature），這是刻意的，不要「簡化」掉。
- Codex 的 `code_mode_host` 不能關，關掉後 web search 也會失效。
- 這是靠移除工具，不是作業系統層級的隔離；CLI 升級可能加入新工具，所以每個 Adapter 都要有 canary 自動測試（工作資料夾外放隨機內容的檔案，輸出中不得出現），CLI 升級後要重跑。
- Gemini CLI 沒有「忽略使用者設定」的參數，所以 Adapter 每次發言都在工作資料夾外的暫存資料夾產生一份 system settings override（用 `GEMINI_CLI_SYSTEM_SETTINGS_PATH` 指定，優先順序高於使用者與專案設定）和一份 admin policy（`--admin-policy`，最高層級）：settings 以 `tools.core` 只留 `google_web_search`、`web_fetch`，其餘本機工具同時列入 `tools.exclude`，清空 `mcpServers`、`mcp.allowed` 指向不存在的名稱、`admin.mcp/extensions/skills.enabled = false`，關掉 hooks、skills、subagents、checkpointing、yolo、folder trust、自動更新與遙測，`context.fileName` 指向不存在的檔案（不載入使用者的 `GEMINI.md`）；policy 以低優先度 deny `*`、allow 兩個網路工具、最高優先度 deny `mcpName = "*"`。命令列：`gemini --output-format stream-json --approval-mode default --extensions none --allowed-mcp-server-names __aigora_no_mcp__ --admin-policy <檔案> [--model <模型>]`，prompt 走 stdin；環境變數 `GEMINI_SANDBOX=false`、`NO_BROWSER=true`。登入資訊（`~/.gemini/oauth_creds.json` 或 API key）仍沿用使用者的。
- 上述 Gemini 參數取自官方文件（headless、CLI reference、configuration、policy engine、tools），撰寫時尚未對已安裝的 CLI 實測；第一次跑 `pytest -m real_ai tests/test_gemini_adapter_real.py`（canary）通過前，不要把它當作已驗證。
