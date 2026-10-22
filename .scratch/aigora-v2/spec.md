# Spec: aigora-v2

Status: ready-for-agent

用語依 `GLOSSARY.md`；原始想法見 `docs/IDEA-v2.md`。未提到的行為一律沿用 `.scratch/aigora-v1/spec.md` 與 `.scratch/ui-redesign/spec.md`；本 spec 只寫 v2 的變更。現有程式的架構說明在 `docs/architecture/`。

## Problem Statement

v1 的參與者在同一輪裡同時發言，彼此只看得到上一輪的內容，比較像「各自交報告」，沒辦法直接回應剛剛那個人說的話。除了提問和共識討論，我也想看 AI 們在沒有任務時自由聊天會聊出什麼。我還想做一個實驗：每個參與者看得到的之前內容多寡（上下文上限）不同時，它們聊出來的內容會不會改變。

另外，v1 的人設只保留了設定欄位，沒有真的用上。設定也分散：模型在參與者表格每一列，主持人在右欄；提問結束後按「開始共識討論」，會直接用預設的主持人、共識裁定方式和輪數上限開始，沒有機會選。

## Solution

- **依序發言**：提問與共識討論都能選「依序」。同一輪一次只有一人發言，後面的人看得到同一輪前面的人剛說的話。共識討論從第 2 輪起，由主持人在寫共識草案時一併排定下一輪的發言順序。
- **自由聊天**：新的討論模式。主題可以不給；參與者依參與者清單順序輪流接話，不表態、不追求共識，到輪數上限（預設 100）結束，最後由主持人寫一份摘要。
- **上下文上限**：每個參與者可以各自設定。超過時從最舊的整則開始遺忘，不做壓縮。參與者知道自己的上限與目前用量；畫面上每個發言標示用量，點一下就能看出它當時遺忘了哪些內容。
- **人設**：寫在 `participants.toml` 當預設值，開始前可以改，放進該參與者自己的系統提示。
- **設定面板**：所有設定在同一個面板一次設完。點開某個參與者，跳出它的設定視窗：模型、人設、上下文上限、設為主持人。提問轉共識討論改成回到設定面板，問題、參與者與模型沿用提問，其餘設定都可以改。

## User Stories

### 依序發言

1. As a 使用者, I want to 在提問與共識討論選擇「依序」發言順序, so that 參與者能直接回應同一輪前面的人。
2. As a 使用者, I want to 依序發言時，後發言的參與者看得到同一輪前面所有人剛完成的發言, so that 討論更像真的交談。
3. As a 使用者, I want to 依序發言時一輪仍然是每個在場參與者各說一次, so that 輪數上限、失敗計數、表態的意義都和 v1 一樣。
4. As a 使用者, I want to 提問選依序時依參與者清單順序發言, so that 順序可以預期。
5. As a 使用者, I want to 共識討論選依序時，第 1 輪依參與者清單順序，之後由主持人在寫共識草案時排定下一輪順序, so that 主持人可以安排誰先回應分歧。
6. As a 使用者, I want to 主持人排順序不需要額外呼叫, so that 不多花額度。
7. As a 使用者, I want to 主持人排定的順序不合法或解析不到時，自動改用參與者清單順序並標示, so that 討論不會卡住，我也知道發生了什麼。
8. As a 使用者, I want to 在草案下方看到「下一輪順序：A → B → C」, so that 我知道接下來誰先說。
9. As a 使用者, I want to 主持人寫的排序那一行不出現在草案內文裡, so that 其他參與者不會把它當作草案內容表態。
10. As a 使用者, I want to 依序發言時插話從下一個發言開始生效, so that 下一位發言者就能回應我的補充。
11. As a 使用者, I want to 插話佇列顯示「第 N 輪第 M 位起生效」, so that 我知道插話何時被看到。
12. As a 使用者, I want to 同時發言時插話仍然從下一輪生效, so that v1 的行為不變。
13. As a 使用者, I want to 依序發言時串流仍照常顯示，一次只有一人在回覆, so that 我能跟著讀。
14. As a 使用者, I want to 依序發言時同一輪的發言依發言順序由上往下排列, so that 讀起來像一串聊天紀錄。
15. As a 使用者, I want to 同時發言時發言卡片仍然左右並排, so that 方便比較答案。
16. As a 使用者, I want to 依序發言時某人失敗或逾時，下一位照常發言並看得到「（沒有回覆）」, so that 一個 AI 掛掉不會拖垮整輪。
17. As a 使用者, I want to 依序發言時按停止會立即結束正在發言的人，其後的人不再發言, so that 停止仍然是立即止損。

### 自由聊天

