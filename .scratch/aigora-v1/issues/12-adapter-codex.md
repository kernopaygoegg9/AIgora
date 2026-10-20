# 12: Adapter：codex

**What to build:** 使用者可以選 Codex CLI 的參與者參加討論：回覆會即時串流顯示，它可以上網查資料，但完全無法讀寫本機檔案。

**Scope:**
- 後端：`codex` Adapter 模組（registry 已在 01 註冊，不必修改）與它的測試。
- 依 ADR 0002 套用隔離參數：非互動 exec、啟用網路搜尋、忽略使用者設定與規則、唯讀 sandbox、停用 shell 與其他本機 feature（shell_tool、unified_exec、view_image、browser_use、browser_use_external、computer_use、apps、plugins、multi_agent、multi_agent_v2、image_generation、hooks、in_app_browser、skill_search、workspace_dependencies）；**不得停用 `code_mode_host`**（停用後網路搜尋失效）。在工作資料夾中執行。
- 不得修改熱點檔案與討論引擎。介面不夠用時停下回報。

**Blocked by:** 02

**Status:** claimed

- [ ] 可用性檢查：未安裝或未登入時回報不可用並附原因
- [ ] 串流：解析 CLI 的 JSONL 事件成 `delta` / `completed`
- [ ] 失敗分類：未登入、額度用完、崩潰對應到正確的失敗種類；取消時子行程結束
- [ ] **Participant 無法讀取工作資料夾以外的檔案**：canary 測試（工作資料夾外放隨機內容的檔案，要求盡力讀取，輸出不得出現該內容）通過
- [ ] Smoke 測試：問一個簡短問題，收到回覆且能解析表態；能用網路搜尋並附網址
- [ ] 真實 CLI 的測試以標記區隔，預設不執行
