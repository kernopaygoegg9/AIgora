# 01: 設計 token、基底樣式與主題機制

Status: resolved

Blocked by: —

**What to build:** 建立整個前端共用的設計 token 與基底樣式，並提供亮色／暗色主題機制（預設跟隨系統，可以手動覆蓋並記住）。完成後畫面結構不變，但所有頁面都已經套用新的底色、字型與 token，系統是暗色時顯示暗色。見 spec「設計 token 與主題」。

**Scope:**
- 新增 `frontend/src/styles/tokens.css`、`frontend/src/styles/base.css`、`frontend/src/composables/useTheme.ts`。
- 修改 `frontend/src/main.ts`（匯入樣式）、`frontend/index.html`（載入前先套用已存主題的內嵌 script）、`frontend/src/layouts/AppLayout.vue`（**只**移除全域 `<style>` 區塊，搬到 `base.css`；版面留給 02）。
- `base.css` 提供共用的原子樣式：`.pill`（含 ok／bad／warn／accent 變化）、`.btn`（含 primary／danger）、表單元件（input、select、textarea，以及 checkbox、radio 的 accent-color）、焦點框、捲軸、`.visually-hidden`。
- 不改任何元件的 scoped 樣式（之後的 ticket 各自負責）。現有元件裡寫死的顏色在暗色主題下可能暫時不協調，這是預期的。
- 不新增 npm 套件；不修改 store、契約、router、後端。

- [x] `tokens.css` 定義 spec 表格中的顏色 token（含各語意色的淡底與邊框）、間距、圓角、字級、陰影，亮色與暗色各一組
- [x] 主題規則：沒有 `data-theme` 時跟隨 `prefers-color-scheme`；有 `data-theme="light|dark"` 時強制使用
- [x] `useTheme()` 提供 `mode`（`system` / `light` / `dark`）與 `cycle()`，存在 `localStorage` 的 `aigora.theme`，讀寫都包 try/catch
- [x] `index.html` 的內嵌 script 在 Vue 載入前套用已存的主題（避免閃一下）
- [x] `body` 有明確的背景色與文字色；字型堆疊符合 spec
- [x] `npm run typecheck --prefix frontend` 與 `cd frontend && npx playwright test` 全部通過

## Comments

- 2026-10-20：完成。
  - 亮色的 `--muted` 調成 `#626d7f`、`--warn` 調成 `#9a6100`，讓文字在 `--bg #f5f6f8` 上也達到 AA 對比（spec 允許微調）。
  - 另外加了 `--text-2`（卡片內文）、`--on-accent`（主色按鈕上的文字），以及字級、間距、圓角、側欄與檢視器寬度的 token。
  - 驗證：typecheck 通過，E2E 33 passed。用 Fake 參與者實際開啟確認：系統是暗色時頁面是暗色；`localStorage` 的 `aigora.theme=light` 在重新整理後由 `index.html` 先套用。
  - 已知暫時狀態：`AppLayout` 的頂部列與各元件 scoped 樣式中寫死的淺色在暗色主題下還不協調，由 02–07 處理。
