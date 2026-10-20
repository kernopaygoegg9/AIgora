# Spec: aigora-v1

Status: ready-for-agent

用語依 `GLOSSARY.md`；相關決策見 `docs/adr/0001`、`docs/adr/0002`；原始想法見 `docs/IDEA.md`。

## Problem Statement

我同時在用 Claude Code、Codex CLI、Gemini CLI。同一個問題要開三個終端機分別問，再自己來回複製貼上比較答案；想讓它們互相看對方的看法、討論出結論，更要自己手動轉貼好幾輪，非常耗時。而且各家 CLI 都是會讀寫檔案、執行指令的 coding agent，直接拿來「聊天」時，我也不希望它們碰到我電腦上的檔案。

## Solution

AIgora 是一個本機執行的網頁應用程式（之後包成桌面 App）。我在一個視窗裡提出問題，選擇要哪些參與者回答：

- **提問**：所有參與者同時回答一輪，回覆並排顯示，方便比較。
- **共識討論**：參與者多輪接力討論，每輪都看得到之前所有人的發言，直到共識裁定方式判定取得共識，或到達輪數上限；最後輸出共識結果，或各方立場與分歧點。

提問結束後可以一鍵把它轉成共識討論。參與者可以上網查資料（並附出處），但完全無法讀寫我的本機檔案。新增一種 AI 只需要加一個 Adapter 和一段設定，不需要改核心程式。

## User Stories

### 提問與參與者選擇
1. As a 使用者, I want to 在一個輸入框輸入問題並發給多個參與者, so that 我不用開多個終端機分別問。
2. As a 使用者, I want to 在每場討論開始前勾選要參加的參與者, so that 我可以只問其中幾個 AI。
3. As a 使用者, I want to 看到所有參與者的發言並排顯示, so that 我可以直接比較答案。
4. As a 使用者, I want to 看到每個發言即時串流出現, so that 我不必等到全部完成才看得到內容。
5. As a 使用者, I want to 對不支援串流的參與者看到「回覆中」的狀態，完成後一次顯示全文, so that 我知道它還在工作。
6. As a 使用者, I want to 選擇「提問」討論模式時只進行一輪就結束, so that 簡單的問題不會浪費額度。
7. As a 使用者, I want to 在提問結束後按「開始共識討論」, so that 我看完答案後覺得值得討論時，不用重打問題。
8. As a 使用者, I want to 轉成共識討論時，原本的提問發言直接當作第 1 輪, so that 已經花掉的額度不會重來一次。

### 共識討論
9. As a 使用者, I want to 選擇「共識討論」讓參與者多輪接力討論, so that 它們能互相修正、收斂出結論。
10. As a 使用者, I want to 每一輪每個參與者都看到題目與之前所有發言, so that 討論是真的互相回應，而不是各說各話。
11. As a 使用者, I want to 第 1 輪是自由回答、不需要表態, so that 參與者先各自提出看法。
12. As a 使用者, I want to 從第 1 輪結束後由主持人整理共識草案, so that 大家有一個具體的版本可以表態。
13. As a 使用者, I want to 主持人和其他參與者一樣發言並對自己的草案表態, so that 主持人不會有特權。
14. As a 使用者, I want to 指定哪個參與者擔任主持人（預設為第一個）, so that 我可以選我信任的 AI 來整理結論。
15. As a 使用者, I want to 選擇共識裁定方式 A（主持人 + 全員表態）, so that 不需要任何額外金鑰就能用。
16. As a 使用者, I want to 選擇共識裁定方式 B（Jev 判斷 + 反問確認）, so that 我可以實驗用 Jev 判斷是否已有共識。
17. As a 使用者, I want to 沒有設定 TypeSafe 金鑰時看到方式 B 是灰色不可選, so that 我知道為什麼不能用。
18. As a 使用者, I want to 方式 B 中 Jev 判斷為是時，再反問每個參與者是否同意已取得共識, so that 不會只憑 Jev 一方就結束。
19. As a 使用者, I want to 反問時有任何參與者不同意，它的理由會帶進下一輪, so that 討論能針對分歧繼續。
20. As a 使用者, I want to 看到每輪的共識草案、各參與者的表態、以及（方式 B）Jev 的機率, so that 我知道離共識還有多遠。
21. As a 使用者, I want to 設定輪數上限（預設 15）, so that 討論不會無止盡消耗額度。
22. As a 使用者, I want to 達成共識時看到一份獨立顯示的共識結果, so that 我能直接拿走結論。
23. As a 使用者, I want to 未達成共識時看到「各參與者的最終立場」與「仍有分歧的重點」, so that 我還是能得到有用的整理。

