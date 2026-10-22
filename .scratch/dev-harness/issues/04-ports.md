# 04: E2E 自動 port + 開發伺服器單一 port 變數

**Type:** 設定（不走 tdd）

**What to build:** 好幾個 E2E 同時跑不會互撞；開發伺服器只用 `AIGORA_PORT` 一個變數同時改前後端。

**Scope:**
- `frontend/playwright.config.ts`：沒有指定 `AIGORA_E2E_BACKEND_PORT` / `AIGORA_E2E_FRONTEND_PORT` 時自動挑空的 port，寫回 `process.env` 讓 worker 讀到同一組（見 spec「Port」）。
- `frontend/vite.config.ts` 改讀 `AIGORA_PORT`；移除 `AIGORA_BACKEND_PORT`。
- 更新 AGENTS.md 與 `docs/architecture/testing.md` 中固定 port、互撞的描述；`.env.example` 若有相關註解一併更新。

**Blocked by:** 01

**Status:** resolved

- [x] 在兩個終端機同時執行 `cd frontend && npx playwright test`，兩邊都通過
- [x] 指定 `AIGORA_E2E_BACKEND_PORT` / `AIGORA_E2E_FRONTEND_PORT` 時 E2E 使用指定的 port
- [x] `AIGORA_PORT=8775 npm run dev --prefix frontend`：後端聽 8775，網頁的 `/api` 與 `/ws` 都正常（打開討論頁能載入參與者清單）
- [x] 專案中不再出現 `AIGORA_BACKEND_PORT`
- [x] `npm run check --prefix frontend` 通過

## Comments

- 2026-10-22 merged (full `check` green: 317 passed, E2E 41 passed). Two concurrent runs passed. Deviation: E2E records go to a per-run `mkdtemp` dir (`aigora-e2e-*`) because Playwright wipes `test-results/` at start; follow-up: these dirs are never cleaned. CI adds the html reporter.