18. As a 使用者, I want to 選擇「自由聊天」討論模式, so that 我可以看 AI 們不帶任務地聊天。
19. As a 使用者, I want to 自由聊天時主題可以不填, so that 參與者可以自己開話題。
20. As a 使用者, I want to 不填主題時由第一位發言者自己開啟話題, so that 聊天有個開頭。
21. As a 使用者, I want to 自由聊天固定依參與者清單順序輪流（A→B→C→A…）, so that 每個人都有一樣多的發言機會。
22. As a 使用者, I want to 自由聊天不表態、不寫共識草案、不判斷共識, so that 不花額度在不需要的事情上。
23. As a 使用者, I want to 自由聊天的發言像聊天一樣自然簡短，直接回應前面的人, so that 不會變成一連串長篇報告。
24. As a 使用者, I want to 自由聊天預設最多 100 輪，可以調整, so that 聊得夠久，又不會無止盡消耗額度。
25. As a 使用者, I want to 切換到自由聊天時，輪數上限自動帶入自由聊天的預設值, so that 不用每次手動改。
26. As a 使用者, I want to 自由聊天結束時由主持人寫一份聊天摘要，摘要時看得到完整紀錄, so that 我不用讀完 100 輪也知道聊了什麼。
27. As a 使用者, I want to 自由聊天的摘要顯示在舞台最上方, so that 一打開就看得到。
28. As a 使用者, I want to 我按停止時自由聊天立即結束、不寫摘要, so that 停止仍然是立即止損。
29. As a 使用者, I want to 自由聊天因參與者不足而結束時，仍在場的主持人寫摘要，主持人不在了就不寫, so that 盡量留下有用的整理。
30. As a 使用者, I want to 沒有摘要時看到結束原因, so that 我知道為什麼沒有摘要。
31. As a 使用者, I want to 自由聊天中也可以插話, so that 我可以把話題帶往別的方向。
32. As a 使用者, I want to 自由聊天中參與者失敗、移出、主持人接手的規則與 v1 相同, so that 不用學新規則。
33. As a 使用者, I want to 自由聊天的檢視器不顯示表態追蹤, so that 畫面不會出現沒有意義的區塊。
34. As a 使用者, I want to 歷史清單中沒有主題的自由聊天顯示「（無主題）」, so that 我分得出是哪一場。

### 上下文上限

35. As a 使用者, I want to 為每個參與者各自設定上下文上限, so that 我可以讓 A 看得到很多、B 只看得到一點。
36. As a 使用者, I want to 不設上下文上限時行為和 v1 完全相同, so that 不做實驗時不受影響。
37. As a 使用者, I want to 上下文上限最小 100 tokens, so that 不會設出沒有意義的值。
38. As a 使用者, I want to 上下文上限在所有討論模式都能用, so that 共識討論也能做實驗。
39. As a 使用者, I want to 上下文上限只計算 AIgora 送給參與者的內容, so that 數字和我設定的意義一致，不受各 CLI 自己的提示影響。
40. As a 使用者, I want to 所有參與者統一用 Claude 的 token 算法計算, so that 不同 AI 之間的數字可以比較。
41. As a 使用者, I want to 在 `.env` 有 `AIGORA_ANTHROPIC_API_KEY` 時用 Anthropic 的 token 計數 API，沒有時用本機估算, so that 有金鑰時數字更準，沒有金鑰也能用。
42. As a 使用者, I want to 在設定面板看到目前用的是哪一種計數方式, so that 我知道數字的精確程度。
43. As a 使用者, I want to token 計數 API 某次失敗時，那一次改用本機估算並記錄下來, so that 討論不會因此中斷。
44. As a 使用者, I want to 超過上限時從最舊的整則開始遺忘，不做摘要或壓縮, so that 實驗條件單純。
45. As a 使用者, I want to 系統提示、人設、本次指示與最新一份共識草案一定保留, so that 參與者知道自己是誰、要做什麼、要對哪份草案表態。
46. As a 使用者, I want to 之前的發言、較舊的草案、插話都可以被遺忘, so that 遺忘的規則一致。
47. As a 使用者, I want to 開始前選擇「保留問題／主題」或「問題／主題也會被遺忘」（預設保留）, so that 我可以實驗連題目都忘掉會怎樣。
48. As a 使用者, I want to 一定保留的部分本身就超過上限時，仍然送出並標示「已超過上限」, so that 討論不會中斷，我也知道這次超過了。
49. As a 使用者, I want to 主持人寫草案、最終結果、分歧整理以及方式 B 的反問確認也套用該參與者的上下文上限, so that 同一個參與者的條件前後一致。
50. As a 使用者, I want to 自由聊天的摘要不受上下文上限限制, so that 摘要涵蓋整場聊天。
51. As a 使用者, I want to 參與者每次發言時都被告知「上下文上限多少、目前用了多少」，但不被告知遺忘了什麼, so that 它知道自己的限制，實驗又不會被額外提示干擾。
52. As a 使用者, I want to 上下文上限不幫回覆預留空間、回覆長度不限, so that 上限的意義就是「看得到多少」。
53. As a 使用者, I want to 每個發言卡片有「上下文 7,200 / 8,000 · 已遺忘 12 則」標籤，超過上限時顯示紅色「已超過上限」, so that 一眼看出它當時的狀態。
54. As a 使用者, I want to 點標籤進入對照模式，這則發言之前它看不到的內容全部變淡，再點一次恢復, so that 我能對照「它說這句話時忘了什麼」。
55. As a 使用者, I want to 唯讀紀錄也能看到標籤和對照模式, so that 事後也能分析。
56. As a 使用者, I want to 有設上下文上限時，檢視器顯示每個參與者目前的上下文用量, so that 不用逐張卡片看。
57. As a 使用者, I want to 主持人的額外呼叫也顯示上下文標籤, so that 我知道它寫草案時看得到什麼。
58. As a 使用者, I want to Ollama 參與者真的看得到我設定的上下文上限那麼多內容, so that Ollama 不會自己默默截斷，污染實驗。

