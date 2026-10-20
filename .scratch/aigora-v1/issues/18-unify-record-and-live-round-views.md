# 18: 歷史唯讀檢視與即時討論頁共用輪次元件

**Status:** needs-triage

**Found in:** 17（整合）。ticket 09 的筆記已指出「17 can unify」，但屬於重構，不在 17 中大改。

**What:** 歷史唯讀檢視（`frontend/src/components/history/RecordView.vue`、`RecordRound.vue`）直接從紀錄 JSON 自己畫一套輪次、草案、表態、裁定、移出/主持人更換與結果；即時討論頁用另一套（`components/discussion/RoundSection.vue`、`TurnCard.vue`、`RoundConsensus.vue`、`RoundNotices.vue`、`DiscussionOutcome.vue`）。兩邊顯示同樣的東西，但樣式與細節各自維護，之後改一邊容易忘了另一邊（例如 08 的 Jev 機率、反問結果）。

**Scope（建議）:**
- 讓兩邊共用同一組顯示元件（輸入為與來源無關的 props），即時頁從 store 轉換、歷史頁從紀錄轉換。
- 不動凍結的 store 與 WebSocket 型別。
- 既有 E2E（`history.spec.ts`、`consensus*.spec.ts`、`failure-handling.spec.ts`）維持通過。

**Blocked by:** 17
