# 10: 後端：開始設定的模型覆寫、臨時參與者與紀錄

Status: resolved

Blocked by: —

**What to build:** `start` 訊息可以替參與者指定模型，也可以加入以設定檔參與者為範本的臨時參與者。後端把這些組成這場討論的參與者清單（含不重複的顯示名稱），紀錄記下實際使用的模型，提問轉共識討論時保留這些設定，舊紀錄仍然能讀取。見 spec「參與者與模型選擇」的「開始設定與紀錄」段落。

**Scope:**
- `backend/aigora/api/messages.py` 與 `frontend/src/contracts/messages.ts`：
  - 新增 `ExtraParticipant`。
  - `StartSettings` 新增 `models`、`extra_participants`（可省略）。
  - `DiscussionSettings` 新增 `models`、`extra_participants`（有預設值）。
  - 兩邊保持同步。v1 凍結的 WebSocket 契約在這張 ticket **刻意**修改，其他訊息型別不改。
- `backend/aigora/discussion/settings.py`：驗證新欄位，新增 `build_participants(settings, config)`（模型覆寫、臨時參與者、顯示名稱不重複）。
- `backend/aigora/api/handlers/discussion_socket.py`：`_build_engine` 改用 `build_participants`；提問轉共識討論時從來源複製 `models` 與 `extra_participants`。
- `backend/aigora/record.py`：`SCHEMA_VERSION = 2`；`frontend/src/contracts/record.ts` 如果需要就同步。
- 測試：`backend/tests/` 中新增 `test_participant_models.py`（或擴充現有的測試），加一份 schema 1 的紀錄 fixture。
- 不修改討論引擎（`engine.py`）、Adapter、`http_models.py`、`http.ts`（屬於 09），也不修改前端元件或 store。

- [x] 不帶新欄位的 `start` 行為和 v1 完全相同（既有測試不改就能通過）
- [x] `models` 覆寫使 Fake Adapter 收到該模型（`TurnRequest.participant.model`），`discussion_started` 與紀錄中的 `participants[].model` 是覆寫後的值
- [x] 臨時參與者可以發言、可以當主持人、可以在主持人接手時被選中；它的 id 出現在 `participant_ids` 與紀錄中
- [x] 不合法的情況回傳 `error`，而且不會開始討論：
  - id 格式錯誤、和設定檔參與者或其他臨時參與者重複
  - 範本不存在或已停用
  - 模型字串不合法
  - `models` 的鍵不在 `participant_ids` 中
  - `participant_ids` 中的臨時參與者 id 沒有對應的 `extra_participants`
- [x] 顯示名稱不重複：重複時加上「（模型）」或「（預設模型）」，仍然重複時依順序加「 2」「 3」；prompt 中參與者互相稱呼用的是改過的名稱
- [x] 提問轉共識討論後，參與者、模型、臨時參與者和原本的提問相同；範本已經從設定檔移除時回傳 `error`
- [x] schema 1 的紀錄 fixture 能被 `GET /api/discussions/{id}` 讀取，也出現在 `GET /api/discussions` 中
- [x] `tests/test_ws_messages.py` 的契約比對通過；`uv run --directory backend pytest`、`npm run typecheck --prefix frontend` 與全部 E2E 通過

## Comments

- 實作：`resolve_settings` 驗證新欄位（模型字串去掉頭尾空白後記下）；`build_participants` 在 `backend/aigora/discussion/settings.py`；`_build_engine` 與提問轉共識討論都改用它。範本已移除時由 `resolve_settings` 回傳「範本不存在或已停用」的 `error`。
- 契約補充（給 ticket 11）：
  - `models` 也可以指定臨時參與者的模型，優先於 `ExtraParticipant.model`。
  - `extra_participants` 中不在 `participant_ids` 的定義仍會驗證，但不寫進快照（快照只記參與這場討論的臨時參與者）。
  - 臨時參與者 id 不能和任何設定檔參與者重複，包含已停用的。
- TS 的 `DiscussionSettings.models` / `extra_participants` 標成可省略（`?`）：既有 E2E spec（`discussion-store.spec.ts`、`history.spec.ts`）自己建 `DiscussionSettings` 物件，而 spec 檔不在本 ticket 可改範圍；後端一律會送這兩欄。
- 刻意修改的測試：`tests/test_ask.py`、`tests/test_history.py` 中 `schema_version == 1` 的斷言改成 `2`（`SCHEMA_VERSION` 升版）。
- 新增 `backend/tests/test_participant_models.py` 與 fixture `backend/tests/fixtures/record-schema1-ask.json`（schema 1 的已完成提問：列表、讀取、轉共識討論都測）。

