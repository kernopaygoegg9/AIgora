# 13: 整合與驗收

**Type:** 程式 + 人工驗收

**What to build:** v2 所有功能整合完成，文件更新，用真實 AI 跑過一次，由使用者目視驗收。

**Scope:**
- 更新 `docs/architecture/`：`discussion-engine.md`（依序、本輪順序、插話位置、上下文預算、自由聊天）、`contracts.md`（新欄位與 schema 3）、`adapters.md`（Ollama `num_ctx`、子行程環境移除金鑰）、`testing.md`（計數器的替換方式）。
- `npm run check --prefix frontend` 全綠。
- 手動驗收（由使用者執行或在使用者同意下執行，會花額度）：
  - Claude + Codex（加選用的 Ollama）不給主題的自由聊天，跑到小的輪數上限並產生摘要。
  - 依序的共識討論，主持人排出下一輪順序。
  - 同一主題與人設，用兩種不同上下文上限各跑一次，在畫面上用對照模式看出遺忘範圍。
  - 有金鑰時設定面板顯示 Anthropic API，用量數字合理。
- 開一份驗收紀錄（比照 `.scratch/aigora-v1/acceptance.md`）。

**Blocked by:** 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12

**Status:** ready-for-human

- [ ] `docs/architecture/` 四頁反映 v2 行為
- [ ] `npm run check --prefix frontend` 通過
- [ ] 使用者完成上列手動驗收並記錄在驗收紀錄中
- [ ] 舊的 v1 紀錄在歷史中仍能打開
