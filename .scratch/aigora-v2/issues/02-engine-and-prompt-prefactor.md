# 02: 引擎與 Prompt Builder 的 prefactor

**Type:** 程式（tdd，行為不變的重構）

**What to build:** 先把之後要用到的接點在引擎與 Prompt Builder 中鋪好，讓依序發言、插話位置、人設、上下文上限都能「只加不改」。行為與 v1 相同。

**Scope:**
- 討論模式介面新增「本輪順序」：給定討論狀態，回傳在場參與者 id 的排列，或「無」（用參與者清單順序，排除已移出者）。引擎每輪開始時取得本輪順序，交給發言順序排成批次，並送出 `round_started.order`、寫入紀錄 `rounds[].order`。
- 發言順序介面的說明改成「依序：每人一個批次，順序依傳入清單」（刪除 v1 的「每輪輪換第一位」）。
- 引擎在每次呼叫前建立可擴充的「呼叫上下文」（這次呼叫的參與者、用途、片段清單），之後的 ticket 在這裡加入人設與上下文預算。
- Prompt Builder 改成先產生有序片段（系統提示、人設（空）、問題／主題、各則歷史、插話、本次指示，每段標示種類與 `HistoryRef`），再串接成文字。問題為空字串時不輸出問題區塊。
- 插話在內部改用「生效位置」（輪 + 該輪第幾位之前）表示；同時發言時一律是下一輪開頭，所以行為不變。
- 額外呼叫寫入紀錄 `rounds[].extra_calls`（`purpose`、`participant_id`、`status`，`context` 為 null）。

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] 用 `echo_prompt` 的 Fake 參與者證明：同一組討論，重構前後送出的 prompt 文字完全相同（提問、共識討論、插話、方式 B 的反問各一例）
- [ ] `round_started.order` 與紀錄 `rounds[].order` 依清單順序填入，移出的參與者不在其中
- [ ] 紀錄 `rounds[].extra_calls` 記下草案、反問、最終結果等額外呼叫
- [ ] 既有後端測試與 E2E 全部通過
