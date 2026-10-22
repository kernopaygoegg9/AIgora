# 10: Anthropic token 計數

**Type:** 程式（tdd）

**What to build:** `.env` 有 `AIGORA_ANTHROPIC_API_KEY` 時，上下文用量改用 Anthropic 的 token 計數 API 計算，設定面板顯示「token 計數：Anthropic API」；某次失敗時改用本機估算並記錄。金鑰不外洩，也不影響 Claude CLI 的計費方式。

**Scope:**
- Anthropic 計數 client：使用 Messages 的 token 計數端點（不收費）；模型用固定常數，可用 `AIGORA_TOKEN_COUNT_MODEL` 覆蓋；金鑰經 `backend_env()` 讀取。
- 計數器工廠：有金鑰時用 Anthropic，否則本機估算；每段失敗時該段改用估算，該次呼叫的 `counter` 記為 `estimate`。
- `/api/options` 的 `token_counter` 依金鑰回報 `anthropic` / `estimate`；不回傳金鑰。
- Claude Adapter（與其他會建子行程的 Adapter）建立子行程環境時移除 `AIGORA_ANTHROPIC_API_KEY`。
- `.env.example` 新增變數與說明；`AGENTS.md` 的 Backend env vars 與 `real_ai` 測試指令。

**Blocked by:** 08

**Status:** ready-for-agent

- [ ] 後端：以假 client（monkeypatch 計數器工廠，比照 `fake_jev`）證明有金鑰時用 API 的數字，`counter = anthropic`
- [ ] 後端：假 client 拋錯時改用估算，`counter = estimate`，討論不中斷
- [ ] 後端：`/api/options` 依金鑰回報 `token_counter`，任何回應與 WebSocket 訊息都不含金鑰
- [ ] 後端：用現有 fake CLI 證明 Claude 子行程的環境中沒有 `AIGORA_ANTHROPIC_API_KEY`
- [ ] `real_ai` 測試：有金鑰時呼叫真實 API 得到正整數；沒有金鑰時略過（不在這張 ticket 中執行）
- [ ] E2E：設定面板顯示「token 計數：本機估算」（E2E 環境沒有金鑰）
