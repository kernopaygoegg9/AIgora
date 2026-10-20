# 以移除本機工具隔離參與者，而不是靠 OS sandbox

參與者不能讀取工作資料夾以外的檔案。實測發現 Codex 的 `--sandbox read-only` 只禁止寫入，仍能讀取整台電腦的檔案，而且各 CLI 都沒有「只允許讀取某個資料夾」的設定；Claude 的 `--tools` 也不會擋掉 claude.ai connector 等 MCP 工具。
因此每個 Adapter 必須把 CLI 的本機工具（shell、檔案讀寫、MCP、外掛、hooks 等）全部關掉，只留下上網查資料的工具，並忽略使用者自己的 CLI 設定檔。

## Consequences

- Adapter 的啟動參數會很長（例如 Codex 要 `--disable` 十幾個 feature），這是刻意的，不要「簡化」掉。
- Codex 的 `code_mode_host` 不能關，關掉後 web search 也會失效。
- 這是靠移除工具，不是作業系統層級的隔離；CLI 升級可能加入新工具，所以每個 Adapter 都要有 canary 自動測試（工作資料夾外放隨機內容的檔案，輸出中不得出現），CLI 升級後要重跑。
