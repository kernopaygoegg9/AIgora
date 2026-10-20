# 06: 歷史頁表格

Status: ready-for-agent

Blocked by: 01

**What to build:** 把歷史頁改成原型 A 的表格，欄位是問題、討論模式、開始時間、結果 pill，頂部列顯示「N 場討論」。見 spec「歷史與唯讀紀錄」與原型 `?variant=A&screen=history`。原型裡的參與者與輪數欄位不做。

**Scope:**
- 修改 `frontend/src/pages/HistoryPage.vue`。可以在 `frontend/src/components/history/labels.ts` 新增顯示用的函式，但不改現有匯出的行為。
- 不修改 `RecordView.vue`、`RecordRound.vue`（屬於 07），不修改任何 E2E 檔案、store、契約、router、後端。

- [ ] 表格的每一列是 `history-item`，裡面的問題是連到 `discussion-record` 的 `RouterLink`，整列都可以點
- [ ] 結果 pill 依結果上色（取得共識：ok；未取得共識：warn；已完成：中性；已停止、參與者不足、錯誤：bad；進行中：accent），保留 `history-outcome`
- [ ] 載入中、錯誤、空清單（`history-empty`）都有樣式
- [ ] 窄螢幕不出現水平捲軸（問題欄可以換行）
- [ ] typecheck 與全部 E2E 通過；亮色、暗色各附一張截圖到 Comments

## Comments