### 介入與控制
24. As a 使用者, I want to 討論中隨時插話（補充資訊或修正問題）, so that 我能引導討論方向。
25. As a 使用者, I want to 插話時正在進行的這一輪不被打斷，插話內容從下一輪開始生效, so that 已經在進行的發言不會被浪費。
26. As a 使用者, I want to 按「停止」立即結束整場討論, so that 我發現方向不對時能馬上止損。
27. As a 使用者, I want to 在開始前的設定面板調整這場討論的討論模式、參與者、共識裁定方式、主持人、發言順序、輪數上限, so that 每場討論可以用不同設定，而不用改設定檔。
28. As a 使用者, I want to 設定面板預設值來自設定檔, so that 我常用的設定不用每次重選。
29. As a 使用者, I want to 討論開始後設定就鎖定, so that 討論紀錄與實際行為一致。

### 失敗處理
30. As a 使用者, I want to 某個參與者出錯或超時時，該發言標為「失敗」並顯示原因，其他人繼續, so that 一個 AI 掛掉不會拖垮整場討論。
31. As a 使用者, I want to 參與者連續 2 輪失敗就被移出這場討論，並看到通知, so that 不會一直等一個壞掉的 AI。
32. As a 使用者, I want to 剩下不到 2 個參與者時討論自動結束並說明原因, so that 不會變成一個 AI 自言自語。
33. As a 使用者, I want to 設定每個發言的逾時時間（預設 5 分鐘）, so that 需要上網查資料的發言有足夠時間。
34. As a 使用者, I want to 在選參與者時就看到哪些參與者目前不可用（例如 CLI 沒安裝或沒登入）, so that 開始前就知道問題。
35. As a 使用者, I want to 主持人失敗或被移出時，由下一個仍在場的參與者接手主持, so that 共識討論可以繼續。

### 參與者與擴充
36. As a 使用者, I want to 在設定檔中定義參與者（Adapter、模型、顯示名稱、頭像）, so that 我能管理可用的 AI。
37. As a 使用者, I want to 同一個 Adapter 建立多個參與者（例如不同模型）, so that 我能讓同一家的不同模型互相討論。
38. As a 使用者, I want to 不能上網的參與者（例如 Ollama）也能加入，並在介面上標示「無上網」, so that 我知道它的回答沒有查證。
39. As a 開發者, I want to 新增一種 AI 只需要寫一個 Adapter 並在設定檔加一段, so that 核心程式不用改。
40. As a 開發者, I want to 用 Fake Adapter 開發前端與跑測試, so that 不用花任何 AI 額度。
41. As a 開發者, I want to 參與者設定中已保留人設欄位, so that 之後加入人設功能時不用改設定格式。
42. As a 開發者, I want to 討論模式、共識裁定方式、發言順序都是可替換的模組, so that 之後加入吵架、法庭等模式、或依序發言時不用改核心。

### 發言內容
43. As a 使用者, I want to 參與者用和問題相同的語言回覆, so that 我讀起來一致。
44. As a 使用者, I want to 參與者引用網路資料時附上網址, so that 我可以自己查證。
45. As a 使用者, I want to 看到每個發言是哪個參與者說的（顯示名稱與頭像）, so that 討論容易閱讀。

### 安全
46. As a 使用者, I want to 參與者完全無法讀寫我電腦上工作資料夾以外的檔案, so that 我的私密檔案（如 `~/.ssh`、其他專案的 `.env`）不會外洩。
47. As a 使用者, I want to 參與者不會載入我自己為各 CLI 設定的 MCP、外掛、hooks, so that 這些額外工具不會變成讀檔的後門。
48. As a 開發者, I want to 每個 Adapter 都有 canary 自動測試, so that CLI 升級後可以快速確認隔離仍然有效。
49. As a 使用者, I want to TypeSafe 金鑰只放在 `.env` 且只有後端讀取, so that 金鑰不會出現在瀏覽器裡。

