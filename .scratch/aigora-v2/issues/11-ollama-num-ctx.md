# 11: Ollama 依上下文上限設定 num_ctx

**Type:** 程式（tdd）

**What to build:** Ollama 參與者真的看得到使用者設定的上下文上限那麼多內容，不會被 Ollama 預設的短 context 默默截斷。

**Scope:**
- Ollama Adapter 在生成請求的 `options.num_ctx` 設為：這次的上下文上限 + 回覆預留量（常數，例如 4096）；沒有上限時用預設大值（常數，例如 32768）。
- `docs/architecture/adapters.md` 的 ollama 段落補上這條規則（若 13 尚未更新）。

**Blocked by:** 08

**Status:** ready-for-agent

- [ ] Adapter 測試（`httpx.MockTransport`）：有上限時 `num_ctx` = 上限 + 預留量；沒有上限時為預設大值
- [ ] 既有 Ollama Adapter 測試全部通過；不執行 `real_ai` 測試