### 人設

59. As a 使用者, I want to 在 `participants.toml` 為參與者寫人設當作預設值, so that 常用的人設不用每次重打。
60. As a 使用者, I want to 人設可以多行、最多 2,000 字, so that 能寫出完整的個性設定，又不會太長。
61. As a 使用者, I want to 開始前在參與者設定視窗修改這場的人設，開始後鎖定, so that 每場可以不同，而紀錄和實際行為一致。
62. As a 使用者, I want to 人設只放進該參與者自己的系統提示，其他參與者看不到原文, so that 人設的效果來自它的言行，不是被別人讀到。
63. As a 使用者, I want to 人設不顯示在發言卡片上，只出現在設定視窗、檢視器的鎖定設定與唯讀紀錄, so that 畫面不會太雜。
64. As a 使用者, I want to 臨時參與者也可以設定人設, so that 用起來和設定檔參與者一樣。

### 設定面板與參與者設定

65. As a 使用者, I want to 所有設定都在同一個設定面板設完就開始, so that 不用在不同地方找設定。
66. As a 使用者, I want to 點開參與者跳出它的設定視窗，設定模型、人設、上下文上限、設為主持人, so that 每個參與者自己的設定集中在一處。
67. As a 使用者, I want to 參與者表格每一列只顯示摘要（模型、是否有人設、上下文上限、主持人標記）, so that 表格保持簡潔。
68. As a 使用者, I want to 同一場只能有一位主持人，只在需要主持人的討論模式（共識討論、自由聊天）出現「設為主持人」, so that 不會出現矛盾的設定。
69. As a 使用者, I want to 主持人預設為設定檔指定的參與者（省略時為第一個）, so that 常用設定不用每次選。
70. As a 使用者, I want to 「新增參與者」保留，新增後一樣能點開設定, so that 臨時參與者和設定檔參與者用起來一樣。
71. As a 使用者, I want to 參與者與模型都有預設值、開始前都能調整, so that 每場可以有不同組合。
72. As a 使用者, I want to 開始後所有設定鎖定, so that 討論紀錄與實際行為一致。
73. As a 使用者, I want to 自由聊天時問題輸入框改成「主題（可不填）」, so that 我知道可以留白。
74. As a 使用者, I want to 選自由聊天時不顯示發言順序、共識裁定方式等用不到的設定, so that 面板只顯示有意義的欄位。

### 提問轉共識討論

75. As a 使用者, I want to 提問結束後按「開始共識討論」回到設定面板, so that 我可以先選主持人、共識裁定方式、輪數上限等再開始。
76. As a 使用者, I want to 轉換時問題、參與者清單與各自的模型鎖定，沿用提問, so that 提問的發言可以直接當作第 1 輪。
77. As a 使用者, I want to 轉換時人設、上下文上限、主持人與其他共識討論設定都可以改，從第 2 輪開始生效, so that 共識討論可以照我的需要設定。
78. As a 使用者, I want to 轉換時面板清楚標示這是由哪場提問轉換而來，並可以取消回到原本的提問結果, so that 我不會搞混正在設定的是哪一場。

### 紀錄與相容

79. As a 使用者, I want to 討論紀錄存下每個發言的上下文用量、遺忘範圍、計數方式，以及每輪的發言順序, so that 事後可以分析實驗。
80. As a 使用者, I want to v1 與 ui-redesign 時期的舊紀錄仍然能以唯讀方式打開, so that 歷史不會遺失。
81. As a 使用者, I want to 唯讀紀錄的版面（依序由上往下、同時左右並排、標籤、對照模式、摘要）和討論中畫面一致, so that 回顧時不用重新適應。

### 開發者

82. As a 開發者, I want to 依序發言、自由聊天都透過既有的發言順序與討論模式介面加入, so that 引擎不用為了某個模式寫特例。
83. As a 開發者, I want to 所有新功能都能用 Fake Adapter 自動測試，不花 AI 額度, so that 開發與 CI 不受額度限制。
84. As a 開發者, I want to 本機估算是確定的（相同文字永遠算出相同 token 數）, so that 測試可以斷言精確的用量與遺忘範圍。
85. As a 開發者, I want to `AIGORA_ANTHROPIC_API_KEY` 只有後端讀取、不送到前端、不傳給任何 CLI 子行程, so that 金鑰不外洩，也不會讓 Claude CLI 改走 API 計費。

