# 01: Spike：Antigravity CLI（agy）能否成為 AIgora 參與者

**Type:** research

**Question:** Google 的 Antigravity CLI（`agy`）能不能在 ADR 0002 的隔離規則下當 AIgora 的 Participant？要在這台 Windows 機器上實測：headless 串流輸出（stdout 為 pipe 時）、只保留網路搜尋的工具限制、忽略使用者設定（AGENTS.md / GEMINI.md / 全域規則、MCP、外掛、skills）、canary 與 smoke、取消後不留孤兒行程、認證方式與服務條款。交付物是 findings 文件與建議（現在做 Adapter／等上游修正／放棄），不寫 Adapter 程式碼。

**Scope:**
- 安裝與登入 `agy` 由使用者自行完成；不代為安裝、不輸入憑證。
- 不修改正式程式碼、ADR、`.scratch/aigora-v1/`、`frontend/`。
- 真的呼叫模型的次數要少、prompt 要短。

**Status:** resolved

## Answer

見 `../spike.md`。重點：官方 FAQ 與條款第 6 條不允許在消費者方案下把 `agy` 包進第三方應用程式（可停權），所以**個人 Google 帳號路線放棄**。API key 路線技術上可能，但沒有忽略使用者設定的旗標（只能靠改 `HOME`/`USERPROFILE`，未驗證），建議**暫不做 Adapter**。`agy` 未安裝，實機測試（pipe 輸出、canary、smoke、取消）未執行；若使用者選擇 API key + agy，另開 ticket 做實測。

## Comments

- 2026-10-20: 只完成桌面研究；`agy` 不在 PATH，依指示不代為安裝。
