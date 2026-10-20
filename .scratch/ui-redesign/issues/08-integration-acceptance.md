# 08: 整合與驗收

Status: ready-for-human

Blocked by: 01, 02, 03, 04, 05, 06, 07

**What to build:** 確認整個新介面一致、沒有遺漏，交給使用者目視驗收。

**Scope:**
- 只修小問題（間距、對比、文字）。發現較大的問題時，記在對應 ticket 的 Comments 或另開新 ticket。
- 驗收通過後刪除 `.scratch/ui-redesign/prototype/`（原型已經留在 git 歷史中）。

- [ ] typecheck、production build（`npm run build --prefix frontend`）與全部 E2E 通過
- [ ] 用 Fake Adapter 跑完提問、提問轉共識討論、共識討論（方式 A）、未取得共識、停止、失敗與移出，亮色與暗色各截一張圖
- [ ] 1280px、1024px、760px 三種寬度都沒有破版，頁面沒有水平捲軸
- [ ] 兩種主題下文字與背景的對比都符合 WCAG AA（一般文字 4.5:1）
- [ ] 使用者用真實參與者（Claude、Codex，加上選用的 Ollama）跑一場討論並目視驗收

## Comments
