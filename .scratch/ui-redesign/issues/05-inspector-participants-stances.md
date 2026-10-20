# 05: 檢視器：參與者狀態與表態追蹤

Status: resolved

Blocked by: 04

**What to build:** 在討論檢視器最上方加兩個區塊：
- 參與者：頭像、名稱、主持人、目前狀態、已移出。
- 表態追蹤：每輪 × 每個參與者的同意／不同意／失敗。

兩者都做成只吃 props 的展示元件，讓 07 的唯讀紀錄可以用紀錄 JSON 餵資料。見 spec「討論中／結束後」的檢視器段落與原型 `?variant=A&screen=live`。

**Scope:**
- 新增 `frontend/src/components/discussion/InspectorParticipants.vue` 與 `frontend/src/components/discussion/StanceTracker.vue`，只吃 props：參與者清單、主持人 id、已移出清單、各輪各參與者的狀態與表態。
- 修改 `frontend/src/components/discussion/DiscussionInspector.vue`：從 store 推導資料，傳給這兩個元件。
- 不修改 store、契約、router、後端，也不修改 `DiscussionInspector.vue` 以外屬於 04 的元件。

- [x] 參與者的每一列用 04 的 `ParticipantLabel`（含模型標籤）；表態追蹤表頭的頭像有 `title`，內容是「名稱（模型）」，讓同一個 Adapter 的參與者分得出來
- [x] 參與者：主持人 pill 跟著 `moderatorId`（主持人接手後會更新）；狀態取最新一輪該參與者的發言狀態；已移出的整列淡化並顯示「已移出」
- [x] 表態追蹤只在共識討論中、從第 2 輪開始出現：同意是綠點，不同意是紅點，失敗或未表態是紅色空心，該輪沒有發言就空白；下方有圖例
- [x] 提問模式不顯示表態追蹤
- [x] 加上 `data-testid`：`inspector-participant`（帶 `data-participant-id`）與 `stance-tracker`；在現有的 E2E（`consensus.spec.ts` 或 `failure-handling.spec.ts`）補一兩個斷言，例如被移出的參與者顯示「已移出」
- [x] typecheck 與全部 E2E 通過；亮色、暗色各附一張截圖到 Comments

## Comments

- 2026-10-20：完成。
  - `InspectorParticipants` 與 `StanceTracker` 都只吃 props。`StanceTracker` 匯出 `StanceCell` 型別，07 從紀錄的 `turns[].status/stance` 組出同樣的資料即可。
  - 參與者的狀態取這個參與者最新一次發言的狀態（跨輪）。在依序發言時，新的一輪還沒輪到他，也不會變成空白。
  - 主持人 pill 只在共識討論顯示（提問沒有主持人）。設定快照裡的「主持人」仍然是開始時設定的人，因為那是鎖定的設定。
  - 表態追蹤的圖例只有同意、不同意、失敗或未表態三種；回覆中另外用虛線圈表示，沒有放進圖例。
  - E2E 新增的斷言：
    - `failure-handling.spec.ts`：Fake Flaky 顯示「已移出」，主持人 pill 在 Fake A 上。
    - `consensus.spec.ts`：表態追蹤有第 2 輪。
    - `ask.spec.ts`：提問沒有表態追蹤。
  - 驗證：typecheck 通過，E2E 35 passed。截圖有「移出＋主持人接手（暗）」與「討論中（亮）」兩張。
