# Spec: ui-redesign

Status: ready-for-agent

用語依 `GLOSSARY.md`。功能行為以 `.scratch/aigora-v1/spec.md` 為準。本 spec 主要改**外觀與版面**；唯一的功能變更是「參與者與模型選擇」（使用者 2026-10-20 決定一起做：「先併進去」），見下方同名段落。除此之外不改任何功能。

## Problem Statement

v1 功能完整、使用者滿意，但介面很陽春：瀏覽器預設的表單元件、灰白配色、所有東西由上往下堆成一長條。設定面板、討論內容、插話、停止按鈕、結果都擠在同一欄，討論進行中很難一眼看出「現在第幾輪、誰在回覆、離共識還有多遠」。

另外，參與者的模型寫死在 `participants.toml` 裡。想讓兩個 Claude 用不同模型互相討論，或臨時多加一個 Claude，只能先去改設定檔。設定檔本來就允許多個參與者使用同一個 Adapter，但介面上沒有辦法選模型，也沒有辦法臨時新增。

## Solution

採用原型的方向 **A — Studio**（使用者 2026-10-20 選定）：類似開發工具的**三欄工作台**，資訊密度高，提供**亮色與暗色兩種主題**，預設跟隨系統，也可以手動切換。

- **左欄（側欄）**：App icon + AIgora、「討論」「歷史」兩個導覽連結、最近的討論清單、主題切換。
- **中欄（舞台）**：目前的主要內容。設定頁是問題輸入框與參與者表格；討論中是頂部列（問題、狀態、停止）、每輪參與者並排的發言、輪與輪之間的共識草案與裁定結果，底部固定插話輸入框；結束後最上方是共識結果或分歧整理。
- **右欄（檢視器）**：設定頁放共識裁定方式與其他設定；討論中放參與者狀態、表態追蹤表、插話佇列，以及已鎖定的設定。
- 所有輪**連續往下捲**，不分頁、不自動收合。
- **參與者與模型選擇**：設定頁的參與者表格每一列都可以選模型；也可以「新增參與者」，以某個已設定的參與者為範本、換一個模型，臨時加進這場討論（例如 2 個 Claude 加 1 個 GPT）。使用同一個 Adapter 的參與者，在畫面上以名稱旁的模型標籤區分。

**視覺參考**：`.scratch/ui-redesign/prototype/index.html`（拋棄式原型，假資料）。從 repo 根目錄執行 `python -m http.server 5190 --bind 127.0.0.1`，打開 `http://127.0.0.1:5190/.scratch/ui-redesign/prototype/index.html?variant=A&screen=live`；`screen` 可以是 `settings`、`live`、`consensus`、`noconsensus`、`history`、`record`，`&theme=light|dark` 可以強制主題。原型裡的 B、C 兩個方向沒有被採用，只留作紀錄。**原型是參考，不是規格**：原型和本 spec 或 v1 行為衝突時，以本 spec 與 v1 為準。例如原型中「以此開始新討論」按鈕並不存在於產品裡，「開始共識討論」只在提問結束後出現。

## User Stories