### 紀錄
50. As a 使用者, I want to 每場討論自動存成一份本機紀錄, so that 我之後可以回顧。
51. As a 使用者, I want to 在歷史清單中看到過去的討論並以唯讀方式打開, so that 我能找回之前的結論。
52. As a 使用者, I want to 討論進行中每輪結束就存檔, so that 程式中途關掉也不會全部遺失。

## Implementation Decisions

### 架構總覽

- **後端（Python，FastAPI，uv 管理）**擁有所有討論邏輯：Adapter、討論引擎、討論模式、共識裁定方式、發言順序、Jev client、設定載入、討論紀錄儲存、HTTP / WebSocket API。
- **前端（Vue + Vite + TypeScript）**只負責顯示與輸入，不含任何討論邏輯；所有狀態以後端推送的事件為準。
- 前後端只透過下方的 **HTTP API 與 WebSocket 訊息契約**溝通。這份契約一旦定好，前端與後端可以並行開發（前端先接 Fake Adapter 跑的真後端）。
- 第一版是本機網頁（後端同時提供前端靜態檔），之後再包成桌面 App；桌面版沿用同一套前端，後端以子行程附帶。
- 第一版只保證 Windows，但不寫死 Windows 路徑。

### 模組

| 模組 | 責任 | 不負責 |
|---|---|---|
| Adapter（每種 AI 一個）+ Adapter Registry | 啟動 CLI 子行程、套用隔離參數、解析 CLI 輸出成統一事件、宣告能力 | 組 prompt、解析表態、判斷共識 |
| Prompt Builder | 把題目、之前所有發言、插話、共識草案、本輪指示組成送給參與者的完整文字 | 呼叫 AI |
| 討論引擎 (Discussion Engine) | 依討論模式與發言順序執行輪、平行執行發言、逾時、失敗計數與移除、插話佇列、停止、發出事件、每輪存檔 | 決定「下一步做什麼」的規則（交給討論模式與共識裁定方式） |
| 討論模式（提問、共識討論） | 決定每輪的指示、輪結束後要繼續、做額外呼叫（例如草案），或結束 | 實際執行呼叫 |
| 共識裁定方式（A：全員表態、B：Jev） | 判斷是否已取得共識，必要時要求反問確認 | 實際執行呼叫 |
| 發言順序（同時；依序只定介面） | 把一輪的參與者排成執行批次 | — |
| 表態解析 | 從發言最後一行解析 `STANCE: AGREE` / `STANCE: DISAGREE` | — |
| Jev Client | 呼叫 TypeSafe API，回傳「已取得共識」的機率 | 決定門檻（交給共識裁定方式 B） |
| 設定載入 | 讀 `participants.toml` 與 `.env`，驗證並提供預設值 | — |
| 討論紀錄儲存 (Discussion Store) | 每場討論一份 JSON；列表與讀取 | 繼續舊討論（不支援） |
| API 層 | HTTP 端點與 WebSocket，將引擎事件轉成訊息 | 討論邏輯 |
| 前端 | 設定面板、討論畫面（每輪參與者並排、草案與裁定結果顯示在輪與輪之間）、歷史清單 | 任何討論邏輯 |

### Adapter 介面

每個 Adapter 提供：

- **識別碼**：例如 `claude`、`codex`、`gemini`、`ollama`、`fake`。在 `participants.toml` 中以此指定。
- **能力宣告**：
  - `web_access`：是否能上網查資料（Ollama 為否）。
  - `streaming`：是否能邊產生邊回傳文字。
- **可用性檢查**：回傳可用 / 不可用與原因（例如找不到 CLI、未登入）。前端在選參與者時顯示。
- **執行一次發言**：輸入為「發言請求」，輸出為非同步事件串流。
  - 發言請求包含：參與者設定（模型、顯示名稱、人設欄位、Adapter 專屬選項）、Prompt Builder 組好的完整文字、這次發言的工作資料夾、逾時秒數。
  - 輸出事件只有三種：`delta`（一段新文字，只有 streaming 的 Adapter 會發）、`completed`（完整文字）、`failed`（失敗種類與原因：not_available、auth、quota、timeout、crashed、unknown）。
  - 被取消時（停止或逾時）必須結束子行程。
