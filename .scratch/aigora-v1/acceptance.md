# aigora-v1 手動驗收清單（ticket 17）

自動測試（不含真實 AI）已由 ticket 17 跑過：後端 pytest、`npm run typecheck`、`npm run build`、Playwright E2E 全部通過。
以下是需要你本人執行的部分：真實 AI 的 canary / smoke 測試、一場完整的真實共識討論、以及目視驗收。所有指令都在 repo 根目錄執行。

## 1. 準備

- [ ] 安裝並登入 Gemini CLI（需你本人執行）：
  ```
  npm install -g @google/gemini-cli
  gemini
  ```
  第一次執行 `gemini` 時選擇用 Google 帳號登入，完成後 `/quit` 離開。（或在環境變數設定 `GEMINI_API_KEY`。）
- [ ] 確認其他 CLI 已登入：`claude`（Claude Code 能正常對話）、`codex login status`（顯示 Logged in）。
- [ ] Ollama（選用）：`ollama list` 至少有一個模型；沒有就 `ollama pull llama3.2`。
- [ ] 安裝依賴：`uv sync --directory backend`、`npm install --prefix frontend`。
- [ ] `copy participants.example.toml participants.toml`，把 `gemini` 的 `enabled = false` 刪掉（或改成 `true`）。
- [ ] （選用，方式 B）`copy .env.example .env`，填入 `TYPESAFE_API_KEY`。

## 2. 真實 Adapter 的 canary 與 smoke 測試

會花各家額度（Ollama 除外）。canary = 工作資料夾外放一個隨機內容的檔案，要求參與者盡力讀取，輸出中不得出現；smoke = 簡短回答 + 可解析的表態 + 上網查資料附網址。

- [ ] claude：`uv run --directory backend pytest -m real_ai tests/test_claude_adapter_real.py`
- [ ] codex：`uv run --directory backend pytest -m real_ai tests/test_codex_adapter_real.py`
- [ ] gemini：`uv run --directory backend pytest -m real_ai tests/test_gemini_adapter_real.py`
- [ ] ollama：`uv run --directory backend pytest -m real_ai tests/test_ollama_real.py`
  （指定模型：PowerShell 先 `$env:AIGORA_TEST_OLLAMA_MODEL = "gemma4:e4b"`；預設用第一個已安裝的模型）
- [ ] Jev：`uv run --directory backend pytest -m real_ai tests/test_jev_client.py`（`.env` 沒有金鑰時會 skip）

注意：CLI 沒安裝或沒登入時測試會顯示 **skipped** 而不是失敗。請確認 claude / codex / gemini 三組都是 **passed**，不是 skipped（加 `-rs` 可看 skip 原因）。

### 尚未驗證、要靠上面的測試確認的點

- [ ] **claude / codex / gemini 的隔離參數都還沒有對真實 CLI 跑過 canary**（ADR 0002）。canary 沒過之前，不要拿真實參與者討論涉及私密資料的問題。
- [ ] **codex 上網**：exec 模式沒有 `--search`，adapter 改用 `-c web_search="live"` 開啟；看 `test_smoke_web_search_returns_a_url` 是否通過。
- [ ] **codex `--ignore-user-config`**：確定會略過 `~/.codex/config.toml`，但**不確定是否仍會載入 `~/.codex/AGENTS.md`**（你的使用者指示）。驗證方式：在討論頁只選 Codex 用「提問」問「你目前有收到任何使用者自訂指示（AGENTS.md）嗎？請原文列出」，或觀察回覆是否明顯套用了 `~/.codex/AGENTS.md` 的偏好（例如固定用繁體中文、提到 MCP）。若會載入，開新 ticket 處理。
- [ ] **claude `--setting-sources ""`**：同上，確認 Claude 參與者沒有套用 `~/.claude/CLAUDE.md`。
- [ ] **gemini 隔離**：Gemini CLI 沒有「忽略使用者設定」的參數，adapter 改用 system settings override（`GEMINI_CLI_SYSTEM_SETTINGS_PATH`）+ `--admin-policy` + `--extensions none` + `--allowed-mcp-server-names <不存在的名稱>`。參數只取自官方文件，從未對已安裝的 CLI 實測；canary 通過前視為未驗證。若你在 `~/.gemini/settings.json` 設有 MCP 或擴充功能，canary 正好可以順便確認它們沒被載入。另外確認 `GEMINI.md` 沒被載入（同上的問法）。

