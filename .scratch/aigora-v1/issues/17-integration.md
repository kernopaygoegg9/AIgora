# 17: 整合

**What to build:** 把所有部分組在一起驗收：用正式素材取代佔位圖，用真實的 Claude、Codex 參與者跑完一場共識討論（v1 暫不使用 Gemini，見 spec「Gemini CLI」）並輸出結果，確認 spec 的成功條件全部成立。

**Scope:**
- 前端：把佔位圖換成正式素材（App icon、favicon、頭像）。這是唯一允許為此修改主版面的 ticket。
- 跑完整的測試：API 測試、E2E、所有真實 Adapter 的 canary 與 smoke 測試。
- 更新 AGENTS.md 中的執行與測試指令（若有變動）。
- 發現的問題記錄為新的 ticket，不在本 ticket 中大改。

**Blocked by:** 01–16 全部

**Status:** ready-for-human

- [ ] 畫面上使用正式素材
- [ ] 所有自動測試通過（真實 Adapter 的測試在已安裝的 CLI 上通過）
- [ ] **所有真實 Adapter 的 canary 測試通過：Participant 無法讀取工作資料夾以外的檔案**
- [ ] 手動驗收：Claude、Codex 參與者（可加 Ollama）完成一場共識討論並輸出結果；未取得共識時能輸出各方立場與分歧點
- [ ] 手動驗收：在 `participants.toml` 加入 Ollama 參與者即可參加討論，不需改其他程式

## Comments

- 2026-10-20 (orchestrator): User decided not to use Gemini in v1 (Google personal sign-in rejected; adapter isolation bugs found, see ticket 14). Acceptance now uses Claude + Codex (+ optional Ollama). Real-AI tests so far: claude 3/3 passed, codex 3/3 passed.

- 2026-10-20 (orchestrator): Asset swap, non-real test suites, AGENTS.md, and code-review fixes merged into `aigora-v1`. Per user decision, real-AI canary/smoke runs, the full real-AI consensus run, and human acceptance are left to the user — checklist in `.scratch/aigora-v1/acceptance.md`.