- **隔離責任（ADR 0002）**：Adapter 必須關掉 CLI 的所有本機工具（shell、檔案讀寫、MCP、外掛、hooks、技能等）、忽略使用者自己的 CLI 設定檔，只保留網路搜尋類工具；在工作資料夾中執行。已實測可行的參數組合：
  - Claude：非互動模式、只開放並預先允許 WebSearch / WebFetch、嚴格 MCP 設定（不載入任何 MCP）、不載入任何設定來源、停用技能。
  - Codex：非互動 exec、啟用網路搜尋、忽略使用者設定與規則、唯讀 sandbox、停用 shell 與其他十餘個本機 feature；`code_mode_host` 不能停用（停用後網路搜尋失效）。
  - Gemini：尚未安裝，實作該 Adapter 時再找出等效參數並以 canary 測試驗證。
  - Ollama：本身沒有工具，以本機 HTTP API 呼叫。
- **無狀態**：每次發言都送完整討論內容，不使用 CLI 的 resume（ADR 0001）。
- **Registry**：核心只透過識別碼查 Adapter。新增 Adapter = 新增一個模組並註冊，不改引擎。
- **Fake Adapter**：正式的 Adapter，用於測試與無額度開發。可在選項中設定：每輪的回覆文字（含表態）、是否串流與速度、在第幾輪失敗與失敗種類、延遲時間、可用性。

### 討論模式介面

- **識別碼與名稱**：`ask`（提問）、`consensus`（共識討論）。
- **使用哪些設定**：提問只用參與者與發言順序；共識討論另外使用主持人、共識裁定方式、輪數上限。設定面板依此顯示欄位。
- **本輪指示**：給定目前討論狀態，回傳這一輪要附加給每個參與者的指示（例如第 2 輪起「請對以下共識草案表態，最後一行寫 STANCE」）。
- **輪結束後的決定**：回傳以下其中一種，由引擎執行：
  - 「繼續下一輪」
  - 「做一次額外呼叫」（指定參與者與用途，例如主持人寫草案、寫最終結果、寫分歧整理），完成後再問一次
  - 「結束」（附結束原因與結果）
- **提問**：第 1 輪結束即結束，原因為 `completed`，結果為所有發言。
- **共識討論**：
  - 每輪結束後請主持人寫共識草案（額外呼叫）。
  - 第 2 輪起，交給共識裁定方式判斷。
  - 到達輪數上限仍未共識：請主持人寫「各參與者最終立場 + 仍有分歧的重點」，結束原因為 `no_consensus`。
  - 主持人失敗或被移出時，由參與者清單中下一個仍在場者接手。
- **由提問轉換**：共識討論可以帶入一場已結束的提問，把它的問題與發言當作第 1 輪，從第 1 輪結束後的草案開始。

### 共識裁定方式介面

- **識別碼**：`stance_vote`（方式 A）、`jev`（方式 B）。
- **可用性**：方式 B 在 `.env` 沒有 TypeSafe 金鑰時不可用（附原因）。
- **評估**：輪結束（且草案已產生）後呼叫，回傳：
  - 「未達成」（附給前端顯示的細節）
  - 「需要反問確認」（附要問每個參與者的問題）
  - 「已達成」（附共識結果的來源）
- **處理反問結果**：引擎把反問結果交回，回傳「已達成」或「未達成」（未達成時附上不同意者的理由，帶進下一輪）。
- **方式 A**：本輪所有在場參與者的表態都是 AGREE（針對同一份草案）→ 已達成，結果為該草案。
- **方式 B**：第 2 輪起，把整場討論交給 Jev 問「是否已取得共識」；機率 ≥ 門檻（預設 0.8）→ 需要反問確認；全員同意 → 請主持人寫最終共識結果 → 已達成；有人不同意 → 未達成並附理由。
- **表態格式**：發言最後一行必須是 `STANCE: AGREE` 或 `STANCE: DISAGREE`；解析不到視為不同意，下一輪的指示會提醒該參與者格式。

### 發言順序介面

- **識別碼**：`parallel`（同時）、`sequential`（依序）。
- **排程**：給定在場參與者清單與輪次，回傳「批次」的有序清單。引擎依序執行批次；同一批次內的發言平行執行，只看得到之前批次與之前輪次的發言。
- **同時**：一個批次包含所有參與者。第一版實作這個。
- **依序**：每人一個批次，第一位發言者每輪輪換（上一輪第一位，這一輪排最後）。第一版只定介面、不實作。

### 系統提示（所有參與者共用）

由 Prompt Builder 組成，包含：你正在和哪些參與者（顯示名稱）討論、用與題目相同的語言回答、引用網路資料時附網址、本輪的指示（來自討論模式）、表態格式（需要時）。人設欄位第一版不放入。

