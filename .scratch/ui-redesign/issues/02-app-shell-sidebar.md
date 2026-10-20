# 02: App 外框：側欄、最近的討論、主題切換

Status: ready-for-agent

Blocked by: 01

**What to build:** 把 `AppLayout` 改成原型 A 的「側欄 + 主要區域」。側欄有品牌、「討論」「歷史」導覽、最近的討論清單和主題切換。見 spec「版面（AppLayout）」與原型 `?variant=A`。

**Scope:**
- 修改 `frontend/src/layouts/AppLayout.vue`。
- 新增 `frontend/src/components/layout/` 底下的元件（例如 `SidebarHistory.vue`、`ThemeToggle.vue`）。
- 新增 `frontend/e2e/theme.spec.ts`。
- 只讀取 store（`useDiscussionStore` 的 `status`、`discussionId`），並呼叫既有的 `reset()`；不修改 store、契約、router、後端；不修改其他頁面或元件。

- [ ] 側欄頂部是頂層 `<header>`（`getByRole('banner')` 包含 AIgora）：App icon（保留 `data-testid="app-logo"`）、AIgora，以及 `<nav>` 裡的「討論」「歷史」`RouterLink`（可存取名稱維持完全相同）
- [ ] 「最近的討論」顯示 `fetchDiscussions()` 的前 20 筆（問題截成一行，下面是模式、時間、結果），點下去開唯讀紀錄，目前看的那筆有標示；最後是「查看全部 →」
- [ ] `store.status` 變成 `running` 或 `finished` 時重新載入清單
- [ ] 已經在 `/` 而且討論已結束時，點「討論」會 `store.reset()` 回到設定頁；討論進行中不會被重設
- [ ] 側欄底部的主題切換依序循環「跟隨系統 → 亮色 → 暗色」，並顯示目前的模式
- [ ] 寬度 760px 以下側欄收成頂部列，頁面沒有水平捲軸
- [ ] `theme.spec.ts`：切換後 `<html data-theme>` 改變，重新整理後仍保留
- [ ] typecheck 與全部 E2E 通過；亮色、暗色各附一張截圖到 Comments

## Comments