## Implementation Decisions

### 模組

| 模組 | v2 變更 |
|---|---|
| 發言順序 | 實作「依序」：每人一個批次，順序依引擎傳入的清單。取代 v1 介面註解中「每輪輪換第一位」的規則 |
| 討論模式 | 新增「排定本輪順序」能力；共識討論解析主持人排的順序；新增自由聊天模式 |
| 討論引擎 | 每輪向討論模式取得發言順序；插話可以在一輪中間生效；每次呼叫前計算上下文與遺忘；記錄順序與上下文用量 |
| Prompt Builder | 改成產生「片段」清單（系統提示、人設、問題／主題、各則歷史、插話、指示），由上下文預算模組決定哪些送出；加入人設與上下文用量提示 |
| 上下文預算（新） | 輸入片段清單、上限、保留規則與計數器，輸出要送的片段、用量、是否超過、遺忘範圍 |
| Token 計數器（新） | 介面：計算一段文字的 token 數。兩個實作：Anthropic 計數 API、本機估算 |
| 設定載入 | 人設正式啟用；新增參與者 `context_limit`、`[defaults] chat_max_rounds`、`[defaults] keep_question` |
| 設定解析 | 解析人設、上下文上限、問題／主題保留方式；自由聊天的問題可以為空，發言順序固定為依序 |
| 提問轉共識討論 | 參與者、模型、臨時參與者一律取自原提問；請求中的人設、上下文上限、主持人與其他設定照常套用 |
| Ollama Adapter | 依這次呼叫的上下文上限設定 `num_ctx` |
| 前端 | 參與者設定視窗、自由聊天、依序版面、上下文標籤與對照模式、提問轉共識討論的設定流程 |

### 發言順序

- `sequential`（依序）：給定參與者清單（已排好順序）與輪次，回傳每人一個批次。同一批次的定義不變：只看得到之前批次與之前輪的發言。所以依序時，後發言者看得到同一輪前面所有人已完成的發言。
- 引擎每輪開始時，先向討論模式取得「本輪順序」（在場參與者 id 的排列）；討論模式沒有指定時用參與者清單順序（排除已移出者），再交給發言順序排成批次。
- 各討論模式的本輪順序：
  - 提問：清單順序。
  - 共識討論：第 1 輪用清單順序；之後，若發言順序是依序且上一輪草案解析出合法的順序，就用該順序，否則用清單順序。
  - 自由聊天：清單順序（每輪 A→B→C）。自由聊天的發言順序固定為依序，設定面板不顯示這個欄位，`start` 送來的值被忽略、快照中記為 `sequential`。
- 依序發言時失敗或逾時的發言照 v1 記錄；下一位照常發言，在歷史中看到該則為「（沒有回覆：原因）」。

### 主持人排定順序

- 只有共識討論且發言順序為依序時，寫草案的指示才要求主持人在草案**最後一行**寫：`ORDER: 顯示名稱1, 顯示名稱2, ...`，列出所有在場參與者（含主持人自己）各一次。用顯示名稱，因為參與者在 prompt 中只看得到顯示名稱，而顯示名稱在同一場討論中不重複（ui-redesign 的規則）。
- 解析：去掉前後空白、以半形或全形逗號分隔、比對時不分大小寫。必須剛好包含所有在場參與者各一次，否則不合法。
- 不論合法與否，`ORDER:` 這一行都從草案內文移除，之後才存成草案、送給其他參與者。
- 草案是在第 N 輪之後寫的，它排的是第 N+1 輪。若第 N+1 輪開始前有人被移出，從排好的順序中刪去該人，其餘順序不變。
- 主持人失敗、由他人接手重寫草案時，以最後成功的那份草案為準。

### 自由聊天模式

- 識別碼 `chat`，名稱「自由聊天」。使用的設定：參與者、主持人、輪數上限、逾時、各參與者的人設與上下文上限、問題／主題保留方式。
- `start` 的 `question` 在自由聊天時可以是空字串（代表沒有主題）；其他討論模式仍至少 1 個字。
- 本輪指示（每一則都有）：像聊天一樣自然、簡短（約 1–3 段），直接回應前面的人，不要寫成報告；沒有主題而且自己是整場第一個發言時，自己開一個話題。不表態。
- 每輪結束：未到輪數上限就繼續；到上限就請主持人寫摘要（額外呼叫，用途 `chat_summary`），完成後以 `completed` 結束，結果為摘要。
- 摘要的 prompt 包含完整紀錄，**不套用**主持人的上下文上限；指示要求整理聊了哪些話題、各參與者的主要觀點與有趣的轉折。
- 主持人寫摘要失敗：依 v1 的主持人接手規則交給下一位仍在場者重試，每人一次；全部失敗則以 `completed` 結束、沒有摘要，`reason` 說明原因。
- 停止：與 v1 相同，立即結束，不寫摘要。
- 參與者不足 2 個：主持人仍在場就先寫摘要，再以 `insufficient_participants` 結束；主持人也已移出就直接結束、沒有摘要。
- 插話、失敗計數、移出、逾時都沿用引擎既有規則。