### HTTP API

- **取得參與者清單**：每個參與者的 id、顯示名稱、Adapter、模型、頭像、能力（web_access、streaming）、可用性與原因。
- **取得選項與預設值**：可用的討論模式、共識裁定方式（含可用性）、發言順序，以及設定檔中的預設設定。
- **取得討論列表**：id、問題、討論模式、開始時間、結束原因。
- **取得單一討論**：完整的討論紀錄 JSON。
- **頭像與前端靜態檔**。

### WebSocket 訊息

每場討論一條 WebSocket 連線。所有訊息都是 JSON，帶有 `type`；伺服器送出的訊息另帶 `discussion_id` 與遞增的 `seq`。

前端 → 後端：

| type | 欄位 | 意義 |
|---|---|---|
| `start` | `question`、`settings`（討論模式、參與者 id 清單、共識裁定方式、主持人 id、發言順序、輪數上限、逾時秒數、Jev 門檻）、`from_discussion_id`（可選，提問轉共識討論時使用） | 開始一場討論；設定此後鎖定 |
| `interject` | `text` | 使用者插話，從下一輪生效 |
| `stop` | — | 立即結束討論 |

後端 → 前端：

| type | 欄位 | 意義 |
|---|---|---|
| `discussion_started` | `settings`（完整快照）、`participants`（快照） | 討論已開始 |
| `round_started` | `round` | 某輪開始 |
| `turn_started` | `round`、`participant_id` | 某參與者開始發言 |
| `turn_delta` | `round`、`participant_id`、`text` | 串流的新文字片段（附加到既有內容後） |
| `turn_completed` | `round`、`participant_id`、`text`（完整）、`stance`（AGREE / DISAGREE / null） | 發言完成 |
| `turn_failed` | `round`、`participant_id`、`reason`、`kind` | 發言失敗 |
| `participant_removed` | `participant_id`、`reason` | 參與者被移出討論 |
| `moderator_changed` | `participant_id` | 主持人改由他人接手 |
| `draft_created` | `round`、`text` | 主持人寫好本輪共識草案 |
| `judge_result` | `round`、`judge`、`outcome`（not_reached / confirm / reached）、`detail`（方式 A：各參與者表態；方式 B：Jev 機率） | 共識裁定結果 |
| `confirmation_result` | `round`、`answers`（每個參與者：同意與否、理由） | 方式 B 反問的結果 |
| `interjection_queued` | `text`、`applies_to_round` | 插話已排入 |
| `round_completed` | `round` | 某輪結束（已存檔） |
| `discussion_finished` | `outcome`（completed / consensus / no_consensus / stopped / insufficient_participants / error）、`result`（共識結果，或最終立場與分歧點，或提問的所有發言） | 討論結束 |
| `error` | `message` | 無法處理的錯誤（例如設定不合法） |

### participants.toml

- **`[defaults]`**：`mode`、`judge`、`speaking_order`、`moderator`（參與者 id，省略時為清單第一個）、`max_rounds`（預設 15）、`turn_timeout_seconds`（預設 300）、`jev_threshold`（預設 0.8）。
- **`[[participant]]`**（可多個）：
  - `id`：唯一識別碼，討論紀錄中以此指稱參與者。
  - `display_name`：顯示名稱，也是其他參與者在討論中看到的名字。
  - `adapter`：Adapter 識別碼。
  - `model`：可選，省略時用 Adapter 預設。
  - `avatar`：可選，省略時用該 Adapter 的預設頭像。
  - `enabled`：可選，預設 true；false 時不出現在選單。
  - `persona`：保留欄位，第一版讀到時忽略並在日誌提示。
  - `options`：可選，Adapter 專屬選項（例如 Fake Adapter 的腳本、Ollama 的位址）。
- 載入時驗證：id 不重複、Adapter 存在、預設主持人存在；錯誤時啟動失敗並指出哪一行。
- 只能編輯檔案，第一版不提供介面編輯。

### .env

- TypeSafe 金鑰。只有後端讀取，不送到前端；必須被 git 忽略。提供 `.env.example`。

### 討論紀錄 JSON

每場討論一個檔案，存在本機資料夾，每輪結束與討論結束時覆寫。

