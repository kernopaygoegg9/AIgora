# dev-harness Tickets 總覽

Spec：`spec.md`。Tickets：`issues/` 下每張一個檔案。熱點檔案歸屬（機器可讀）：`hot-files.toml`。

## Tickets

| # | Ticket | Blocked by | 類型 |
|---|---|---|---|
| 01 | 單一檢查入口 + linter | — | 設定（不走 tdd） |
| 02 | CI（GitHub Actions） | 01 | 設定（不走 tdd；最後驗收需使用者推分支） |
| 03 | 真實 Adapter 測試共用 helper | 01 | 程式（tdd） |
| 04 | E2E 自動 port + `AIGORA_PORT` | 01 | 設定（不走 tdd） |
| 05 | 測試不留下子行程 | 01 | 程式（tdd） |
| 06 | 用詞檢查 | 01 | 程式（tdd） |
| 07 | 熱點檔案歸屬檢查 | 01 | 程式（tdd） |
| 08 | 合併腳本 | 01、07 | 設定（不走 tdd；以實際執行驗收） |

## 並行批次

1. **01 單獨先做**：formatter 會改到幾乎所有檔案，其他 ticket 從它之後的整合分支開始。
2. **02–07 並行**。
3. **08**（需要 07 的檢查腳本）。

## 熱點檔案

見 `hot-files.toml`。重點：

- `frontend/package.json` 屬於 01；06 只能改 `check` / `check:fast` 兩行。
- `AGENTS.md` 所有 ticket 皆可改（各自只改自己的那幾行），衝突在合併時解決。
- `docs/architecture/testing.md` 由 04、05 共用，各改不同段落。
