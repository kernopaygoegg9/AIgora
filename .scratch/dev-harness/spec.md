# Spec: dev-harness

Status: ready-for-agent

來源：v1 實作 session 的回顧（2026-10-22），第 1、2、3、7、8 項。用語依 `GLOSSARY.md`；架構說明見 `docs/architecture/`。

## Problem Statement

v1 由多個 agent 平行實作，品質全靠每個 agent 自己記得跑測試：

- repo 沒有 CI、沒有 pre-commit、沒有 linter；merger 漏跑 E2E 時，合併照樣進了整合分支。
- 每次合併都派一個 merger subagent（約 57k tokens），實際工作只是 `git merge` 加三個測試指令。
- E2E 的 port 寫死（8766/5174），平行 agent 互撞，只好各自複製 `playwright.config.ts`；開發伺服器的 8765 也和別的程式撞過，而且後端與前端用兩個不同的變數名指同一個 port。
- 取消測試失敗時留下孫行程，導致 worktree 刪不掉。
- gemini 的真實 canary 在 CLI 根本沒啟動時「通過」；四個 Adapter 的真實測試各寫一套檢查，寬嚴不一。
- 用詞違規（GLOSSARY 的 _Avoid_）與熱點檔案歸屬違規只寫在文件裡，到最後 code review 才被發現。

## Solution

給 repo 一個**單一的檢查入口**，本機、agent、CI 都跑同一個指令；把能機械化判斷的規則變成檢查；讓平行執行不再互撞；讓合併變成一支腳本。

## User Stories

1. As a 開發者（人或 agent）, I want to 用一個指令跑完所有檢查, so that 不必記得要跑哪幾個指令。
2. As a 開發者, I want to lint 與格式檢查涵蓋後端與前端, so that 風格問題不必靠 review。
3. As a 使用者, I want to 每個 PR 與每次推到 master 都自動跑檢查, so that 壞掉的變更進不了 master 而不自知。
4. As a 使用者, I want to 真實 Adapter 的 canary 只有在發言真的完成時才算通過, so that 隔離沒生效時不會被誤判為安全。
5. As a 平行工作的 agent, I want to E2E 自動使用空的 port, so that 好幾個 agent 同時跑 E2E 不會互撞。
6. As a 使用者, I want to 用一個環境變數改開發伺服器的 port, so that 8765 被占用時前後端一起換。
7. As a 開發者, I want to 測試結束後不留下任何子行程, so that worktree 可以正常刪除。
8. As a 協調者 agent, I want to 用一支腳本合併 implementer 分支並跑檢查, so that 沒有衝突的合併不必派 subagent。
9. As a reviewer, I want to 使用者看得到的文字裡出現 GLOSSARY _Avoid_ 詞時檢查失敗, so that 用詞不必靠人眼抓。
10. As a 協調者 agent, I want to 合併前自動檢查分支是否改了不屬於該 ticket 的熱點檔案, so that 歸屬規則有機器把關。

## Implementation Decisions

### 單一檢查入口

- 入口放在 `frontend/package.json`（沿用 `npm run dev` 同時管前後端的慣例），從 repo 根目錄執行：
  - `npm run check --prefix frontend`：lint + 格式檢查 + 用詞檢查 + backend pytest + typecheck + build + E2E，依序執行，任一步失敗即非零結束。
  - `npm run check:fast --prefix frontend`：同上但不含 build 與 E2E，給 TDD 迴圈用。
  - `npm run lint --prefix frontend`、`npm run format --prefix frontend`（自動修正）。
- `real_ai` 測試維持預設跳過，`check` 永遠不跑它們。
- AGENTS.md 的 Commands 段改以 `check` / `check:fast` 為主，個別指令保留。

### Linter 與格式（使用者決定：標準）

- 後端：ruff，規則 `E`、`F`、`I`；`ruff format` 統一格式。設定寫在 `backend/pyproject.toml`。
- 前端：ESLint flat config，`eslint-plugin-vue` recommended + `typescript-eslint` recommended，搭配 `eslint-config-prettier`；Prettier 統一格式。
- 既有違規全部修掉，`check` 在 master 上必須是綠的。

### CI（使用者決定：PR + push master）

- `.github/workflows/check.yml`：觸發 `pull_request` 與 `push` 到 `master`；ubuntu；安裝 uv、Node（版本與本機一致，寫在 workflow）、依賴、`npx playwright install --with-deps chromium`，然後跑 `npm run check --prefix frontend`。
- 不需要任何 secret；沒有 `.env`、沒有 TypeSafe 金鑰（方式 B 相關測試本來就用假的 key 或 mock）。
- E2E 失敗時上傳 Playwright report 作為 artifact。

### 真實 Adapter 測試共用 helper

