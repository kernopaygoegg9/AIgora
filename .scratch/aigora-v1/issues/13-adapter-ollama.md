# 13: Adapter：ollama

**What to build:** 使用者可以選本機 Ollama 模型的參與者參加討論：回覆會即時串流顯示；它不能上網，介面上會標示「無上網」。

**Scope:**
- 後端：`ollama` Adapter 模組（registry 已在 01 註冊，不必修改）與它的測試。透過 Ollama 的本機 HTTP API 呼叫；位址與模型由參與者的 `options` / `model` 設定。
- 宣告能力：`web_access = false`、`streaming = true`。
- 不得修改熱點檔案與討論引擎。介面不夠用時停下回報。

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] 可用性檢查：Ollama 沒在執行或模型不存在時回報不可用並附原因
- [ ] 串流：解析串流回應成 `delta` / `completed`
- [ ] 失敗分類與取消行為正確
- [ ] canary 測試通過（Ollama 沒有工具，作為所有 Adapter 一致的檢查）
- [ ] Smoke 測試：問一個簡短問題，收到回覆且能解析表態
- [ ] 真實 Ollama 的測試以標記區隔，預設不執行