| 欄位 | 意義 |
|---|---|
| `schema_version` | 紀錄格式版本，從 1 開始 |
| `id` | 討論 id |
| `question` | 使用者的問題 |
| `created_at` / `finished_at` | 開始 / 結束時間 |
| `settings` | 開始時鎖定的設定完整快照（同 `start` 的 settings） |
| `participants` | 參與者快照（id、顯示名稱、Adapter、模型、能力），避免之後改設定檔影響舊紀錄 |
| `derived_from` | 由哪場提問轉換而來（可為 null） |
| `rounds` | 每輪：`number`；`turns`（每個：`participant_id`、`status` ok / failed / timeout、`text`、`stance`、`started_at`、`ended_at`、`error`）；`draft`；`judge`（方式、結果、細節）；`confirmations` |
| `interjections` | 每個：`text`、`at`、`applies_to_round` |
| `removed_participants` | 每個：`participant_id`、`round`、`reason` |
| `moderator_changes` | 每個：`round`、`participant_id` |
| `outcome` | 同 `discussion_finished` 的 outcome；進行中為 null |
| `result` | 同 `discussion_finished` 的 result |

### 失敗與控制規則

- 每個發言有逾時（預設 300 秒）；逾時視為失敗。
- 參與者連續 2 輪失敗即移出；在場參與者少於 2 個時以 `insufficient_participants` 結束。
- 插話放入佇列，於下一輪的 prompt 中出現。
- 停止：取消所有進行中的發言（結束子行程），存檔，以 `stopped` 結束。

## Testing Decisions

### 好的測試

只測外部行為：送進 WebSocket / HTTP 的輸入、收到的訊息序列、存下來的討論紀錄。不測內部類別、方法呼叫順序或私有狀態，讓討論模式、共識裁定方式、發言順序等內部結構可以自由重構。

### 測試接縫（共 4 個）

1. **後端 HTTP / WebSocket API（主接縫）**：用 FastAPI 的測試 client，參與者全部用 Fake Adapter，Jev 用回傳固定機率的假 client。涵蓋：提問、提問轉共識討論、共識討論方式 A 與 B（含反問有人不同意）、輪數上限、表態解析失敗、插話生效時機、停止、發言失敗、連續失敗移出、參與者不足結束、主持人接手、設定驗證錯誤、討論紀錄內容與每輪存檔、歷史列表。討論模式、共識裁定方式、發言順序不另外寫單元測試。
2. **每個真實 Adapter 對接它的 CLI**：
   - canary 隔離測試：工作資料夾外放一個內容隨機的檔案，要求參與者盡力讀取，輸出中不得出現該內容。
   - smoke 測試：問一個簡短問題，能收到回覆並解析表態。
   - 會呼叫真實 AI、慢且花額度，以標記區隔，只在手動要求與 CLI 升級後執行。沒安裝的 CLI 自動略過。
3. **Jev client**：主接縫中用假 client；另有一個呼叫真實 TypeSafe API 的測試，只在設定了金鑰時執行。
4. **前端 E2E**：Playwright 對真實後端（Fake Adapter）操作瀏覽器。涵蓋：設定面板與預設值、多參與者並排串流顯示、插話、停止、共識結果顯示、未共識結果顯示、失敗與移出提示、歷史清單唯讀檢視、無上網標示、方式 B 無金鑰時不可選。前端元件不另寫單元測試。

### Prior art

專案目前沒有程式碼，沒有既有測試可參考。Canary 測試的做法來自 grilling 階段的手動實測（見 ADR 0002）。

## Out of Scope

- 提問、共識討論以外的討論模式（吵架、法庭、爭議事件討論、悠閒聊天）。
- 依序發言的實作（只定介面）。
- 人設（只保留設定欄位）與討論模式指派的角色。
- 匿名化參與者名稱。
- 繼續已結束的舊討論（歷史只能唯讀檢視；提問轉共識討論除外）。
- 討論中加入或移除參與者（失敗自動移出除外）。
- 在介面上編輯 `participants.toml`。
- 桌面 App 打包（Tauri / Electron）。
- macOS / Linux 的測試與保證。
- 帳號系統、多人共用、雲端同步。
- 管理各 AI 的 API 金鑰與計費（TypeSafe 金鑰除外）。
- 語音、圖片輸入。
- 使用 CLI 的 resume 節省 token。
- 驗證參與者附上的網址是否真實。
- 匯出討論紀錄（Markdown 等）。