1. As a 使用者, I want to 介面預設跟隨系統的亮色／暗色, so that 它和我的其他 App 一致。
2. As a 使用者, I want to 在側欄手動切換「跟隨系統 / 亮色 / 暗色」，而且下次打開時記得這個選擇, so that 我可以覆蓋系統設定。
3. As a 使用者, I want to 從側欄隨時看到最近的討論並點開, so that 不用先切到歷史頁。
4. As a 使用者, I want to 在設定頁用表格看到每個參與者的頭像、Adapter／模型、能否上網、是否可用, so that 一眼就能選人。
5. As a 使用者, I want to 共識裁定方式、主持人、發言順序、輪數上限、逾時（以及 Jev 門檻）集中在右欄, so that 問題和參與者有足夠空間。
6. As a 使用者, I want to 討論中在頂部列看到問題、目前狀態（第幾輪、討論中／結果）和停止按鈕, so that 不用捲動就能控制討論。
7. As a 使用者, I want to 每輪的參與者發言並排成等寬卡片，回覆中、完成、失敗、逾時用顏色與標籤區分, so that 一眼看出每個人的狀態。
8. As a 使用者, I want to 共識草案與裁定結果（表態或 Jev 機率條＋門檻刻度、反問確認）並排顯示在該輪下方, so that 我知道這輪後離共識多遠。
9. As a 使用者, I want to 移出討論、主持人接手的通知以醒目的提示列出現在該輪下方, so that 不會漏看。
10. As a 使用者, I want to 右欄有「表態追蹤」表（每輪 × 每個參與者：同意／不同意／失敗）, so that 看得出討論的收斂趨勢。
11. As a 使用者, I want to 右欄列出參與者目前狀態（回覆中、完成、失敗、已移出）與主持人標記, so that 不用在卡片間找。
12. As a 使用者, I want to 插話輸入框固定在舞台底部、插話佇列顯示在右欄並標示「第 N 輪起生效」, so that 隨時能插話並看到排隊中的內容。
13. As a 使用者, I want to 討論結束後，共識結果或「最終立場與仍有分歧的重點」以醒目的區塊顯示在舞台最上方, so that 不用捲到底就拿得到結論。
14. As a 使用者, I want to 歷史頁是表格（問題、討論模式、開始時間、結果）, so that 容易掃視與比較。
15. As a 使用者, I want to 唯讀紀錄和討論中畫面長得一樣（只是沒有插話與停止）並標示「唯讀紀錄」, so that 回顧時不用重新適應。
16. As a 使用者, I want to 討論結束後能從頂部列或側欄的「討論」回到設定頁開始新討論，而且上一次填的問題和選擇還在, so that 可以微調後再問一次。

### 參與者與模型選擇

17. As a 使用者, I want to 在設定頁替每個參與者從清單選模型（Claude 的別名、Codex 目錄中的模型、Ollama 已安裝的模型），預設是 `participants.toml` 中的模型, so that 不用改設定檔就能換模型。
18. As a 使用者, I want to 清單沒有我要的模型時自行輸入模型名稱（Claude、Codex）, so that 新模型一推出就能用。
19. As a 使用者, I want to 按「新增參與者」，選一個 Adapter 和模型，把它臨時加進這場討論, so that 我可以讓 2 個 Claude 加 1 個 GPT 一起討論，不用改設定檔。
20. As a 使用者, I want to 臨時新增的參與者可以移除、可以擔任主持人，而且只存在於這場討論, so that 它和設定檔中的參與者用起來一樣，但不會留在設定檔裡。
21. As a 使用者, I want to 使用同一個 Adapter 的參與者在發言卡片、表態、檢視器與唯讀紀錄中，名稱旁都標示模型, so that 我分得出誰是誰。
22. As a 使用者, I want to 討論紀錄記下每個參與者實際使用的模型，而且舊的紀錄仍然能打開, so that 回顧時知道是哪個模型說的。
23. As a 使用者, I want to 參與者名稱在同一場討論中不重複（重複時自動加上模型，仍然重複再加編號）, so that 參與者在討論中互相稱呼時不會混淆。

## Implementation Decisions

### 約束（所有 ticket）

