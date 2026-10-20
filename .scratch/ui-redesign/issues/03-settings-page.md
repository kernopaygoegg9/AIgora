# 03: 設定頁（舞台＋檢視器）

Status: ready-for-agent

Blocked by: 01

**What to build:** 把設定面板改成原型 A 的設定頁：舞台是問題、討論模式和參與者表格；檢視器是共識裁定方式與其他設定，加上「開始討論」按鈕。行為完全不變，包括預設值、依討論模式顯示欄位、至少 2 個參與者、不可用的選項不能選。見 spec「設定頁」與原型 `?variant=A&screen=settings`。

**Scope:**
- 修改 `frontend/src/components/settings/SettingsPanel.vue`（可以拆出 `components/settings/` 底下的子元件）。
- 刻意修改的測試：所有 E2E 檔案中的 `getByRole('button', { name: '送出' })` 改成 `{ name: '開始討論' }`，涉及 `ask-to-consensus`、`ask`、`consensus-jev`、`consensus`、`failure-handling`、`history`、`interject-and-stop`、`settings-panel` 這些 spec。這張 ticket 只能改這一種斷言。
- 不修改 `DiscussionPage.vue`（屬於 04）；不修改 store、契約、router、後端。

- [ ] `SettingsPanel` 自己排成舞台＋檢視器（300px）兩欄；1024px 以下檢視器移到下方
- [ ] 問題 `<textarea>` 的 label 是「問題」，Ctrl+Enter 送出
- [ ] 討論模式是分段控制，底下是原生 radio（`getByRole('radio', { name: '共識討論' })` 可以使用）
- [ ] 參與者表格：勾選（可存取名稱是顯示名稱）、頭像＋名稱、`adapter · model`、可上網／無上網 pill、可用／不可用：原因 pill；不可用的列淡化而且不能勾選；保留 `participant-option`、`participants-hint` testid
- [ ] 檢視器：共識裁定方式 radio 卡片（保留 `judge-options`、`judge-option`；不可用時灰色並顯示原因）、主持人、發言順序、輪數上限、逾時（秒）、Jev 門檻（選 Jev 時），label 文字不變
- [ ] 主要按鈕是「開始討論」，下方顯示「已選 N 個參與者 · 預設值來自 participants.toml」
- [ ] `locked` prop 的行為維持不變（04 會改成隱藏面板）
- [ ] typecheck 與全部 E2E 通過；亮色、暗色各附一張截圖到 Comments

## Comments
