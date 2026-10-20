# 04: 討論舞台、插話列與檢視器骨架

Status: resolved

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
- 新增 `frontend/src/components/discussion/ParticipantLabel.vue`：頭像＋名稱＋無上網 pill＋模型標籤（`ParticipantSnapshot.model`，`null` 時顯示「預設模型」），見 spec「參與者與模型選擇」的介面段落。發言卡片、裁定與反問的表態清單都改用它；05、07、11 也會重用。`model` 欄位本來就在快照裡，所以不需要等後端的 ticket。
- 新增 `frontend/src/styles/discussion.css`：發言卡片、草案、裁定、通知、結果區塊的共用 class，07 的唯讀紀錄會重用。
- 刻意修改的測試：`settings-panel.spec.ts` 中「討論進行中設定鎖定」的斷言，改成檢查檢視器的 `settings-locked` 可見、設定表單不可見。
- 不修改 store、契約、router、後端、`SettingsPanel.vue`。

- [x] 討論開始後用 `v-show` 隱藏 `SettingsPanel`；回到設定頁時上一次的輸入還在
- [x] 頂部列：`discussion-question`（單行省略，hover 顯示全文）、`discussion-status` pill；進行中顯示「停止」，提問結束後顯示「開始共識討論」與提示文字（保留 `start-consensus`）
- [x] 結果區塊（`discussion-result`、`discussion-stopped`）在第 1 輪之前；取得共識、未取得共識、參與者不足各用不同的色系
- [x] 發言卡片依 spec 呈現各種狀態；串流文字結尾有游標；表態用等寬字顯示
- [x] 發言卡片、表態清單、反問回答的名稱旁都有模型標籤（`ParticipantLabel`）；`turn-card` 的 `hasText: <顯示名稱>` 篩選仍然可以用
- [x] 輪下方有通知（`participant-removed`、`moderator-changed`），以及「草案／額外呼叫｜裁定結果」兩格（`consensus-draft`、`extra-call`、`judge-result`、`stance`、`jev-probability`、`confirmation-result`、`confirmation-answer`）；Jev 機率有橫條與門檻刻度
- [x] 底部固定插話列：label「插話」、按鈕「送出插話」，只在討論中、非唯讀、非提問時出現
- [x] 檢視器：插話佇列（`interjection`，標示「第 N 輪起生效」）、設定（已鎖定）（`settings-locked`）
- [x] 錯誤（`discussion-error`、連線中斷）顯示在頂部列下方
- [x] 一輪的欄位太多時只有那一輪橫向捲動，頁面沒有水平捲軸
- [x] typecheck 與全部 E2E 通過；討論中、取得共識、未取得共識三種畫面在亮色與暗色下各附截圖到 Comments

## Comments

- 2026-10-20：完成。
  - `discussion-status` 的文字維持「討論中／已結束」，因為測試用 `toHaveText` 比對全文。「· 第 N 輪」和結果 pill 放在旁邊的元素。
  - 刻意修改的測試（`settings-panel.spec.ts`）：
    - 鎖定斷言改成檢查 `discussion-inspector` 裡的 `settings-locked`，並確認 `settings-panel` 已隱藏。
    - 隱藏的元素 `getByRole` 預設找不到，所以 radio、checkbox、button 的 disabled 斷言加上 `includeHidden: true`，斷言本身保留。
    - 新增：回到設定頁時，上一次的問題和逾時都還在。
  - 行為：回到即時畫面時，如果 store 裡是已結束的討論，就 `reset()`，回到新討論的設定頁；進行中的討論照常顯示。原因是設定頁改成討論開始後隱藏，從唯讀紀錄點「討論」時原本會停在上一場已結束的討論（`history.spec.ts` 會檢查這點）。只改 `DiscussionPage.vue`，沒有改 store。
  - 發言卡片會另外顯示一行解析出來的表態（`STANCE: AGREE · 同意`）。AI 回覆的最後一行通常也有 STANCE，所以畫面上會出現兩次。要隱藏原文那一行需要改 store 或 markdown 的處理，不在這張 ticket 的範圍。
  - `discussion.css` 的 class 一律用 `d-` 開頭，從各元件 import（Vite 會去重）。不改 01 擁有的 `main.ts`。
  - 驗證：typecheck 通過，E2E 35 passed。截圖有討論中、取得共識、未取得共識三種畫面，亮色與暗色各一張，另外有 420px 的窄螢幕截圖。
