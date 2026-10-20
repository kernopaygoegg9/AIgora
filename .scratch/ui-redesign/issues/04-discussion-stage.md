# 04: 討論舞台、插話列與檢視器骨架

Status: ready-for-agent

Blocked by: 03

**What to build:** 把討論中與結束後的畫面改成原型 A 的樣子：
- 頂部列：問題、狀態、停止／開始共識討論。
- 結果區塊放在最上方。
- 每輪的發言卡片等寬並排。
- 輪下方是通知，以及「草案｜裁定」兩格。
- 插話列固定在底部。
- 右邊是檢視器骨架（插話佇列＋設定已鎖定）。

設定頁在討論開始後隱藏但不卸載。見 spec「討論中／結束後」與原型 `?variant=A&screen=live|consensus|noconsensus`。

**Scope:**
- 修改 `frontend/src/pages/DiscussionPage.vue` 與 `frontend/src/components/discussion/` 底下所有現有元件（`RoundSection`、`TurnCard`、`RoundConsensus`、`RoundNotices`、`DiscussionControls`、`DiscussionOutcome`、`StartConsensusButton`、`ParticipantAvatar`）。
- 新增 `frontend/src/components/discussion/DiscussionInspector.vue`。這張 ticket 只放「插話佇列」與「設定（已鎖定）」兩個區塊，參與者與表態追蹤由 05 加入。
- 新增 `frontend/src/styles/discussion.css`：發言卡片、草案、裁定、通知、結果區塊的共用 class，07 的唯讀紀錄會重用。
- 刻意修改的測試：`settings-panel.spec.ts` 中「討論進行中設定鎖定」的斷言，改成檢查檢視器的 `settings-locked` 可見、設定表單不可見。
- 不修改 store、契約、router、後端、`SettingsPanel.vue`。

- [ ] 討論開始後用 `v-show` 隱藏 `SettingsPanel`；回到設定頁時上一次的輸入還在
- [ ] 頂部列：`discussion-question`（單行省略，hover 顯示全文）、`discussion-status` pill；進行中顯示「停止」，提問結束後顯示「開始共識討論」與提示文字（保留 `start-consensus`）
- [ ] 結果區塊（`discussion-result`、`discussion-stopped`）在第 1 輪之前；取得共識、未取得共識、參與者不足各用不同的色系
- [ ] 發言卡片依 spec 呈現各種狀態；串流文字結尾有游標；表態用等寬字顯示
- [ ] 輪下方有通知（`participant-removed`、`moderator-changed`），以及「草案／額外呼叫｜裁定結果」兩格（`consensus-draft`、`extra-call`、`judge-result`、`stance`、`jev-probability`、`confirmation-result`、`confirmation-answer`）；Jev 機率有橫條與門檻刻度
- [ ] 底部固定插話列：label「插話」、按鈕「送出插話」，只在討論中、非唯讀、非提問時出現
- [ ] 檢視器：插話佇列（`interjection`，標示「第 N 輪起生效」）、設定（已鎖定）（`settings-locked`）
- [ ] 錯誤（`discussion-error`、連線中斷）顯示在頂部列下方
- [ ] 一輪的欄位太多時只有那一輪橫向捲動，頁面沒有水平捲軸
- [ ] typecheck 與全部 E2E 通過；討論中、取得共識、未取得共識三種畫面在亮色與暗色下各附截圖到 Comments

## Comments
