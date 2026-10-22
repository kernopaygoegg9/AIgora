# 01: 契約與設定擴充（expand）

**Type:** 程式（tdd）

**What to build:** 把 v2 需要的所有新欄位一次加進前後端契約、討論紀錄與設定載入，全部可省略或有預設值。這張做完後行為和 v1 完全相同，之後的 ticket 不必再改契約檔。

**Scope:**
- WebSocket 訊息、HTTP 回應、討論紀錄的 Python 與 TypeScript 兩邊（spec「WebSocket 訊息變更」「HTTP API」「討論紀錄 JSON」）：
  - 新型別 `ContextUsage`、`HistoryRef`。
  - `ModeId` 新增 `chat`；`TurnPurpose` 新增 `chat_summary`；`DiscussionResult.kind` 新增 `chat_summary`。
  - `StartSettings` / `DiscussionSettings` 新增 `personas`、`context_limits`、`keep_question`。
  - `round_started.order`、`turn_started.context`、`draft_created.next_order` / `next_order_source`、`interjection_queued.applies_before_turn`。
  - `ParticipantInfo.persona` / `context_limit`；`OptionsResponse` 的 `chat_max_rounds`、`keep_question` 預設值與 `token_counter`。
  - 紀錄 `SCHEMA_VERSION = 3`：`rounds[].order` / `next_order` / `next_order_source` / `extra_calls`、`turns[].context`、`interjections[].applies_before_turn`。
- `participants.toml`：`persona` 正式啟用（≤ 2,000 字，超過時載入失敗並指出行號），移除「保留欄位」的日誌；`context_limit`（整數 ≥ 100）；`[defaults] chat_max_rounds`（預設 100）、`keep_question`（預設 true）。更新 `participants.example.toml`。
- 設定解析：`personas`、`context_limits`、`keep_question` 的預設值與驗證（spec「設定」），快照中每個參與者都有解析後的值；臨時參與者的人設預設沿用範本。
- 新欄位暫時只有預設值：`order` 依實際發言順序填、`context` 為 null、`token_counter` 為 `estimate`、`next_order*` 為 null。

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] `test_ws_messages.py` 比對 Python 與 TypeScript 契約，全部欄位一致
- [ ] schema 1、2 的舊紀錄仍可透過 `GET /api/discussions/{id}` 讀取，新欄位為預設值
- [ ] 新紀錄寫出 `schema_version: 3` 與新欄位
- [ ] `participants.toml` 新欄位的載入與錯誤（人設過長、上下文上限 < 100、型別錯誤）有測試，錯誤訊息指出行號
- [ ] `start` 帶人設、上下文上限、`keep_question` 時存進鎖定快照；驗證錯誤以 `error` 訊息回傳（id 不在這場、上限 < 100、人設過長）
- [ ] `/api/participants` 回傳 `persona`、`context_limit`；`/api/options` 回傳 `chat_max_rounds`、`keep_question`、`token_counter`
- [ ] 既有後端測試與 E2E 全部通過，沒有任何行為變化
