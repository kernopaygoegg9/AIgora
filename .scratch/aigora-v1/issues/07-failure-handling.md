# 07: 失敗處理

**What to build:** 參與者出錯或超時時，該發言標為失敗並顯示原因，其他人繼續；連續 2 輪失敗的參與者被移出；剩不到 2 個參與者時討論結束；主持人失敗或被移出時由下一位接手。

**Scope:**
- 後端：討論引擎（逾時、失敗計數、移出、參與者不足）、共識討論模式（主持人接手）。
- 前端：討論頁中失敗、移出、主持人變更的提示元件。
- 不得修改熱點檔案（含前端路由、全域 store、主版面）。WebSocket 訊息型別已凍結：若需要新訊息類型，**停下回報，不要自行修改**。

**Blocked by:** 06

**Status:** ready-for-agent

- [ ] 發言逾時（依設定秒數）→ `turn_failed`（kind = timeout），其他參與者正常完成
- [ ] Adapter 回報失敗 → `turn_failed` 附原因
- [ ] 連續 2 輪失敗 → `participant_removed`；中間有一輪成功則重新計數
- [ ] 在場參與者少於 2 → outcome = insufficient_participants
- [ ] 主持人被移出 → `moderator_changed`，由清單中下一個在場者接手，討論繼續
- [ ] 討論紀錄的 `removed_participants`、`moderator_changes` 正確
- [ ] E2E：看到失敗與移出提示