### 插話（依序發言）

- 同時發言：從下一輪生效（v1）。
- 依序發言：從**下一個尚未開始的發言**生效。若本輪還有人沒開始，生效位置是本輪下一位；若本輪最後一位正在發言或本輪已在額外呼叫階段，生效位置是下一輪第 1 位。
- 插話紀錄與 `interjection_queued` 新增 `applies_before_turn`：在該輪發言順序中的位置（從 1 開始），表示從第幾位發言者開始看得到；`null` 代表從該輪開始就看得到（同時發言，或依序時的第 1 位）。
- Prompt 中插話出現在歷史的對應位置（該輪第 M 位發言之前），不再只在輪的開頭。

### 上下文上限與遺忘

**片段**：Prompt Builder 把一次呼叫要送的內容組成有序片段，每段標示種類：

| 種類 | 一定保留 | 說明 |
|---|---|---|
| 系統提示 | 是 | 含參與者名單、語言、網址、本機檔案限制 |
| 人設 | 是 | 該參與者自己的人設（有的話） |
| 問題／主題 | 依設定 | 「保留問題／主題」時一定保留；否則視為最舊的歷史 |
| 歷史：發言、草案、插話 | 否 | 依時間由舊到新 |
| 最新一份共識草案 | 是 | 共識討論中，這次呼叫要表態或參考的那份 |
| 上下文用量提示 | 是 | 「你的上下文上限是 X tokens，這次送給你的內容約 Y tokens。」 |
| 本次指示 | 是 | 討論模式給的指示 |

**計算**：

1. 沒有設定上限：全部送出；仍計算 token 數並記錄用量（上限為 null）。
2. 有上限：先把所有片段都算進去；超過上限時，從最舊的可遺忘片段開始整則移除，直到總數不超過上限，或已經沒有可遺忘的片段。
3. 一定保留的部分本身就超過上限時：送出這些部分，其餘全部遺忘，標記 `over_limit = true`。
4. 用量提示裡的 Y 是最終要送的總數（包含提示這一行本身；先用估算值，誤差可以接受）。
5. 每次呼叫（一般發言與額外呼叫）都在開始前計算，只有自由聊天的摘要例外。

**遺忘範圍的表示**：因為遺忘一定是從最舊的開始連續移除，紀錄只需要存「最後一個被遺忘的歷史項目」：

- `ContextUsage`：`limit`（int 或 null）、`used`（int）、`counter`（`anthropic` / `estimate`）、`over_limit`（bool）、`question_forgotten`（bool）、`forgotten_count`（int，被遺忘的歷史項目數，不含問題／主題）、`forgotten_through`（`HistoryRef` 或 null）。
- `HistoryRef`：`kind`（`turn` / `draft` / `interjection`）、`round`、`participant_id`（turn 時）、`index`（interjection 時，為紀錄中 `interjections` 的索引）。
- 歷史項目的時間順序（前端用來還原「哪些變淡」）：依輪次；同一輪內，插話依 `applies_before_turn` 插在對應位置之前，發言依該輪的發言順序，草案在該輪最後。歷史中被一定保留的最新草案，即使在 `forgotten_through` 之前也不算遺忘。

**Token 計數器**：

- 介面：`count(text) -> int`，非同步。每段片段分開計算，以文字內容快取（發言內容不會變，所以每段只算一次），總數等於各段相加。
- Anthropic：`.env`（經 `backend_env()`）有 `AIGORA_ANTHROPIC_API_KEY` 時使用 Anthropic Messages 的 token 計數端點。這個端點不收費，模型用一個固定的 Claude 模型（常數，必要時可用環境變數 `AIGORA_TOKEN_COUNT_MODEL` 覆蓋）。某段計數失敗時，該段改用本機估算，該次呼叫的 `counter` 記為 `estimate`。
- 本機估算：不新增套件。CJK 字元（中日韓文字與全形標點）每字 1 token，其他字元每 4 個 1 token（無條件進位），兩者相加。結果是確定的。
- 金鑰只在後端讀取；不出現在任何 HTTP 回應或 WebSocket 訊息；建立 CLI 子行程時不傳入（`.env` 本來就不會載入行程環境；若行程環境裡有，Adapter 建子行程環境時要移除 `AIGORA_ANTHROPIC_API_KEY`）。
- `.env.example` 新增這個變數與說明。

**Ollama**：Ollama Adapter 在 `POST /api/generate` 的 `options.num_ctx` 設定為：這次呼叫的上下文上限加上回覆預留量（常數，例如 4096）；沒有上限時用 Adapter 的預設大值（常數，例如 32768）。發言請求因此需要帶上這次的上下文上限。

### 人設