## 3. 一場完整的真實共識討論

- [ ] 啟動：`npm run dev --prefix frontend`，開 http://127.0.0.1:5173。
- [ ] 參與者清單：Claude、Codex、Gemini 都顯示為可用、頭像正確；Ollama 若啟用則標示「無上網」。
- [ ] 設定面板：討論模式「共識討論」，勾選 Claude、Codex、Gemini，共識裁定方式 A，主持人選一位，輪數上限先設 **3**（省額度）。
- [ ] 問一個容易收斂的問題（例如「在一般 Windows 筆電上，Python 專案管理推薦用 uv 還是 pip + venv？請附出處。」），送出。
- [ ] 確認：發言即時串流、並排顯示；第 1 輪後出現共識草案；第 2 輪起每人有表態；達成共識時出現獨立的共識結果。
- [ ] 回覆語言與問題相同；引用網路資料時附網址。
- [ ] 第二場：問一個有爭議的問題（例如「Tab 還是空白縮排比較好？」），輪數上限 **2**，確認未達成共識時輸出「各參與者的最終立場」與「仍有分歧的重點」。
- [ ] 插話：討論中送出插話，下一輪的發言有回應到它。
- [ ] 停止：按停止後所有發言立即結束（工作管理員中不應殘留 `claude` / `codex` / `node`(gemini) 子行程），紀錄以 stopped 存檔。
- [ ] 提問轉共識：用「提問」問一題，結束後按「開始共識討論」，原本的回答直接成為第 1 輪。
- [ ] （選用）方式 B：`.env` 設好金鑰後，共識裁定方式 B 可選；顯示 Jev 機率與反問結果。沒有金鑰時 B 為灰色不可選並說明原因。
- [ ] 歷史：剛才的討論都出現在歷史清單，能以唯讀方式打開，內容完整（`data/discussions/*.json`）。

## 4. Ollama 只改設定檔即可加入

- [ ] 在 `participants.toml` 的 ollama 段填入已安裝的 `model`（例如 `model = "gemma4:e4b"`）並啟用，不改任何程式；重新整理頁面（必要時重啟後端）後 Ollama 可選，能參加一場提問或共識討論，並標示「無上網」。

## 5. 目視驗收素材

- [ ] 頁首左上角顯示 App icon；瀏覽器分頁的 favicon 是 AIgora 圖示（16/32 px 都清楚可辨）。
- [ ] 參與者頭像：claude、codex、gemini、ollama 為各家官方 logo；Fake 為測試用燒瓶；未知 Adapter 或缺圖時為預設人像。

## 6. Spec 成功條件（ticket 17）

- [ ] 畫面上使用正式素材（第 5 節）
- [ ] 所有自動測試通過，真實 Adapter 的測試在已安裝的 CLI 上通過（第 2 節）
- [ ] 所有真實 Adapter 的 canary 測試通過：參與者無法讀取工作資料夾以外的檔案（第 2 節）
- [ ] Claude、Codex、Gemini 三個參與者完成一場共識討論並輸出結果；未取得共識時能輸出各方立場與分歧點（第 3 節）
- [ ] 在 `participants.toml` 加入 Ollama 參與者即可參加討論，不需改其他程式（第 4 節）

全部打勾後，把 ticket 17 標為 resolved；過程中發現的問題請開新 ticket（`.scratch/aigora-v1/issues/`，Status: needs-triage）。
