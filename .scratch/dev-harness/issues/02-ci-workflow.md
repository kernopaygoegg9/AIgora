# 02: CI（GitHub Actions）

**Type:** 設定（不走 tdd）

**What to build:** 每個 PR 與每次推到 `master` 都在 GitHub Actions 跑 `npm run check --prefix frontend`。

**Scope:**
- `.github/workflows/check.yml`，內容見 spec「CI」。Node 版本與本機開發一致（看 `frontend/package.json` 的 engines 或本機 `node -v`，寫死在 workflow）。
- E2E 失敗時上傳 Playwright report。
- AGENTS.md 加一行說明 CI 跑的就是 `check`。

**Blocked by:** 01

**Status:** resolved

- [x] 用 `act` 或對 workflow 檔做靜態檢查（如 `actionlint`，若本機沒有就以 YAML 語法檢查加人工核對步驟）確認 workflow 可解析
- [x] workflow 只在 `pull_request` 與 `push` 到 `master` 觸發
- [x] 不需要任何 secret
- [x] **使用者驗收**：使用者推上分支並開 PR 後，PR 顯示 check 通過；在分支上故意放一個 lint 違規時 check 失敗（之後移除）

## Comments

- 2026-10-22 merged; workflow parses (YAML + manual review), triggers and no-secrets verified; full `check` green locally. Remaining: user pushes `dev-harness`, opens a PR, sees the check pass, and sees it fail on a deliberate lint violation.
- 2026-10-22 user acceptance done on PR #2: check green at `c56018c` (after fixing a Linux-only hang in `test_leftover_processes.py`); deliberate lint violation `d8018cb` failed CI with `no-unused-vars` at `main.ts:16`; reverted.
