# 06: 歷史頁表格

Status: resolved

Blocked by: 01

**What to build:** 把歷史頁改成原型 A 的表格，欄位是問題、討論模式、開始時間、結果 pill，頂部列顯示「N 場討論」。見 spec「歷史與唯讀紀錄」與原型 `?variant=A&screen=history`。原型裡的參與者與輪數欄位不做。

**Scope:**
- 修改 `frontend/src/pages/HistoryPage.vue`。可以在 `frontend/src/components/history/labels.ts` 新增顯示用的函式，但不改現有匯出的行為。
- 不修改 `RecordView.vue`、`RecordRound.vue`（屬於 07），不修改任何 E2E 檔案、store、契約、router、後端。

- [x] 表格的每一列是 `history-item`，裡面的問題是連到 `discussion-record` 的 `RouterLink`，整列都可以點
- [x] 結果 pill 依結果上色（取得共識：ok；未取得共識：warn；已完成：中性；已停止、參與者不足、錯誤：bad；進行中：accent），保留 `history-outcome`
- [x] 載入中、錯誤、空清單（`history-empty`）都有樣式
- [x] 窄螢幕不出現水平捲軸（問題欄可以換行）
- [x] typecheck 與全部 E2E 通過；亮色、暗色各附一張截圖到 Comments

## Comments

- 2026-10-20：完成。
  - `history-item` 標在 `<tr>` 上，問題本身是 `RouterLink`（`@click.stop`，避免重複導覽），整列可以點。
  - 640px 以下隱藏「討論模式」欄，時間可以換行。
  - 驗證：typecheck 通過，E2E 35 passed，有亮色與暗色截圖。