- Vue 3 + Vite + TypeScript 維持不變；**不新增 npm 套件**（需要時停下來問使用者）。樣式用純 CSS（scoped + 全域 token），不引入 CSS 框架或字型套件。
- **不修改**：`frontend/src/stores/discussion.ts`（只能讀 state/getter，呼叫既有的 action，例如 `reset()`）、`frontend/src/router.ts`、討論引擎（`backend/aigora/discussion/engine.py`）。WebSocket／HTTP 契約與後端**只有** ticket 09、10 可以改，而且只能改「參與者與模型選擇」段落列出的部分。`backend/aigora/adapters/` 只有 09 可以改，只能新增列模型的功能，不能碰 `gemini.py` 或任何隔離參數（agy／gemini 另有 session 在處理）。
- 用語依 `GLOSSARY.md`；現有的標籤文字（`components/labels.ts`、`components/history/labels.ts`）沿用。
- 既有 Playwright E2E 的 `data-testid` 全部保留（可以移到新的元件上，但同一個 testid 要標在語意相同的元素上）。依賴 role／label 的選擇器（`getByLabel('問題')`、`getByRole('checkbox', { name: 'Fake A' })`、`getByRole('radio', { name: '共識討論' })`、`getByLabel('主持人')`、`getByLabel('插話')`、`getByRole('button', { name: '停止' })`、`getByRole('link', { name: '討論' / '歷史', exact: true })`、`getByRole('banner')` 包含 AIgora 等）也要能繼續使用。只有下面「刻意修改的測試」列出的情況才改測試，改的時候在 ticket 的 Comments 記下原因。
- 原生表單元件保留語意：分段按鈕底下仍是 `<input type="radio">`，表格中的勾選仍是 `<input type="checkbox">`，而且可存取名稱就是參與者顯示名稱（用 `<label>` 包住或 `aria-labelledby`）；下拉選單仍是 `<select>`。
- 頭像使用官方 logo，**僅限本機自用**的註記保留在 `.scratch/aigora-v1/spec.md` 與素材來源說明中，本次不改素材。
- 支援寬度：1280px 以上為主要設計；1024–1279px 檢視器縮窄；1024px 以下檢視器移到舞台下方；760px 以下側欄收成頂部列。任何寬度下頁面本身都不能出現水平捲軸；一輪的發言欄位太多時，只有那一輪的區塊可以橫向捲動。

### 設計 token 與主題

- 新增 `frontend/src/styles/tokens.css`（顏色、間距、圓角、字級、陰影 token）與 `frontend/src/styles/base.css`（reset、`body` 背景與文字色、字型、捲軸、焦點框、共用的 `.pill`、`.btn`、`.field` 等原子樣式），在 `main.ts` 匯入。AppLayout 原本的全域 `<style>` 移到這裡。
- 顏色 token（值以原型為準，可微調到 WCAG AA 對比）：

  | token | 暗色 | 亮色 | 用途 |
  |---|---|---|---|
  | `--bg` | `#0e1116` | `#f5f6f8` | 頁面背景 |
  | `--panel` | `#151a21` | `#ffffff` | 側欄、檢視器、卡片 |
  | `--panel-2` | `#1b212a` | `#eef1f5` | 次要底色、hover |
  | `--line` | `#262e39` | `#dde2e9` | 邊框、分隔線 |
  | `--text` | `#e6e9ee` | `#1c2230` | 主要文字 |
  | `--muted` | `#8b95a3` | `#687385` | 次要文字 |
  | `--accent` | `#7c9cff` | `#3d63dd` | 主色、回覆中、插話 |
  | `--ok` | `#3ecf8e` | `#13854f` | 同意、完成、取得共識 |
  | `--bad` | `#ff6b6b` | `#c9302c` | 不同意、失敗、移出、停止 |
  | `--warn` | `#f5b84b` | `#a86a00` | 無上網、未取得共識、Jev 機率 |

  另外每個語意色各有一組淡底與邊框（例如 `--ok-bg`、`--ok-line`），供 pill、失敗卡片、結果區塊使用。
- 字型：`'Segoe UI', 'Noto Sans TC', 'Microsoft JhengHei', system-ui, sans-serif`；表態行等機器文字用 `Consolas, 'Cascadia Mono', monospace`。基礎字級 13.5–14px（高密度）。
- 主題機制：`<html data-theme="light|dark">`。沒有設定時用 `prefers-color-scheme`（`:root` 預設暗色 token，`@media (prefers-color-scheme: light) { :root:not([data-theme="dark"]) {…} }`，再加 `:root[data-theme="light"]`）。使用者的選擇（`system` / `light` / `dark`）存在 `localStorage` 的 `aigora.theme`，所有讀寫都包在 try/catch 裡，讀不到就當作 `system`。`frontend/index.html` 加一小段內嵌 script，在載入前先套用已存的主題，避免閃一下。新增 `frontend/src/composables/useTheme.ts` 提供目前模式與切換。

