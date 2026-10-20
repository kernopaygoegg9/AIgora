# 02: 契約 + Fake Adapter

**What to build:** 把 spec 中的介面契約寫成程式碼，讓之後的 ticket 可以各自實作而不必互相溝通；並完成 Fake Adapter，讓開發與測試完全不花 AI 額度。

**Scope:**
- 後端：Adapter、討論模式、共識裁定方式、發言順序的介面定義；WebSocket 訊息型別（Python）；`participants.toml` 載入與驗證；Fake Adapter 模組；表態解析。
- 前端：WebSocket 訊息型別（TypeScript）；在 01 建好的全域 store 中填入「套用每一種伺服器訊息到討論狀態」的處理。
- **本 ticket 完成後，WebSocket 訊息型別（Python / TS）與全域 store 的事件處理即凍結。**

**Blocked by:** 01

**Status:** resolved

- [ ] 四種介面的定義與 spec「Implementation Decisions」一致
- [ ] Python 與 TypeScript 的 WebSocket 訊息型別涵蓋 spec 表格中所有 `type` 與欄位，兩邊一致
- [ ] `participants.toml` 載入：預設值正確；id 重複、Adapter 不存在、預設主持人不存在時啟動失敗並指出位置；`persona` 欄位被忽略並記錄提示
- [ ] Fake Adapter 可由 `options` 設定每輪回覆（含表態）、是否串流與速度、在第幾輪失敗與失敗種類、延遲、可用性
- [ ] 表態解析：最後一行 `STANCE: AGREE` / `STANCE: DISAGREE` 正確解析，其他情況回傳無法解析
- [ ] 前端 store 能把一串伺服器訊息套用成正確的討論狀態（以一串手寫訊息驗證）
