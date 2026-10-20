# 05: 檢視器：參與者狀態與表態追蹤

Status: ready-for-agent

Blocked by: 04

**What to build:** 在討論檢視器最上方加兩個區塊：
- 參與者：頭像、名稱、主持人、目前狀態、已移出。
- 表態追蹤：每輪 × 每個參與者的同意／不同意／失敗。

兩者都做成只吃 props 的展示元件，讓 07 的唯讀紀錄可以用紀錄 JSON 餵資料。見 spec「討論中／結束後」的檢視器段落與原型 `?variant=A&screen=live`。

**Scope:**
- 新增 `frontend/src/components/discussion/InspectorParticipants.vue` 與 `frontend/src/components/discussion/StanceTracker.vue`，只吃 props：參與者清單、主持人 id、已移出清單、各輪各參與者的狀態與表態。
- 修改 `frontend/src/components/discussion/DiscussionInspector.vue`：從 store 推導資料，傳給這兩個元件。
- 不修改 store、契約、router、後端，也不修改 `DiscussionInspector.vue` 以外屬於 04 的元件。

- [ ] 參與者的每一列用 04 的 `ParticipantLabel`（含模型標籤）；表態追蹤表頭的頭像有 `title`，內容是「名稱（模型）」，讓同一個 Adapter 的參與者分得出來
- [ ] 參與者：主持人 pill 跟著 `moderatorId`（主持人接手後會更新）；狀態取最新一輪該參與者的發言狀態；已移出的整列淡化並顯示「已移出」
- [ ] 表態追蹤只在共識討論中、從第 2 輪開始出現：同意是綠點，不同意是紅點，失敗或未表態是紅色空心，該輪沒有發言就空白；下方有圖例
- [ ] 提問模式不顯示表態追蹤
- [ ] 加上 `data-testid`：`inspector-participant`（帶 `data-participant-id`）與 `stance-tracker`；在現有的 E2E（`consensus.spec.ts` 或 `failure-handling.spec.ts`）補一兩個斷言，例如被移出的參與者顯示「已移出」
- [ ] typecheck 與全部 E2E 通過；亮色、暗色各附一張截圖到 Comments

## Comments