### 版面（AppLayout）

- `AppLayout.vue` 改成兩欄：側欄（232px）＋ `<main>`。檢視器不在 layout 裡，由各頁面自己排成「舞台＋檢視器（300px）」，這樣 layout 不需要知道頁面內容。
- 側欄由上而下：
  - 頂層 `<header>`（維持 banner role）：App icon、AIgora，以及 `<nav>` 內的「討論」「歷史」兩個 `RouterLink`（名稱維持完全相同；「討論」做成側欄最上方的主要按鈕樣式）。
  - 「最近的討論」：呼叫既有的 `fetchDiscussions()`，最多顯示 20 筆（問題截成一行，下面是討論模式、時間、結果），每筆都是連到 `discussion-record` 的 `RouterLink`；目前看的那筆要標示。進入頁面時載入；`store.status` 變成 `running`（新紀錄產生）或 `finished` 時重新載入。最後是「查看全部 →」連到歷史頁。
  - 最底部：主題切換（跟隨系統 → 亮色 → 暗色 循環，顯示目前狀態）。
- 「討論」連結：目前已經在 `/` 而且討論已結束時，點下去要回到設定頁（呼叫 `store.reset()`；進行中的討論不受影響，回到 `/` 只是顯示它）。

### 設定頁（舞台＋檢視器）

- `SettingsPanel.vue` 自己排成兩欄：
  - 舞台：問題 `<textarea>`（label「問題」，Ctrl+Enter 送出）、討論模式分段控制（radio）、參與者表格（勾選、頭像＋顯示名稱、`adapter · model`、能力 pill「可上網／無上網」、狀態 pill「可用／不可用：原因」）、「請選擇至少 2 個參與者」提示。
  - 檢視器：共識裁定方式（radio 卡片：名稱＋說明，不可用時灰色並顯示原因）、主持人、發言順序（「依序（尚未提供）」disabled）、輪數上限、逾時（秒）、選 Jev 時的 Jev 門檻；底部是主要按鈕「開始討論」與「已選 N 個參與者 · 預設值來自 participants.toml」。
  - 只有討論模式用到的欄位才顯示（沿用現有的 `uses_settings` 邏輯）。
- 送出按鈕的文字從「送出」改成「**開始討論**」（刻意修改的測試，見下方）。
- 討論開始後設定頁**隱藏但不卸載**（`v-show`），所以回到設定頁時上一次填的問題和選擇都還在。原本的「討論進行中，設定已鎖定」改由討論中的檢視器「設定（已鎖定）」區塊表示，`data-testid="settings-locked"` 移到那裡。

### 討論中／結束後（舞台＋檢視器）

- 舞台頂部列：問題（`discussion-question`，單行省略，hover 顯示全文）、狀態 pill（`discussion-status`：「討論中 · 第 N 輪」／結果名稱，文字內容沿用現有標籤）、進行中顯示「停止」（danger 樣式），提問結束後顯示「開始共識討論」（`StartConsensusButton` 搬到這裡，提示文字保留）。
- 結果區塊（`DiscussionOutcome`，`discussion-result`）移到舞台**最上方、第 1 輪之前**；共識結果用綠色系，未取得共識用黃色系，參與者不足用紅色系。`discussion-stopped` 的說明也放在這裡。
- 每輪（`RoundSection`）：標題列「第 N 輪」＋（進行中）pill＋分隔線；發言卡片等寬並排（`TurnCard`：頭像、名稱、無上網 pill、狀態 pill；失敗或逾時卡片用紅色系底色並顯示原因；回覆中卡片用主色框線，串流文字結尾有游標；有表態時卡片底部用等寬字顯示 `STANCE: AGREE · 同意`）。
- 輪下方：通知（`RoundNotices`：移出討論用紅色系，主持人接手用中性色），接著是左右兩格：左格是共識草案／額外呼叫（`RoundConsensus` 的 draft 與 extra calls，主色淡底），右格是裁定結果（方式 A：各參與者表態 pill；方式 B：Jev 機率數字、橫條與門檻刻度；反問確認的回答與理由）。testid 全部沿用。
- 底部固定插話列（`DiscussionControls`）：只在討論中、非唯讀、非提問時出現；`<textarea>` 的 label 是「插話」（可以視覺隱藏），按鈕「送出插話」。停止按鈕移到頂部列。插話佇列清單從這裡移到檢視器。
- 新增 `DiscussionInspector.vue`（檢視器），由上而下：
  - 參與者：頭像、名稱、主持人 pill（`store.moderatorId`）、目前狀態（最新一輪該參與者發言的狀態；已移出的整列淡化並顯示「已移出」）。
  - 表態追蹤（只有共識討論，從第 2 輪開始）：表格，列是輪、欄是參與者頭像，格子是同意（綠點）、不同意（紅點）、失敗／未表態（紅色空心）、該輪沒有發言（空白）。資料只從 `store.rounds[].turns[].stance/status` 推導。
  - 插話佇列：`store.interjections`，每筆「第 N 輪起生效」＋內容（`data-testid="interjection"`）。
  - 設定（已鎖定）：討論模式、共識裁定方式、Jev 門檻（有的話）、發言順序、輪數上限、逾時（`data-testid="settings-locked"`）。
