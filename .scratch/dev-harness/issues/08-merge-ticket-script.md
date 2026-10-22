# 08: 合併腳本

**Type:** 設定（不走 tdd；以實際執行驗收）

**What to build:** 協調者用一支腳本合併 implementer 分支：沒有衝突就自動檢查並保留，有衝突或檢查失敗就退回原狀並非零結束。

**Scope:**
- `scripts/merge-ticket.sh`，行為見 spec「合併腳本」；有給 `--feature` / `--ticket` 時先跑 07 的熱點檔案檢查。
- AGENTS.md「implement-spec: extra rules」改成：沒有衝突時協調者執行這支腳本；腳本因衝突失敗時才派 merger subagent。

**Blocked by:** 01、07

**Status:** resolved

- [x] 在一個暫時的整合分支上驗證四種情況，每種都確認結束碼與分支狀態：
  - 乾淨合併且檢查通過 → 結束碼 0，merge commit 留下
  - 有衝突 → 結束碼非零，工作目錄回到合併前、沒有殘留的合併狀態
  - 合併成功但 `check` 失敗 → 結束碼非零，分支回到合併前
  - 改到不屬於該 ticket 的熱點檔案 → 結束碼非零，分支回到合併前
- [x] 在 Windows 的 Git Bash 執行通過
- [x] 驗證用的暫時分支都已刪除

## Comments

- 2026-10-22 merged by running the script itself on `dev-harness` with the default full `check` (exit 0, pytest 317, E2E 41). Exit codes: 0 ok, 1 hot-file/check failure (reset), 2 usage/dirty tree, 3 conflict (abort, dispatch merger). `AIGORA_MERGE_CHECK_CMD` overrides the check. Added `.gitattributes` (`*.sh eol=lf`).
