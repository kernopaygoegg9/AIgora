# 11: 設定頁：模型選擇與新增參與者

Status: resolved

Blocked by: 03, 09, 10

**What to build:** 在 03 做好的設定頁參與者表格中，加上每一列的模型選單，以及「＋ 新增參與者」（選 Adapter，再選模型，加入的臨時參與者可以移除），並把選擇轉成 `start` 的 `models` 與 `extra_participants`。見 spec「參與者與模型選擇」的介面段落。

**Scope:**
- 修改 `frontend/src/components/settings/` 底下的元件（`SettingsPanel.vue` 與 03 拆出的子元件）。
- 可以重用 04 的 `ParticipantLabel.vue`，但不能修改它（如果 04 還沒完成，就在 settings 底下自己顯示）。
- 新增 `frontend/e2e/participant-models.spec.ts`；其他 E2E 檔案不改。
- 不修改 `DiscussionPage.vue`、store、契約（09、10 已經改好）、router、後端。

- [x] 參與者表格新增「模型」欄：
  - 第一項是「預設（…）」，接著是 `ParticipantInfo.models`；`free_text_model` 時最後一項是「其他…」，選了會出現文字框。
  - `models_error` 顯示在選單旁。
  - 可存取名稱是「`<顯示名稱>` 的模型」。
  - 不可用的參與者不能選模型。
- [x] 只有勾選而且和設定檔不同的模型才放進 `models`
- [x] 「＋ 新增參與者」：
  - Adapter 選項是每個已啟用而且可用的 Adapter，範本取該 Adapter 在設定檔中的第一個參與者。
  - 加入的列預設勾選，有「臨時」標籤和移除按鈕（可存取名稱是「移除 `<名稱>`」）。
  - id 依 spec 的規則產生，而且不會重複。
- [x] 主持人選單也列出臨時參與者；主持人被移除時沿用現有的「改選第一個勾選的參與者」邏輯
- [x] 前端顯示的名稱遵守 spec 的不重複規則（重複時加上模型）
- [x] 回到設定頁時（04 的 `v-show`），模型選擇與臨時參與者都還在
- [x] `participant-models.spec.ts` 涵蓋以下情境（用 09 加到 `participants.e2e.toml` 的 fake 模型）：
  - 替 Fake A 選另一個模型後開始討論，卡片上顯示該模型。
  - 新增一個以 Fake A 為範本的臨時參與者，它也會發言，而且兩個名稱分得出來。
  - 移除臨時參與者。
  - 臨時參與者當主持人。
- [x] typecheck 與全部 E2E 通過；亮色、暗色各附一張截圖到 Comments

## Comments

### 2026-10-20 (agent)

做了什麼：
- 新增 `components/settings/ModelSelect.vue`：第一項「預設（<設定檔 model>／Adapter 預設）」，接著是 `models`；`free_text_model` 時最後一項「其他…」，選了出現文字框（可存取名稱「<名稱> 的自訂模型」）。`models_error` 以「清單載入失敗：…」顯示在選單旁，仍可選預設。
- `SettingsPanel.vue`：表格欄位改成「參與者／Adapter／模型／能力／狀態」（原「Adapter · 模型」拆開，模型改由選單表示）；名稱欄改用 `ParticipantLabel`（hide-web，模型 pill 顯示目前選的模型；未修改該元件）。不可用的參與者模型選單 disabled。
- 只有勾選、而且和設定檔不同的模型放進 `models`；臨時參與者放進 `extra_participants`（`model` 選預設時為 `null`），id 也照表格順序放進 `participant_ids`。兩者都是空的時不送，行為同 v1。「其他…」的名稱不合法（空白、超過 100 字元）時顯示提示並停用「開始討論」。
- 「＋ 新增參與者」：Adapter 選單（可存取名稱「新參與者的 Adapter」）、模型選單（「新參與者的模型」）、加入／取消。臨時列預設勾選，有「臨時」pill 與移除按鈕（「移除 <名稱>」）。id 規則 `<範本 id>-<n>`（n 從 2 起，小寫、非法字元換成 `-`），不和任何設定檔參與者或臨時參與者重複。
- 主持人選單列出所有勾選的參與者（含臨時）；移除時沿用既有 watch 改選第一個勾選者。
- 名稱：照後端 `_unique_names` 的規則，只在**已勾選**的參與者之間去重（重複加「（模型）」／「（預設模型）」，仍重複加「 2」「 3」）；未勾選的列顯示原名。勾選框、模型選單、移除按鈕、主持人選項都用這個名稱。
- 窄螢幕：640px 以下另外隱藏「能力」欄、模型選單可縮，375px 寬沒有水平捲軸；1024px 以上名稱列不換行。

和 ticket 不同的決定：
- 範本取該 Adapter 在設定檔中**第一個可用**的參與者（`/api/participants` 只回傳已啟用的參與者），而不是單純第一個，避免範本本身不可用。
- 名稱去重只算已勾選者（和後端快照一致）；所以未勾選的設定檔參與者和臨時參與者可能暫時同名，以「臨時」pill 與模型欄區分。

驗證：
- `npm run typecheck --prefix frontend` 乾淨。
- `npx playwright test`：39 passed（含新的 `participant-models.spec.ts` 4 個：選模型後卡片顯示該模型、以 Fake A 為範本的臨時參與者發言且名稱分得出來並在回到設定頁後保留、移除臨時參與者、臨時參與者當主持人並在移除後改選第一個勾選者）。既有 E2E 未修改。
- `uv run --directory backend pytest`：291 passed, 14 deselected。
- 截圖（1440×900，Fake B 選 fake-small、新增 fake-large 的臨時 Fake A，新增列展開）：亮色、暗色各一張，存在 repo 外的 scratchpad（`.../scratchpad/t11/settings-models-light.png`、`settings-models-dark.png`）。