- 錯誤訊息（`discussion-error`、連線中斷）顯示在頂部列下方的紅色提示列。

### 歷史與唯讀紀錄

- 歷史頁：舞台只有一張表格，欄位是問題、討論模式、開始時間、結果 pill；頂部列顯示「N 場討論」。整列可以點；每列的問題本身是 `RouterLink`（`history-item` 裡要有一個 link，維持現有測試）。原型的「參與者頭像」「輪數」兩欄**不做**：`DiscussionSummary` 沒有這兩個欄位，而本次不改後端。
- 唯讀紀錄（`RecordView`／`RecordRound`）：版面和討論中畫面相同（頂部列＋結果區塊＋各輪＋檢視器），頂部列多一個「唯讀紀錄」標示，沒有插話列、停止或任何按鈕。檢視器顯示參與者（含已移出）、表態追蹤和設定快照，資料從紀錄 JSON 推導。`record-*` testid 全部沿用。為了讓兩邊外觀一致，發言卡片、草案、裁定、通知的**樣式**要共用（共用 CSS class 或小的展示元件），資料來源各自維持（store vs. 紀錄）。

### 參與者與模型選擇

調查結果見 `model-listing-findings.md`。

**名詞**：「設定檔參與者」是 `participants.toml` 中的 `[[participant]]`；「臨時參與者」是只在某場討論中存在、以某個設定檔參與者為**範本**複製出來的參與者。範本提供 Adapter、顯示名稱、頭像與 `options`（例如 Ollama 的位址），模型由使用者選。不另外寫進 `GLOSSARY.md`，兩者都還是「參與者」。

**列出模型（ticket 09）**

- `Adapter` 基底類別新增 `async def list_models(self, participant) -> ModelChoices`，預設回傳「沒有清單、不可自行輸入」。`ModelChoices` 包含 `models: list[ModelOption(id, label)]`、`free_text: bool`、`error: str | None`。和可用性檢查一樣**不能花額度**。
- 實作：
  - claude：固定清單 `fable`、`opus`、`sonnet`、`haiku`，可以自行輸入。
  - codex：`codex debug models`，取 `visibility == "list"` 的模型並依 `priority` 排序，可以自行輸入。
  - ollama：`GET /api/tags`，不可以自行輸入。
  - fake：讀 `options.models`。
  - gemini：不修改，沿用預設。
- 結果依（Adapter、options）快取 5 分鐘；失敗時 `error` 寫原因，`models` 為空。
- HTTP：`ParticipantInfo` 新增 `models: list[ModelOption]`、`free_text_model: bool`、`models_error: str | None`。`GET /api/participants` 和可用性檢查一起同時查詢，不可用的參與者回傳空清單。`model` 欄位維持設定檔中的值（`null` 代表 Adapter 預設）。
- Python 與 TypeScript 契約保持同步（`tests/test_ws_messages.py` 會比對）。

