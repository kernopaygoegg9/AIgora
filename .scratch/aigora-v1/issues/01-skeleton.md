# 01: 骨架

**What to build:** 一個指令就能啟動後端與前端，瀏覽器打開看到 AIgora 的主版面（空白內容）。所有之後會被多張 ticket 共用的熱點檔案都在這裡一次建好，之後的 ticket 只需要新增或修改自己的模組。

**Scope:**
- 後端專案（uv、FastAPI）：依賴清單、啟動入口、**路由註冊**（spec 中所有 HTTP 端點與 WebSocket 端點都先註冊，暫時回傳「未實作」）、**Adapter registry**（`claude`、`codex`、`gemini`、`ollama`、`fake` 全部先註冊，依識別碼對應到各自的模組位置，模組可以是空殼）、pytest 設定。
- 前端專案（Vue + Vite + TypeScript）：依賴清單、**前端路由**（討論頁、歷史頁都先註冊）、**全域 store**（空殼，只定義位置與匯出名稱）、**主版面**、Playwright 設定。
- 共用：`.gitignore`（含 `.env`、討論紀錄資料夾）、`.env.example`、`participants.toml` 範例檔、AGENTS.md 的安裝 / 啟動 / 測試指令。
- 依賴清單一次補齊 spec 會用到的套件（FastAPI、uvicorn、httpx、pytest 等；Vue、Vite、Vue Router、Playwright 等），之後的 ticket 不再修改依賴清單。

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] 一個指令啟動後，瀏覽器能看到主版面，並能切換到討論頁與歷史頁（空白）
- [ ] 所有 spec 中的 HTTP / WebSocket 端點都已註冊，呼叫時回傳「未實作」
- [ ] Adapter registry 能用識別碼查到 5 個 Adapter 的位置
- [ ] `pytest` 與 Playwright 都能執行（各至少一個冒煙測試通過）
- [ ] AGENTS.md 寫明安裝、啟動、測試指令
- [ ] `.env` 與討論紀錄資料夾被 git 忽略
- [ ] 熱點檔案清單與擁有者寫入 `tickets-overview.md`（若與實際檔名不同，更新該表）