- `participants.toml` 的 `persona` 正式啟用（字串，可多行，最多 2,000 字；超過時載入失敗並指出行號）。不再記錄「保留欄位」的日誌。
- 臨時參與者的人設預設沿用範本。
- 系統提示在參與者名單之後加入：「你的人設：<人設>。在整場討論中以這個人設發言。」（實際文字由實作決定，須與題目語言無關地清楚）。只有該參與者自己的 prompt 有。
- 自由聊天的摘要與共識討論的額外呼叫也帶主持人自己的人設。

### 設定（StartSettings / DiscussionSettings）

`StartSettings` 新增（全部可以省略；省略時與 v1 相同）：

- `personas`：參與者 id → 人設文字（空字串代表這場不用人設）；省略的參與者用設定檔或範本的預設值。
- `context_limits`：參與者 id → 上下文上限（整數，≥ 100）；`null` 或省略代表不限制（設定檔有 `context_limit` 時省略則用設定檔的值，明確送 `null` 代表不限制）。
- `keep_question`：布林，預設來自 `[defaults] keep_question`（預設 true）。

`DiscussionSettings`（鎖定的快照）新增 `personas`、`context_limits`、`keep_question`，存的是**解析後的實際值**（每個參與者都有項目）。`mode` 新增 `chat`。

驗證：人設長度、上下文上限 ≥ 100、指定的參與者 id 必須在這場討論中；錯誤以 `error` 訊息回傳（同 v1）。

輪數上限預設：自由聊天用 `[defaults] chat_max_rounds`（預設 100），其他討論模式用 `max_rounds`（預設 15）。

### 提問轉共識討論

- 前端：提問結束後按「開始共識討論」，回到設定頁並進入轉換狀態：討論模式固定為共識討論；問題、參與者清單與模型（含臨時參與者）唯讀，沿用該提問；其餘欄位可以改；頂部標示「由提問轉換：<問題>」；「取消」回到該提問的結果畫面。
- 後端：`start` 帶 `from_discussion_id` 時，問題、`participant_ids`、`models`、`extra_participants` 一律取自原提問（請求中這幾項被忽略）；`personas`、`context_limits`、`keep_question`、主持人、共識裁定方式、發言順序、輪數上限、逾時、Jev 門檻取自請求。
- 第 1 輪沿用提問的發言（含當時的上下文用量）；新的人設與上下文上限從第 2 輪開始生效。

### HTTP API

- `ParticipantInfo` 新增 `persona`（字串或 null）、`context_limit`（整數或 null），作為設定面板的預設值。
- `OptionsResponse`：
  - 討論模式清單新增 `chat`，各模式的 `uses_settings` 反映上述欄位。
  - 依序發言改為已實作。
  - 預設值新增 `chat_max_rounds`、`keep_question`。
  - 新增 `token_counter`：`anthropic` 或 `estimate`（只回傳種類，不回傳金鑰）。
- `DiscussionSummary` 不變；前端在問題為空時顯示「（無主題）」。

### WebSocket 訊息變更

| type | 變更 |
|---|---|
| `start` | `question` 在自由聊天時可以為空字串；settings 新增欄位（見上） |
| `discussion_started` | settings 快照含新欄位 |
| `round_started` | 新增 `order`：本輪發言順序（參與者 id 清單） |
| `turn_started` | 新增 `context`：`ContextUsage`（每個一般發言與額外呼叫都有；自由聊天摘要的 `limit` 為 null） |
| `draft_created` | 新增 `next_order`（清單或 null）與 `next_order_source`（`moderator` / `default` / null）；同時發言時兩者皆為 null |
| `interjection_queued` | 新增 `applies_before_turn` |
| `discussion_finished` | `result.kind` 新增 `chat_summary`（`text` 為摘要，可為 null） |

`turn_*` 的 `purpose` 新增 `chat_summary`。

### 討論紀錄 JSON

- `SCHEMA_VERSION = 3`。仍能讀取 schema 1、2 的紀錄（新欄位用預設值：沒有人設、沒有上下文上限、保留問題、`order` 由發言出現順序推得、`context` 為 null）。
- `settings`：新增 `personas`、`context_limits`、`keep_question`。
- `rounds[]`：新增 `order`（本輪發言順序）、`next_order`、`next_order_source`、`extra_calls`（每個額外呼叫：`purpose`、`participant_id`、`status`、`context`；不重複存全文，草案全文仍在 `draft`）。
- `rounds[].turns[]`：新增 `context`（`ContextUsage` 或 null）。
- `interjections[]`：新增 `applies_before_turn`。
- `result.kind` 可以是 `chat_summary`。

### participants.toml

- `[[participant]]` 新增 `context_limit`（可選，整數 ≥ 100）；`persona` 正式啟用（≤ 2,000 字）。
- `[defaults]` 新增 `chat_max_rounds`（預設 100）、`keep_question`（預設 true）；`mode` 可以是 `chat`；`speaking_order` 可以是 `sequential`。
- `participants.example.toml` 與 E2E 設定檔一併更新範例。

### 前端