**開始設定與紀錄（ticket 10）**

- `StartSettings` 新增兩個可省略的欄位，省略時行為和 v1 完全相同：
  - `models: dict[str, str]`：參與者 id → 這場討論使用的模型。
  - `extra_participants: list[ExtraParticipant]`：`ExtraParticipant = { id, template_id, model }`，`model` 是 `null` 時沿用範本的模型。
- `participant_ids` 仍然是這場討論**全部**參與者的有序清單，臨時參與者的 id 也放在裡面，所以主持人可以是臨時參與者。發言順序與主持人接手的順序都依這個清單。
- 臨時參與者的 id 由前端產生，規則是 `^[a-z0-9][a-z0-9_-]{0,63}$`，不能和任何設定檔參與者或其他臨時參與者重複。範本必須是已啟用的設定檔參與者。
- 模型字串：去掉頭尾空白後 1–100 字元、不能有空白字元。後端**不**比對清單（清單可能過時，Claude 也接受完整名稱）；錯的模型會在發言時失敗，走 v1 的失敗處理。
- 顯示名稱：臨時參與者沿用範本的顯示名稱。整場討論的顯示名稱要唯一：重複的名稱全部加上「（模型）」，沒有指定模型時加「（預設模型）」；這樣仍然重複的，依清單順序加上「 2」「 3」。改名只影響這場討論（快照、prompt、紀錄），不影響設定檔。
- 新增 `build_participants(settings, config) -> list[ParticipantConfig]`（放在 `backend/aigora/discussion/settings.py`）：把設定檔參與者套上模型覆寫（`dataclasses.replace`），用範本建出臨時參與者，最後套用名稱規則。`_build_engine` 改用它，討論引擎本身不改。
- `DiscussionSettings`（鎖定的設定快照）新增 `models: dict[str, str] = {}` 與 `extra_participants: list[ExtraParticipant] = []`，把解析後的值原樣記下來。
- **提問轉共識討論**：除了 `participant_ids`，`models` 與 `extra_participants` 也從來源提問的 `settings` 複製，再用 `build_participants` 重建，所以轉換後還是同樣的參與者與模型。如果來源紀錄中的範本已經從設定檔移除，就回傳 `error`。
- **紀錄**：`ParticipantSnapshot.model` 本來就存在，改成記下**實際使用**的模型（覆寫後的值）。`SCHEMA_VERSION` 改成 2；schema 1 的紀錄沒有新欄位，靠預設值仍然能讀取，歷史清單與唯讀紀錄都正常顯示（要有測試）。
- WebSocket 的其他訊息型別不變；`discussion_started` 本來就帶完整的 `settings` 與 `participants` 快照，所以會自動帶出新欄位。

**介面（ticket 11 與 04、05、07）**

- 設定頁的參與者表格新增「模型」欄：
  - 下拉選單第一項是「預設（`<設定檔的 model>` 或「Adapter 預設」）」，接著是清單中的模型。可以自行輸入時，最後一項是「其他…」，選了會出現文字框。
  - 清單載入失敗時顯示 `models_error`，但仍然可以選預設。
  - 可存取名稱是「`<顯示名稱>` 的模型」。只有勾選的參與者才送 `models`，而且和設定檔的值不同才送。
- 表格下方「＋ 新增參與者」：
  1. 先選 Adapter，選項是每個已啟用、可用的 Adapter，範本取該 Adapter 在設定檔中的第一個參與者。
  2. 再選模型，選單和上面相同。
  3. 加入後新的一列預設勾選，有「臨時」標籤和移除按鈕。
  - 主持人下拉選單也會列出臨時參與者。
  - 前端顯示的名稱和後端規則相同：重複時加上模型；後端的快照才是最後結果。
