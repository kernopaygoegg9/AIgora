# 03: 提問 tracer bullet

**What to build:** 使用者在討論頁輸入問題、選幾個參與者（Fake Adapter），按下送出後，看到所有參與者的發言**同時**串流出現並排顯示；這一輪結束後討論結束，並存成一份討論紀錄 JSON。這是第一條貫穿所有層的完整路徑。

**Scope:**
- 後端：討論引擎（本 ticket 建立，之後由 04 → 06 → 07 → 08 依序修改）、Prompt Builder、提問模式、同時發言順序、討論紀錄儲存（寫入）、參與者清單與 WebSocket 端點的處理函式。
- 前端：討論頁的頁面與元件（輸入框、參與者勾選、並排的發言卡片）。
- 不得修改熱點檔案（見 `tickets-overview.md`）。WebSocket 訊息型別已凍結：若需要新訊息類型，**停下回報，不要自行修改**。

**Blocked by:** 02

**Status:** claimed

- [ ] API 測試（Fake Adapter）：送出 `start`（提問）後依序收到 `discussion_started`、`round_started`、各參與者的 `turn_started` / `turn_delta` / `turn_completed`、`round_completed`、`discussion_finished`（outcome = completed）
- [ ] 同一批次的參與者平行執行（總耗時接近最慢的一個，而不是加總）
- [ ] Prompt 中包含：參與者顯示名稱、用題目的語言回答、引用網路資料附網址
- [ ] 討論紀錄 JSON 欄位符合 spec，結束後可在資料夾中找到
- [ ] E2E：在瀏覽器中完成一次提問，看到兩個以上參與者的串流文字並排出現
