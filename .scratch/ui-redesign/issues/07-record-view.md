# 07: 唯讀紀錄

Status: resolved

Blocked by: 05

**What to build:** 讓唯讀紀錄的外觀和討論中畫面一致：
- 頂部列加上「唯讀紀錄」標示。
- 結果區塊放在最上方。
- 各輪沿用 04 的共用樣式。
- 右邊的檢視器有參與者、表態追蹤與設定快照。
- 整頁沒有任何按鈕或文字輸入框。

見 spec「歷史與唯讀紀錄」與原型 `?variant=A&screen=record`。

**Scope:**
- 修改 `frontend/src/components/history/RecordView.vue`、`frontend/src/components/history/RecordRound.vue`。
- 重用 `frontend/src/styles/discussion.css` 的 class，以及 05 的 `InspectorParticipants`、`StanceTracker`（props 從紀錄 JSON 推導）。如果需要調整共用的樣式或元件，只能**新增**變化（例如新的 modifier class），不能改變討論中畫面的外觀。
- （「沒有 button／textbox」的斷言已經在 02 改成只檢查 `record-view` 範圍內，這張 ticket 不用再改測試。）
- 不修改 store、契約、router、後端、`DiscussionPage.vue`。

- [x] 名稱旁的模型標籤沿用 04 的 `ParticipantLabel`（資料來自紀錄的 `participants[].model`）；schema 1 的舊紀錄同樣顯示
- [x] 所有 `record-*` testid 以及 `turn-card`、`turn-text` 都保留在語意相同的元素上
- [x] 頂部列有問題、結果 pill、「唯讀紀錄」標示；`record-derived-from` 顯示在附近
- [x] 結果區塊（`record-result`）在第 1 輪之前，配色和討論中畫面一致
- [x] 檢視器：參與者（含已移出、主持人接手）、表態追蹤（共識討論）、設定快照（`record-meta`）
- [x] 插話、移出、主持人接手沿用討論中畫面的樣式；不屬於任何一輪的事件（leftovers）仍然顯示
- [x] `record-view` 內沒有任何 button 或 textbox
- [x] typecheck 與全部 E2E 通過；亮色、暗色各附一張截圖到 Comments

## Comments

- 2026-10-20：完成。
  - 唯讀紀錄改用 04 的 `discussion.css`、`TurnCard`、`ParticipantLabel`，以及 05 的 `InspectorParticipants`、`StanceTracker`，資料從紀錄 JSON 推導。
  - 對共用元件只做了新增：在 `TurnCard` 加一個 `stance` 具名 slot，預設內容不變，所以討論中的畫面一樣。紀錄頁用這個 slot 把 `record-stance` 放在同一行表態裡，因為 `history.spec.ts` 用 `toHaveText('同意')` 比對全文。
  - `record-meta` 搬到檢視器，標題是「設定快照」；`record-derived-from` 和「← 回到歷史」放在頂部列下方。
  - 主持人取最後一次接手的人，沒有接手時用設定中的主持人。schema 1 的舊紀錄沒有 `model`，模型標籤顯示「預設模型」。
  - 驗證：typecheck 通過，E2E 35 passed（沒有修改測試），有亮色與暗色截圖。
