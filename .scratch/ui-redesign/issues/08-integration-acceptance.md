# 08: 整合與驗收

Status: ready-for-human

Blocked by: 01, 02, 03, 04, 05, 06, 07, 09, 10, 11

**What to build:** 確認整個新介面一致、沒有遺漏，交給使用者目視驗收。

**Scope:**
- 只修小問題（間距、對比、文字）。發現較大的問題時，記在對應 ticket 的 Comments 或另開新 ticket。
- 驗收通過後刪除 `.scratch/ui-redesign/prototype/`（原型已經留在 git 歷史中）。

- [x] typecheck、production build（`npm run build --prefix frontend`）與全部 E2E 通過
- [x] 用 Fake Adapter 跑完提問、提問轉共識討論、共識討論（方式 A）、未取得共識、停止、失敗與移出，亮色與暗色各截一張圖
- [x] 1280px、1024px、760px 三種寬度都沒有破版，頁面沒有水平捲軸
- [x] 兩種主題下文字與背景的對比都符合 WCAG AA（一般文字 4.5:1）
- [x] 後端測試全部通過（`uv run --directory backend pytest`）；有安裝的 CLI 跑一次 `list_models` 的 `real_ai` 測試
- [x] 用 Fake Adapter 跑一場「同一個 Adapter 不同模型＋臨時參與者當主持人」的共識討論，打開它的唯讀紀錄，並打開一份 schema 1 的舊紀錄
- [ ] 使用者用真實參與者跑一場「2 個 Claude（不同模型）＋1 個 Codex」的討論
- [ ] 使用者用真實參與者（Claude、Codex，加上選用的 Ollama）跑一場討論並目視驗收

## Comments

### 2026-10-21 自動化部分（agent）

勾選的前 6 項已完成；最後兩項（真實參與者）留給使用者，所以 Status 維持 ready-for-human。原型目錄還沒刪，等使用者驗收通過再刪。

**測試結果**
- `npm run typecheck --prefix frontend`、`npm run build --prefix frontend`：通過。
- E2E：39 passed。修正後第一次全跑時 `settings-panel.spec.ts:25` 失敗一次（沒留下錯誤訊息），單獨重跑和再全跑一次都通過，看起來是偶發 flake。
- 後端 `uv run --directory backend pytest`：291 passed，14 deselected（`real_ai`）。
- `real_ai` 的 `list_models`（`-k model_list`）：codex、ollama 2 passed。claude 的清單是固定的，不會呼叫 CLI，所以沒有對應的 real_ai 測試。這次沒有跑任何會花額度的測試。

**截圖**（不在 repo 內）：`C:\Users\KERUEI~1\AppData\Local\Temp\claude\D--OpenKWL-Projects-AIgora--claude-worktrees-ui-redesign-02be96\99b99627-08b1-4306-a85c-3b875a85d8c2\scratchpad\t08\shots\`
- 每個狀態都有 `<狀態>-light.png`／`-dark.png`（1280px，整頁），也有 `-dark-1024.png`、`-light-760.png`、`-dark-760.png`。
- 狀態：00 設定頁、01 提問、02 提問轉共識討論、03 共識討論（方式 A，含無上網參與者）、04 未取得共識（Fake A＋Fake Echo，輪數上限 2）、05a 進行中＋插話佇列、05b 停止、06 失敗與移出（Fake Flaky 擔任主持人）、07a/07b/07c 同一個 Adapter 不同模型（Fake A `fake-small`）＋臨時參與者 Fake A（`fake-large`）擔任主持人：設定頁、結束畫面、唯讀紀錄、08 歷史頁、09a schema 1 共識紀錄（和 `history.spec.ts` 的 mock 同樣內容，放進暫存 data dir）、09b schema 1 提問紀錄（`backend/tests/fixtures/record-schema1-ask.json`）。
- 腳本 `shots.cjs` 和結果 `report.json` 放在同一個資料夾。

**寬度**：上面每個狀態 × 兩種主題 × 1280／1024／760 共 84 次檢查，`scrollWidth <= innerWidth` 全部成立，也沒有元素超出所在欄（舞台、檢視器、側欄）。

**對比**：用 `tokens.css` 算出每個文字色（text、text-2、muted、accent、ok、bad、warn）在每個底色（bg、panel、panel-2、各語意淡底）上的對比，也在每個畫面的實際 DOM 上掃過（算進 opacity 和半透明底色）。

**已修正（小問題）**
1. 對比：亮色的 `--ok` `#13854f` 在 bg（4.32）、panel-2（4.12）、ok-bg（4.37）、accent-bg 上都不到 4.5:1，改成 `#117e4b`，最低是 4.51（panel-2）。`tokens.css` 是 01 的熱點檔案，依本 ticket 的範圍只做這個最小調整。修正後所有 token 組合都至少 4.5:1。
2. 對比：模型標籤（`ParticipantLabel.vue` `.model`）多了 `opacity: 0.85`，亮色只有 3.48。拿掉 opacity 之後，muted 本身就夠淡，最低 4.62。
3. 對比：檢視器裡已移出的參與者整列用 `opacity: 0.5`，名稱在亮色只有 3.18、模型標籤 1.74。改成文字用 `--muted`＋刪除線，只有頭像維持 0.5 透明（`InspectorParticipants.vue`）。
4. 版面：1024–1279px 時設定頁的參與者表格因為 `nowrap` 撐到約 690px，超出舞台，壓在檢視器底下；1280px 也超出 5px。改成只在 1280px 以上不換行，儲存格左右 padding 從 12px 改成 10px，並且依 spec「1024–1279px 檢視器縮窄」在 `tokens.css` 加了 `--inspector-width: 260px`（原本沒有任何 ticket 實作這一點）。

**沒有修，只記錄（較大，或屬於其他 ticket）**
- 停用中的元件對比不到 4.5:1：停用的「開始討論」「送出插話」約 2.5–2.7，不可用的 Jev 選項及原因文字 2.4–4.3。WCAG 1.4.3 對停用元件不要求，所以沒改；但「不可用：.env 沒有設定 TYPESAFE_API_KEY」是有用的資訊，如果希望它好讀，可以只把原因文字移出 opacity（03／11）。
- 側欄「最近的討論」在討論進行中不會出現這場討論，結束後才出現。原因是側欄在 `running` 時重新載入，但後端第 1 輪完成後才第一次存紀錄（`engine._complete_round`）。修法可以是側欄在第 1 輪完成時也重新載入；這屬於 02 的行為，所以沒改。
- 1024–1279px 和 760px 下設定頁表格很擠：名稱逐字換行、模型下拉被截成「預設（Ada」、「不可用：fake: CLI not installed」變成很高的 pill。沒有破版，但可以考慮在 1280px 以下隱藏 ADAPTER 欄，或把狀態原因改成換行文字（03／11）。如果遇到很長的模型名稱，表格在 1024px 仍然可能被撐寬。
- 1024px 時一輪有 3 張發言卡片就需要橫向捲動（第 3 張只露出邊緣），捲軸也不明顯。這符合 spec「只有那一輪可以橫向捲動」，但 3 張就要捲動可能不是想要的結果（04）。
- 760px 時插話框的 placeholder 第二行被切掉（「（Ctrl+Enter 送出）」）（04）。
- 整頁截圖裡側欄只有一個視窗高，這是 sticky 側欄在整頁截圖中的正常現象，實際捲動時沒有問題。