- **設定頁**：
  - 討論模式分段控制新增「自由聊天」；選自由聊天時，問題輸入框的 label 改為「主題（可不填）」，允許空白送出。
  - 參與者表格每列：勾選、頭像與名稱、摘要（模型、「有人設」標記、上下文上限或「不限」、主持人 pill）、能力與可用性 pill，加上「設定」按鈕。原本每列的模型下拉選單移到設定視窗。
  - 參與者設定視窗（對話框，原生 `<dialog>` 或等效、可用鍵盤操作與 Esc 關閉）：模型（沿用 ui-redesign 的模型選擇元件與自行輸入規則）、人設（多行文字框、字數計數）、上下文上限（數字輸入，空白 = 不限）、「設為主持人」（只在討論模式需要主持人時顯示）。確定後套用、取消不變。
  - 右欄：主持人改為唯讀顯示（「主持人：Claude」，在設定視窗中更換），同時保留可存取名稱為「主持人」的控制項，讓既有 E2E 選擇器仍然有效（或依「刻意修改的測試」規則更新測試並記錄原因）；發言順序的「依序」可以選；新增「問題／主題」保留方式（radio：保留問題／主題、問題／主題也會被遺忘）；顯示 token 計數方式（「token 計數：Anthropic API」或「token 計數：本機估算」）。
  - 切換到自由聊天時，輪數上限帶入 `chat_max_rounds`；切回其他模式時帶回 `max_rounds`（使用者手動改過的值不覆蓋）。
  - 提問轉共識討論的轉換狀態（見上）。
- **討論中／唯讀紀錄**：
  - 發言順序為依序時，同一輪的發言卡片依 `order` 由上往下排列（寬度填滿舞台）；同時發言維持左右並排。
  - 發言卡片新增上下文標籤（有 `context` 時）：「上下文 7,200 / 8,000 · 已遺忘 12 則」，沒有上限時為「上下文 7,200」；`over_limit` 時為紅色「已超過上限」。額外呼叫（草案等）也有同樣的標籤。
  - 對照模式：點標籤後，依 `forgotten_through`、`question_forgotten` 與歷史順序規則，把這次呼叫看不到的內容（問題／主題區塊、發言卡片、草案、插話）加上淡化樣式；該標籤標示為「對照中」；再點一次或點其他標籤即切換。一次只有一個對照中的呼叫。
  - 草案下方顯示「下一輪順序：A → B → C」，`next_order_source = default` 時加「（主持人未指定，依清單順序）」。
  - 自由聊天：結果區塊顯示摘要（或結束原因）；檢視器隱藏表態追蹤；插話列可用。
  - 檢視器新增「上下文」區塊（有任何參與者設了上限時）：每個參與者最近一次呼叫的用量 / 上限與已遺忘則數。
  - 檢視器的「設定（已鎖定）」列出每個參與者的人設與上下文上限、問題／主題保留方式。
  - 插話佇列項目：依序時顯示「第 N 輪第 M 位起生效」，同時發言維持「第 N 輪起生效」。
- **歷史**：問題為空時顯示「（無主題）」；討論模式欄顯示「自由聊天」。
- 前端文字須通過 glossary 檢查（不使用「記憶」「窗口」「對話」等 _Avoid_ 詞）。

## Testing Decisions

### 好的測試

沿用 v1：只測外部行為，也就是送進 WebSocket / HTTP 的輸入、收到的訊息序列、存下來的討論紀錄，以及 Fake Adapter `echo_prompt` 回傳的「參與者實際收到的 prompt」。不測內部類別、片段資料結構或私有狀態；討論模式、發言順序、上下文預算、Prompt Builder 不另外寫單元測試。

### 測試接縫（沿用 v1 的 4 個，不新增）

1. **後端 HTTP / WebSocket API（主接縫）**：Fake Adapter 參與者；測試環境沒有 `AIGORA_ANTHROPIC_API_KEY`，所以計數器是確定的本機估算。涵蓋：
   - 依序發言：同一輪後發言者的 prompt 含前面的人本輪的發言、同時發言則不含；`round_started.order`；依序時失敗不影響下一位。
   - 主持人排順序：合法順序用於下一輪；不合法、缺人、重複、未知名稱時退回清單順序並標 `default`；`ORDER:` 行從草案移除；排定後有人被移出。
   - 插話：依序時從下一個發言生效（`applies_before_turn` 與 prompt 位置）；最後一位發言中插話時生效於下一輪第 1 位；同時發言維持下一輪。
   - 自由聊天：空主題、輪數上限結束並產生摘要、摘要 prompt 含完整紀錄（不受上限）、停止不寫摘要、參與者不足時主持人寫摘要／主持人已移出時不寫、摘要失敗由他人接手、預設輪數 100、發言順序固定依序。
   - 上下文上限：沒設時 prompt 與 v1 相同；從最舊整則遺忘；一定保留的片段；最新草案保留；保留與不保留問題；`over_limit`；額外呼叫套用、自由聊天摘要不套用；用量提示文字；`ContextUsage` 的數值與 `forgotten_through`；Anthropic 計數器失敗時改用估算（monkeypatch 假計數器，比照現有 Jev 的測法）。
   - 人設：只出現在自己的 prompt；預設值、請求覆蓋、空字串取消；長度驗證。
   - 設定：新欄位的驗證錯誤；`chat_max_rounds` / `keep_question` 預設；`/api/options` 的 `token_counter` 與 `chat` 模式；`/api/participants` 的 `persona`、`context_limit`。
   - 提問轉共識討論：參與者／模型取自原提問、人設與上下文上限取自請求並從第 2 輪生效。
   - 紀錄：schema 3 新欄位；舊的 schema 1、2 紀錄仍可讀取。
   - 契約：`test_ws_messages.py` 繼續比對 Python 與 TypeScript 的欄位。