- 新增 `backend/tests/real_adapter.py`：`run_real_turn(adapter, participant, prompt, workspace)` 在不可用時 `pytest.skip`，最後一個事件不是 `Completed` 就讓測試失敗，回傳最終文字與串流文字；`assert_canary_not_leaked(secret, result)` 同時檢查兩者。
- claude、codex、gemini、ollama 的真實測試改用它。行為上只有 gemini 的 canary 改變（不再假通過）；codex 的 canary 多檢查串流文字。
- helper 本身用 Fake Adapter 寫一般（非 `real_ai`）測試：`Failed` 結尾時測試會失敗。

### Port（使用者決定：E2E 自動、dev 可覆寫）

- E2E：`playwright.config.ts` 在環境變數沒有指定時自動挑兩個空的 port，寫回 `process.env`（Playwright 的 worker 會重新載入 config，必須讓 worker 讀到同一組 port），再傳給兩個 `webServer` 與 `baseURL`。仍可用 `AIGORA_E2E_BACKEND_PORT` / `AIGORA_E2E_FRONTEND_PORT` 指定。
- 開發：只用 `AIGORA_PORT`（預設 8765），後端與 `vite.config.ts` 都讀它；移除 `AIGORA_BACKEND_PORT`。Vite 自己的 port 維持 Vite 預設行為（被占用就往後找）。
- 更新 AGENTS.md 與 `docs/architecture/testing.md` 中關於固定 port 與互撞的描述。

### 不留下子行程

- 會產生孫行程的測試（取消、行程樹結束的測試）在 teardown 一定結束它們，即使測試失敗也一樣：假 CLI 把自己產生的子行程 PID 寫到測試的暫存資料夾，fixture 在 teardown 結束仍存活的 PID。
- 以一個測試驗證：故意讓取消失敗（不結束行程樹）時，teardown 之後該 PID 已不存在。

### 合併腳本

- `scripts/merge-ticket.sh <branch> [--feature <slug> --ticket <NN>]`：在目前分支（整合分支）上 `git merge --no-ff <branch>`；有衝突時 `git merge --abort` 並以非零結束，請協調者派 merger；沒有衝突就跑熱點檔案檢查（有給 feature/ticket 時）與 `npm run check --prefix frontend`，失敗時 `git reset --hard ORIG_HEAD` 並非零結束。在 Windows 的 Git Bash 與 CI 的 bash 都能跑。
- AGENTS.md 的「implement-spec: extra rules」改成指向這支腳本。

### 用詞檢查

- `scripts/check_glossary.py`（Python 標準庫即可，用 `uv run` 執行）：從 `GLOSSARY.md` 每個 `_Avoid_:` 行解析出要避免的詞（去掉括號內的說明）；掃描 `frontend/src` 中使用者看得到的文字（`.vue` 的 `<template>` 文字與屬性值、`.ts` / `.vue` script 中的字串常值），不掃註解與識別字。
- 若命中的位置是某個 GLOSSARY 正式用語的一部分（例如「討論模式」中的「模式」），不算違規。
- 同一行有 `glossary-ignore` 註記時略過。輸出 `檔案:行: 用詞「X」，請改用「Y」`。
- 接進 `check` 與 `check:fast`。

### 熱點檔案歸屬檢查

- 每個 feature 的熱點檔案歸屬改用機器可讀的 `.scratch/<feature>/hot-files.toml`（路徑或 glob → 擁有的 ticket 編號，可列多個；可標註「所有 ticket 皆可改」）。`tickets-overview.md` 保留文字說明並指向它。
- `scripts/check_hot_files.py --feature <slug> --ticket <NN> <base>..<branch>`：列出分支改到、但不屬於該 ticket 的熱點檔案，有則非零結束。
- 為本 feature 寫 `.scratch/dev-harness/hot-files.toml` 作為第一份實例；v1 與 ui-redesign 已結束，不回補。

## Testing Decisions

- 好的測試：從外部行為驗證（指令的結束碼與輸出、檔案內容），不測內部實作。
- 腳本（用詞檢查、熱點檔案檢查）以 pytest 對暫存資料夾裡的假 repo / 假檔案測試；測試放在 `backend/tests/`，或另建 `scripts/tests/` 並接進 `check`。
- 設定類 ticket（linter、CI、port、合併腳本）不走 TDD，驗收寫在各 ticket，以實際執行指令驗證。

## Out of Scope

- pre-commit hook（CI 加上 `check` 已足夠；之後若需要再加）。
- 真實 AI 測試進 CI。
- 修 Gemini Adapter 的 bug（ticket 14）。
- 回補 v1、ui-redesign 的 `hot-files.toml`。

## Further Notes

- `git push` 與在 GitHub 上看 CI 結果由使用者執行（AGENTS.md「User-only actions」）。CI ticket 的最後驗收需要使用者推分支、開 PR。
- 熱點檔案與並行批次見 `tickets-overview.md`。