## Further Notes

### 待確認的小決策

以下是撰寫 spec 時補上的合理預設，grilling 時沒有明確討論，實作前可再調整：

- 主持人失敗或被移出時，由參與者清單中下一個仍在場者接手。
- 未達成共識時的「最終立場與分歧點」由主持人額外呼叫一次撰寫。
- 討論紀錄每輪結束就存檔。

### Gemini CLI

本機尚未安裝。實作 Gemini Adapter 時先經使用者同意安裝，再找出隔離參數並通過 canary 測試。

### 素材規格

App icon、Favicon 與 `fake`、`default` 頭像由 Codex（`codex-imagegen`）產生；`claude`、`codex`、`gemini`、`ollama` 四張 Adapter 頭像改用官方產品 logo（來源：`simple-icons` 與 `@lobehub/icons-static-svg` 套件，見下方「Adapter 頭像例外」）。素材不走 TDD；程式端先用佔位圖，依檔名與尺寸開發，不必等素材完成。驗收需要使用者目視確認。

**風格指南**

- 原創風格：扁平、幾何、簡潔，圓角，柔和但可辨識的配色。
- App icon、Favicon 與 `fake`、`default` 頭像：**不使用、不模仿任何公司或產品的 logo、商標、吉祥物或品牌配色組合**（包括 Anthropic、OpenAI、Google、Ollama 等），也不放任何文字或字母。
- **Adapter 頭像例外**（使用者決定，2026-10-20）：`claude`、`codex`、`gemini`、`ollama` 四張頭像使用該產品的官方 logo 與官方品牌色，`claude`、`gemini`、`ollama` 來源為 `simple-icons` 套件（SVG 與 hex），`codex` 來源為 `@lobehub/icons-static-svg` 1.95.1（MIT）的 Codex 圖示 `codex.svg`，圓形填色用同套件 `codex-color.svg` 的官方漸層；做法為品牌色圓形（約 84% 直徑）內置白色 logo，品牌色過深或過淺時改用淺色圓形配品牌色 logo。僅限本機自用；公開或散布本專案前需依各家品牌規範重新檢視。
- 頭像之間風格一致（同樣的線條粗細、圓角、構圖比例），以不同主色與不同抽象圖形區分。
- 淺色與深色背景上都要清楚可辨。

**素材清單**

| 素材 | 說明 | 尺寸 | 格式 | 檔名與位置 |
|---|---|---|---|---|
| App icon（母檔） | 代表「多個聲音在廣場聚集討論」的抽象圖形 | 1024×1024 | PNG，透明背景 | `assets/brand/app-icon.png` |
| Favicon | 由母檔縮小，需在 32px 下仍可辨識 | 32×32、16×16 | PNG | `assets/brand/favicon-32.png`、`assets/brand/favicon-16.png` |
| 頭像：claude | `claude` Adapter 的預設頭像（官方 logo，來源 `simple-icons`；僅限本機自用；公開或散布本專案前需依各家品牌規範重新檢視。） | 256×256 | PNG，透明背景，主體置中、可裁成圓形 | `assets/avatars/claude.png` |
| 頭像：codex | `codex` Adapter 的預設頭像（官方 logo，來源 `@lobehub/icons-static-svg` 1.95.1 的 `codex.svg`；僅限本機自用；公開或散布本專案前需依各家品牌規範重新檢視。） | 同上 | 同上 | `assets/avatars/codex.png` |
| 頭像：gemini | `gemini` Adapter 的預設頭像（官方 logo，來源 `simple-icons`；僅限本機自用；公開或散布本專案前需依各家品牌規範重新檢視。） | 同上 | 同上 | `assets/avatars/gemini.png` |
| 頭像：ollama | `ollama` Adapter 的預設頭像（官方 logo，來源 `simple-icons`；僅限本機自用；公開或散布本專案前需依各家品牌規範重新檢視。） | 同上 | 同上 | `assets/avatars/ollama.png` |
| 頭像：fake | Fake Adapter 的頭像（開發用，可明顯看出是測試用） | 同上 | 同上 | `assets/avatars/fake.png` |
| 頭像：default | 未知 Adapter 或缺圖時的備用頭像 | 同上 | 同上 | `assets/avatars/default.png` |

桌面 App 打包時需要的其他尺寸，之後由 App icon 母檔產生，不在本次範圍。
