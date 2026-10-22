# 05: 測試不留下子行程

**Type:** 程式（tdd）

**What to build:** 會產生孫行程的測試（取消、結束行程樹）即使失敗，teardown 後也不留下任何行程。

**Scope:**
- 假 CLI（`backend/tests/fake_claude_cli.py`、`fake_codex_cli.py`、`fake_gemini_cli.py`）把自己產生的子行程 PID 寫到測試的暫存資料夾。
- `backend/tests/conftest.py` 新增 fixture：teardown 時結束仍存活的這些 PID（Windows 與 POSIX 都要能用，可沿用 `aigora/adapters/subprocesses.py` 的做法）。
- 相關測試改用這個 fixture。
- `docs/architecture/testing.md` 補一句說明。

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] 有一個測試證明：模擬「取消沒有結束行程樹」時，fixture 的 teardown 之後那個孫行程已不存在
- [ ] 跑完整個 `uv run --directory backend pytest` 後，沒有任何由測試產生、仍在執行的 python 行程（以行程清單比對驗證）
- [ ] `npm run check --prefix frontend` 通過
