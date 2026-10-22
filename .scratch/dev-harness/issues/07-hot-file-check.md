# 07: 熱點檔案歸屬檢查

**Type:** 程式（tdd）

**What to build:** 合併前能自動判斷一個 implementer 分支是否改了不屬於它的熱點檔案。

**Scope:**
- `.scratch/<feature>/hot-files.toml` 格式（路徑或 glob → 擁有的 ticket 編號；可標「所有 ticket 皆可改」），寫進 `docs/agents/issue-tracker.md`。
- `scripts/check_hot_files.py --feature <slug> --ticket <NN> <base>..<branch>`，見 spec。
- 本 feature 的 `.scratch/dev-harness/hot-files.toml` 已由 spec 階段建立，本 ticket 驗證它能被讀取。
- 測試以暫存資料夾裡的假 git repo 驗證。

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] 測試涵蓋：只改自己擁有的檔案 → 通過；改到別張 ticket 的熱點檔案 → 失敗並列出檔案與擁有者；改到「所有 ticket 皆可改」的檔案 → 通過；改到不在表中的檔案 → 通過；glob 比對
- [ ] 對本 feature 的實際分支執行一次（例如 01 的分支對 `dev-harness`），結果正確
- [ ] `docs/agents/issue-tracker.md` 說明 `hot-files.toml` 的格式與用途
