# 19: 有 `frontend/dist` 時後端測試失敗（SPA fallback 吃掉未知的 /api 路徑）

**Status:** resolved

**Found in:** 17（整合）。

**What:** 執行 `npm run build --prefix frontend` 產生 `frontend/dist` 之後，`uv run --directory backend pytest` 會有 1 個失敗：

```
tests/test_history.py::test_unknown_discussion_is_404
    client.get("/api/discussions/..%2F..%2Fparticipants") -> 200（預期 404）
```

原因：`backend/aigora/app.py` 只在 `frontend/dist` 存在時掛上 `SpaStaticFiles`。該路徑解碼後不符合任何 API 路由，落到靜態檔；`SpaStaticFiles.get_response` 收到的 `path` 已經正規化，不再以 `api/` 開頭，於是回傳 `index.html`（200）。沒有 dist 時則是 404，所以測試結果取決於使用者有沒有 build 過前端。

只會回傳 `index.html`，沒有讀到其他檔案，不是安全問題；但 (1) 測試不穩定、(2) 未知的 `/api/...`、`/ws/...` 路徑應該一律 404，而不是回網頁。

**Scope（建議）:**
- `app.py` 是 ticket 01 的熱點檔案，需要擁有者同意後修改：在 fallback 判斷中改用原始請求路徑（`scope["path"]`）判斷 `/api/`、`/ws/` 前綴，或讓 `/api`、`/ws` 底下的未知路徑在路由層就回 404。
- 後端測試不應依賴 `frontend/dist` 是否存在（例如 `create_app` 接受 dist 路徑參數，測試固定為不存在或固定為一個暫存資料夾）。
- 加一個「有 dist 時未知 /api 路徑仍是 404」的測試。

**Workaround:** 跑後端測試前刪除 `frontend/dist`（git-ignored）。

## Comments

- 2026-10-20（review 修正）：已修正。`SpaStaticFiles` 改用原始請求路徑（`scope["path"]`）判斷，有 `frontend/dist` 時未知的 `/api/...`、`/ws/...` 仍回 404；`create_app(frontend_dist=...)` 接受 dist 路徑（測試傳 `None` 或暫存資料夾）。測試：`backend/tests/test_spa_fallback.py`。AGENTS.md 的「跑後端測試前刪除 `frontend/dist`」workaround 已移除。
