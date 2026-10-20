# 06: 插話與停止

**What to build:** 討論進行中，使用者可以插話，插話不打斷進行中的這一輪，從下一輪開始出現在所有參與者的 prompt 中；使用者按「停止」時，所有進行中的發言立即取消（子行程結束），討論存檔並結束。

**Scope:**
- 後端：討論引擎（插話佇列、取消）、Prompt Builder（插話內容）。
- 前端：討論頁的插話輸入與停止按鈕元件。
- 不得修改熱點檔案（含前端路由、全域 store、主版面）。WebSocket 訊息型別已凍結：若需要新訊息類型，**停下回報，不要自行修改**。

**Blocked by:** 04

**Status:** ready-for-agent

- [ ] 送出 `interject` 後收到 `interjection_queued`（applies_to_round = 下一輪）
- [ ] 插話內容出現在下一輪所有參與者的 prompt 中，不影響進行中的這一輪
- [ ] 討論紀錄的 `interjections` 正確
- [ ] 送出 `stop` 後進行中的發言被取消（Fake Adapter 可觀察到取消）、收到 outcome = stopped、紀錄已存檔
- [ ] E2E：插話與停止