2. **真實 Adapter 與外部服務**：
   - Anthropic token 計數 client：呼叫真實 API 的測試，標 `real_ai`，沒有金鑰時略過（比照 Jev client 測試）。
   - Ollama：在現有 Adapter 測試（`httpx.MockTransport`）中驗證 `num_ctx` 依上下文上限設定、沒有上限時用預設大值。
   - 既有的 canary 測試不變；Claude Adapter 建子行程環境時移除 `AIGORA_ANTHROPIC_API_KEY`，用現有的 fake CLI 驗證。
3. **Jev client**：不變。
4. **前端 E2E（Playwright，Fake Adapter）**：參與者設定視窗（模型、人設、上下文上限、設為主持人）、表格摘要、自由聊天（主題可空、輪數預設、摘要顯示、無表態追蹤）、依序版面由上往下、上下文標籤與對照模式（討論中與唯讀紀錄）、草案下方的下一輪順序、插話佇列「第 N 輪第 M 位起生效」、提問轉共識討論回到設定面板（鎖定欄位、可改欄位、取消）、歷史「（無主題）」、token 計數方式顯示。必要時在 `participants.e2e.toml` 新增 Fake 參與者（例如會寫 `ORDER:` 的草案腳本）。

### Prior art

- `test_ask.py`、`test_consensus.py`、`test_interject_and_stop.py`（`receive_until`）、`test_failure_handling.py`、`test_ask_to_consensus.py`、`test_history.py`：主接縫的寫法。
- `test_consensus_jev.py` 的 `env_file` / `fake_jev` fixture：外部服務 client 的替換方式，Anthropic 計數器比照辦理。
- `test_ollama_adapter.py`：`httpx.MockTransport`。
- `frontend/e2e/participant-models.spec.ts`、`ask-to-consensus.spec.ts`、`settings-panel.spec.ts`：設定頁與轉換流程的 E2E 寫法；Judge B UI 用 `page.routeWebSocket` 的做法可用於難以用 Fake 重現的畫面狀態。

## Out of Scope

- 吵架、法庭、爭議事件討論等其他討論模式，以及討論模式指派的角色。
- 超過上下文上限時的摘要或壓縮。
- 討論中加入、移除參與者或換模型（失敗自動移出除外）。
- 每次發言後由主持人點名下一位；依序發言時每輪輪換第一位的舊規則。
- 自由聊天以共識或 AI 自行宣告結束。
- 管理 Anthropic API 計費；`AIGORA_ANTHROPIC_API_KEY` 只用於免費的 token 計數，可以不提供。
- 讓參與者知道自己遺忘了什麼。
- 為回覆預留上下文空間或限制回覆長度。
- 在介面上編輯 `participants.toml`（人設、上下文上限的預設值仍只能改檔案）。
- 匯出討論紀錄、繼續已結束的討論（提問轉共識討論除外）。
- 其餘沿用 v1 與 ui-redesign 的 Out of Scope。

## Further Notes

### 撰寫 spec 時補上的預設（實作前可再調整）

- 摘要失敗時依主持人接手規則重試，每人一次。
- `ORDER:` 用顯示名稱、不分大小寫、半形或全形逗號皆可。
- 本機估算的換算方式（CJK 每字 1 token、其他每 4 字元 1 token）。
- Ollama `num_ctx` 的回覆預留量與無上限時的預設值。
- 用量提示的 Y 包含提示本身，誤差可接受。
- 提問轉共識討論的轉換狀態可以取消，回到原本的提問結果。

### 與既有文件的關係

- 實作時同步更新 `docs/architecture/discussion-engine.md`（依序、本輪順序、插話位置、上下文預算）、`contracts.md`（新欄位與 schema 3）、`adapters.md`（Ollama `num_ctx`、子行程環境移除金鑰）、`testing.md`（計數器的替換方式）。
- `AGENTS.md` 的 Backend env vars 新增 `AIGORA_ANTHROPIC_API_KEY`、`AIGORA_TOKEN_COUNT_MODEL`，以及 Anthropic 計數 client 的 `real_ai` 測試指令。
- 熱點檔案（契約、引擎、設定頁、`participants.e2e.toml`）由 `/to-tickets` 階段的 `hot-files.toml` 指定負責的 ticket。
