# 08: 共識裁定方式 B（Jev 判斷 + 反問確認）

**What to build:** 使用者選擇方式 B 時，第 2 輪起每輪由 Jev 判斷是否已取得共識；機率達門檻就反問每個參與者，全員同意則由主持人寫最終共識結果並結束，有人不同意則把理由帶進下一輪。`.env` 沒有 TypeSafe 金鑰時方式 B 不可用。

**Scope:**
- 後端：共識裁定方式 B、Jev Client、討論引擎（執行反問確認）、`.env` 讀取。
- 前端：討論頁中 Jev 機率與反問結果的顯示元件。
- 實作前先讀 TypeSafe 官方文件（llms.txt、API 或 Python SDK、Noul 等相關 primitive），依文件決定呼叫方式；金鑰只在後端讀取。
- 不得修改熱點檔案（含依賴清單；若需要 TypeSafe SDK，停下回報）。WebSocket 訊息型別已凍結：若需要新訊息類型，**停下回報，不要自行修改**。

**Blocked by:** 07

**Status:** ready-for-agent

- [ ] 無金鑰時，選項端點標示方式 B 不可用並附原因
- [ ] 假 Jev client（固定機率）下：低於門檻 → 繼續下一輪；達門檻 → 收到 `confirmation_result`
- [ ] 反問全員同意 → 主持人寫最終結果 → outcome = consensus
- [ ] 反問有人不同意 → 理由出現在下一輪的 prompt 中
- [ ] `judge_result` 的細節含 Jev 機率；討論紀錄的 `judge` 與 `confirmations` 正確
- [ ] 有金鑰時才執行的真實 Jev 測試：能取得 0–1 之間的機率