- 模型標籤：發言卡片、裁定與反問的表態清單、檢視器的參與者、唯讀紀錄中，名稱旁顯示 `ParticipantSnapshot.model`。是 `null` 時顯示「預設模型」。用小號、低對比的 pill，所有參與者一律顯示。共用元件是 `ParticipantLabel.vue`（頭像＋名稱＋無上網＋模型），由 04 建立，05、07、11 重用。
- 歷史清單（`DiscussionSummary`）不變，不顯示參與者。

### 刻意修改的測試

只有下面這些可以改，其餘 E2E 要原樣通過：

1. 送出按鈕改名：`getByRole('button', { name: '送出' })` → `{ name: '開始討論' }`。
2. 鎖定設定：`settings-panel.spec.ts` 中討論進行中的斷言改成檢查檢視器的 `settings-locked` 是否可見，並確認設定表單已經不顯示；不再要求面板內的「問題」是 disabled。
3. 唯讀頁「沒有任何按鈕／文字輸入框」（由 02 修改）：側欄的主題切換是按鈕，所以 `history.spec.ts` 的 `page.getByRole('button')`、`page.getByRole('textbox')` 改成在 `record-view` 範圍內檢查。
4. 其他因為 DOM 結構改變而必須調整的選擇器，在對應 ticket 的 Comments 寫明原因；**不可以**用刪除斷言的方式讓測試通過。

## Testing Decisions

- 不新增前端單元測試（沿用 v1 決策）。行為由既有 Playwright E2E 保證：每張 ticket 完成時跑 `npm run typecheck --prefix frontend` 和 `cd frontend && npx playwright test`，全部通過。
- 視覺驗收：每張 ticket 完成時用 Fake Adapter 實際跑一次（`npm run dev --prefix frontend`），亮色與暗色各截一張圖附在 ticket 的 Comments，和原型 A 對照。最後的整合 ticket 由使用者目視驗收。
- 新增一個 E2E：切換主題後 `<html>` 的 `data-theme` 改變，重新整理後仍保留（`theme.spec.ts`）。
- 參與者與模型選擇：
  - 後端測試走 v1 的主接縫（HTTP／WebSocket API＋Fake Adapter），涵蓋：
    - 參與者清單帶出模型清單（fake 的 `options.models`）。
    - 模型覆寫使 Fake Adapter 收到該模型，紀錄的快照寫下覆寫後的模型。
    - 臨時參與者可以發言、可以擔任主持人。
    - 名稱重複的處理。
    - 不合法的 id、範本、模型回傳 `error`。
    - 提問轉共識討論保留模型與臨時參與者。
    - schema 1 的舊紀錄可以讀取。
  - claude、codex、ollama 的 `list_models` 用假 CLI（`tests/fake_*_cli.py`）或假的 HTTP 回應測試；真實 CLI 的測試標記 `real_ai`。
  - 前端新增 `e2e/participant-models.spec.ts`：選模型、新增與移除臨時參與者、開始討論後卡片上的模型標籤。

## Out of Scope

- 「參與者與模型選擇」以外的任何功能或行為改變（包含新的討論模式、匯出）。
- 在介面上編輯或寫回 `participants.toml`（臨時參與者與模型覆寫只存在於單場討論和它的紀錄中）。
- 臨時參與者的顯示名稱、頭像、人設由使用者自訂（沿用範本）。
- 推理強度（reasoning effort）等模型以外的 Adapter 參數。
- gemini／agy 的模型清單。
- 討論引擎與 store 事件處理的修改。
- 新素材（App icon、頭像沿用 `assets/`）。
- 原型 B（Agora）與 C（Roundtable）的元素。
- 行動裝置的完整最佳化（只保證 760px 以下不破版、可以操作）。
- 桌面 App 打包。

## Further Notes

- 原型是在 `.scratch/ui-redesign/prototype/` 用純 HTML 加假資料寫成的拋棄式程式碼，不要複製到 `frontend/src`；整合 ticket 完成後可以刪掉。
- 「最近的討論」側欄沒有分頁，`fetchDiscussions()` 回傳全部後在前端取前 20 筆。如果之後紀錄很多導致變慢，再另開 ticket 給後端加分頁。
