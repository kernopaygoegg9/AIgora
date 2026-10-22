# 01: 單一檢查入口 + linter

**Type:** 設定（不走 tdd）

**What to build:** 一個指令跑完所有檢查；後端 ruff、前端 ESLint + Prettier 上線，既有違規全部修好，master 上 `check` 是綠的。

**Scope:**
- `frontend/package.json` 新增 `check`、`check:fast`、`lint`、`format` scripts（內容見 spec「單一檢查入口」）；新增 ESLint、Prettier 相關 devDependencies 與設定檔。
- `backend/pyproject.toml` 新增 ruff（dev 依賴）與設定：規則 `E`、`F`、`I`，`ruff format`。
- 跑一次 formatter 並修掉所有 lint 違規。這會改到幾乎所有檔案，所以本 ticket 單獨先做，其他 ticket 都在它之後。
- AGENTS.md 的 Commands 段改以 `check` / `check:fast` 為主。

**Blocked by:** None

**Status:** ready-for-agent

- [ ] 在 repo 根目錄執行 `npm run check --prefix frontend` 全部通過，結束碼 0
- [ ] `npm run check:fast --prefix frontend` 不跑 build 與 E2E，全部通過
- [ ] 故意在後端加一個未使用的 import、在前端加一個未使用的變數、把一個檔案的縮排弄亂：`check:fast` 各自失敗並指出檔案與行號（驗證後還原，不 commit）
- [ ] `real_ai` 測試仍預設跳過
- [ ] formatter 只改格式，所有既有測試（pytest、typecheck、E2E）照常通過
