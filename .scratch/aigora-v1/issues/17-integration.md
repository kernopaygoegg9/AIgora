# 17: 整合

**What to build:** 把所有部分組在一起驗收：用正式素材取代佔位圖，用真實的 Claude、Codex、Gemini 參與者跑完一場共識討論並輸出結果，確認 spec 的成功條件全部成立。

**Scope:**
- 前端：把佔位圖換成正式素材（App icon、favicon、頭像）。這是唯一允許為此修改主版面的 ticket。
- 跑完整的測試：API 測試、E2E、所有真實 Adapter 的 canary 與 smoke 測試。
- 更新 AGENTS.md 中的執行與測試指令（若有變動）。
- 發現的問題記錄為新的 ticket，不在本 ticket 中大改。

**Blocked by:** 01–16 全部

**Status:** ready-for-agent

- [ ] 畫面上使用正式素材
- [ ] 所有自動測試通過（真實 Adapter 的測試在已安裝的 CLI 上通過）
- [ ] **所有真實 Adapter 的 canary 測試通過：Participant 無法讀取工作資料夾以外的檔案**
- [ ] 手動驗收：Claude、Codex、Gemini 三個參與者完成一場共識討論並輸出結果；未取得共識時能輸出各方立場與分歧點
- [ ] 手動驗收：在 `participants.toml` 加入 Ollama 參與者即可參加討論，不需改其他程式
