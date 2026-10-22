# 06: 用詞檢查

**Type:** 程式（tdd）

**What to build:** 前端使用者看得到的文字出現 GLOSSARY 的 _Avoid_ 詞時，`check` 失敗並指出位置與正確用詞。

**Scope:**
- `scripts/check_glossary.py`，規則見 spec「用詞檢查」。
- 測試以暫存資料夾裡的假 `GLOSSARY.md` 與假前端檔案驗證。
- 接進 `frontend/package.json` 的 `check` 與 `check:fast`（只改這兩行 script）。
- 修掉目前 `frontend/src` 中真正的違規（若有）；誤判用 `glossary-ignore` 並在 PR 說明。

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] 測試涵蓋：template 文字命中、字串常值命中、註解不命中、識別字不命中、「討論模式」中的「模式」不命中、`glossary-ignore` 略過、括號說明被去掉
- [ ] 違規輸出格式為 `檔案:行: 用詞「X」，請改用「Y」`，結束碼非零
- [ ] 把 v1 的「現有的回答當作第 1 輪」暫時放回某個元件，`check:fast` 會失敗（驗證後還原）
- [ ] `npm run check --prefix frontend` 在目前的程式碼上通過
