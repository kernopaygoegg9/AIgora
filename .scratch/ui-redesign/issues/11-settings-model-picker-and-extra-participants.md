# 11: 設定頁：模型選擇與新增參與者

Status: ready-for-agent

Blocked by: 03, 09, 10

**What to build:** 在 03 做好的設定頁參與者表格中，加上每一列的模型選單，以及「＋ 新增參與者」（選 Adapter，再選模型，加入的臨時參與者可以移除），並把選擇轉成 `start` 的 `models` 與 `extra_participants`。見 spec「參與者與模型選擇」的介面段落。

**Scope:**
- 修改 `frontend/src/components/settings/` 底下的元件（`SettingsPanel.vue` 與 03 拆出的子元件）。
- 可以重用 04 的 `ParticipantLabel.vue`，但不能修改它（如果 04 還沒完成，就在 settings 底下自己顯示）。
- 新增 `frontend/e2e/participant-models.spec.ts`；其他 E2E 檔案不改。
- 不修改 `DiscussionPage.vue`、store、契約（09、10 已經改好）、router、後端。

- [ ] 參與者表格新增「模型」欄：
  - 第一項是「預設（…）」，接著是 `ParticipantInfo.models`；`free_text_model` 時最後一項是「其他…」，選了會出現文字框。
  - `models_error` 顯示在選單旁。
  - 可存取名稱是「`<顯示名稱>` 的模型」。
  - 不可用的參與者不能選模型。
- [ ] 只有勾選而且和設定檔不同的模型才放進 `models`
- [ ] 「＋ 新增參與者」：
  - Adapter 選項是每個已啟用而且可用的 Adapter，範本取該 Adapter 在設定檔中的第一個參與者。
  - 加入的列預設勾選，有「臨時」標籤和移除按鈕（可存取名稱是「移除 `<名稱>`」）。
  - id 依 spec 的規則產生，而且不會重複。
- [ ] 主持人選單也列出臨時參與者；主持人被移除時沿用現有的「改選第一個勾選的參與者」邏輯
- [ ] 前端顯示的名稱遵守 spec 的不重複規則（重複時加上模型）
- [ ] 回到設定頁時（04 的 `v-show`），模型選擇與臨時參與者都還在
- [ ] `participant-models.spec.ts` 涵蓋以下情境（用 09 加到 `participants.e2e.toml` 的 fake 模型）：
  - 替 Fake A 選另一個模型後開始討論，卡片上顯示該模型。
  - 新增一個以 Fake A 為範本的臨時參與者，它也會發言，而且兩個名稱分得出來。
  - 移除臨時參與者。
  - 臨時參與者當主持人。
- [ ] typecheck 與全部 E2E 通過；亮色、暗色各附一張截圖到 Comments

## Comments
