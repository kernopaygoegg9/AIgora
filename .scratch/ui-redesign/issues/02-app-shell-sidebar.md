# 02: App 外框：側欄、最近的討論、主題切換

Status: resolved

Blocked by: 01

**What to build:** 把 `AppLayout` 改成原型 A 的「側欄 + 主要區域」。側欄有品牌、「討論」「歷史」導覽、最近的討論清單和主題切換。見 spec「版面（AppLayout）」與原型 `?variant=A`。

**Scope:**
- 修改 `frontend/src/layouts/AppLayout.vue`。
- 新增 `frontend/src/components/layout/` 底下的元件（例如 `SidebarHistory.vue`、`ThemeToggle.vue`）。
- 新增 `frontend/e2e/theme.spec.ts`。
- 只讀取 store（`useDiscussionStore` 的 `status`、`discussionId`），並呼叫既有的 `reset()`；不修改 store、契約、router、後端；不修改其他頁面或元件。

- [x] 側欄頂部是頂層 `<header>`（`getByRole('banner')` 包含 AIgora）：App icon（保留 `data-testid="app-logo"`）、AIgora，以及 `<nav>` 裡的「討論」「歷史」`RouterLink`（可存取名稱維持完全相同）
- [x] 「最近的討論」顯示 `fetchDiscussions()` 的前 20 筆（問題截成一行，下面是模式、時間、結果），點下去開唯讀紀錄，目前看的那筆有標示；最後是「查看全部 →」
- [x] `store.status` 變成 `running` 或 `finished` 時重新載入清單
- [x] 已經在 `/` 而且討論已結束時，點「討論」會 `store.reset()` 回到設定頁；討論進行中不會被重設
- [x] 側欄底部的主題切換依序循環「跟隨系統 → 亮色 → 暗色」，並顯示目前的模式
- [x] 寬度 760px 以下側欄收成頂部列，頁面沒有水平捲軸
- [x] `theme.spec.ts`：切換後 `<html data-theme>` 改變，重新整理後仍保留
- [x] typecheck 與全部 E2E 通過；亮色、暗色各附一張截圖到 Comments

## Comments

- 2026-10-20：完成。
  - 新增 `components/layout/SidebarHistory.vue`（testid `sidebar-history`、`sidebar-history-item`，沒有用 `history-item`，避免和歷史頁的測試混淆）與 `ThemeToggle.vue`（`theme-toggle`）。
  - 「討論」連結裡的「＋」加了 `aria-hidden`，可存取名稱仍然是「討論」。
  - **提前做了原本屬於 07 的刻意測試修改**：主題切換按鈕出現在每一頁，所以 `history.spec.ts` 中唯讀頁「沒有 button／textbox」的斷言一加上按鈕就會失敗。已經改成在 `record-view` 範圍內檢查（共 2 處），07 不用再改。
  - `theme.spec.ts`：測試循環切換、重新整理後保留，以及跟隨系統時的背景色。
  - 驗證：typecheck 通過，E2E 35 passed。截圖：1280px 亮色與暗色、700px（頂部列）。
