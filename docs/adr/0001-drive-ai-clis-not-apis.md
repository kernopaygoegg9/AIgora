# 直接操作各家 AI CLI（子行程），不呼叫 API

AIgora 以子行程執行 Claude Code、Codex CLI、Gemini CLI 等的非互動模式來取得參與者的發言，而不是呼叫各家的 HTTP API。
這樣可以沿用使用者已登入的訂閱帳號，不必另外申請 API 金鑰、也不另外付費；代價是各 CLI 的輸出格式、旗標與權限控制都不同，必須由每個 Adapter 各自處理解析與限制，CLI 改版時也可能需要跟著修。

## Consequences

- 每次發言都送出完整的討論內容（不使用各 CLI 的 resume），讓所有 Adapter 行為一致，也讓不支援 session 的 AI（如 Ollama）能接入。
- 這些 CLI 本身是會讀寫檔案、執行指令的 coding agent，Adapter 必須負責把它們限制成只能上網查資料、不能動到本機。
- 例外：Jev（共識裁定方式 B）透過 TypeSafe API 呼叫，需要使用者自行提供金鑰。
