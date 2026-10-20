# 14: Adapter：gemini

**What to build:** 使用者可以選 Gemini CLI 的參與者參加討論：回覆會即時串流顯示（若 CLI 支援），它可以上網查資料，但完全無法讀寫本機檔案。

**Scope:**
- 後端：`gemini` Adapter 模組（registry 已在 01 註冊，不必修改）與它的測試。
- **開始前必須先徵求使用者同意，才能安裝 Gemini CLI。** 未取得同意前不要安裝，停下回報。
- 安裝後找出 Gemini CLI 的非互動、輸出格式、工具限制、忽略使用者設定與 MCP 的參數，依 ADR 0002 只保留網路搜尋；在工作資料夾中執行。找到的參數組合補記到 ADR 0002 的 Consequences。
- 不得修改熱點檔案與討論引擎。介面不夠用時停下回報。

**Blocked by:** 02

**Status:** ready-for-human

- [ ] 已取得使用者同意並安裝 Gemini CLI
- [ ] 可用性檢查：未安裝或未登入時回報不可用並附原因
- [ ] 串流或一次回傳的解析正確，能力宣告與實際一致
- [ ] 失敗分類與取消行為正確
- [ ] **Participant 無法讀取工作資料夾以外的檔案**：canary 測試通過
- [ ] Smoke 測試：問一個簡短問題，收到回覆且能解析表態；能用網路搜尋並附網址
- [ ] 真實 CLI 的測試以標記區隔，預設不執行

## Comments

- 2026-10-20 (orchestrator): Adapter code + unit tests merged into `aigora-v1`. Gemini CLI install was blocked by the permission system; user must run `npm install -g @google/gemini-cli`, log in, then run the real_ai tests per `.scratch/aigora-v1/acceptance.md`. Resolve after canary/smoke pass.
- 2026-10-20 (orchestrator): User decided **not to use Gemini in v1**; ticket stays open. Real-CLI probe (no valid login) found, before auth:
  1. Admin policy / system settings temp dir rejected as insecure on Windows: `OWNER RIGHTS` has write permission on `%TEMP%igora-gemini-*`. Needs a dir ACL granting only the current user (POSIX 0700/0600).
  2. `aigora-policy.toml` schema validation failed: `rule.3.toolName: Invalid input` (rule #1) — policy is rejected, so isolation would NOT apply. Match the installed CLI's policy schema.
  3. Headless run needs `--skip-trust` or `GEMINI_CLI_TRUST_WORKSPACE=true`; `security.folderTrust.enabled=false` in the override is not enough.
  4. Auth: Google personal OAuth now fails with `IneligibleTierError` (client no longer supported for Gemini Code Assist for individuals). Use `GEMINI_API_KEY` (env or `~/.gemini/.env`); user's `~/.gemini/settings.json` still has `security.auth.selectedType = oauth-personal` — consider setting the auth type in the adapter's settings override when an API key is present.
  5. The real canary "passed" only because the CLI failed to start; real tests must treat a `Failed` turn as failure/skip, not pass. Also make the adapter fail hard if the CLI reports an admin-policy load error.
