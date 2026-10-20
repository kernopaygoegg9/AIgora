# 16: 美術：6 張預設頭像

**Type:** 美術（不走 tdd；`fake`、`default` 用 codex-imagegen 產生，四張 Adapter 頭像用官方 logo 繪製：`claude`、`gemini`、`ollama` 來源 `simple-icons`，`codex` 來源 `@lobehub/icons-static-svg`）

**What to build:** 各 Adapter 的預設頭像，讓使用者一眼分辨是哪個參與者在發言。6 張在同一張 ticket 中產生，確保風格一致。

**Scope:**
- 依 spec「Further Notes / 素材規格」：`assets/avatars/` 下的 `claude.png`、`codex.png`、`gemini.png`、`ollama.png`、`fake.png`、`default.png`；256×256，PNG，透明背景，主體置中、可裁成圓形。
- `claude`、`codex`、`gemini`、`ollama`：使用官方產品 logo 與官方品牌色（來源：`claude`、`gemini`、`ollama` 用 `simple-icons` 套件，`codex` 用 `@lobehub/icons-static-svg` 套件）；品牌色圓形內置白色 logo，品牌色過深或過淺時改用淺色圓形配品牌色 logo。僅限本機自用；公開或散布本專案前需依各家品牌規範重新檢視。
- `fake`、`default`（以及 App icon）：原創風格，扁平、幾何、圓角；**不使用、不模仿任何公司或產品的 logo、商標、吉祥物或品牌配色組合**（包括 Anthropic、OpenAI、Google、Ollama）；不含文字或字母。
- `fake.png` 要明顯看得出是測試用；`default.png` 是中性的備用頭像。
- 每次產圖都附上風格指南與已完成的圖作為參考。
- 只新增素材檔，不改任何程式碼。

**Blocked by:** None (can start immediately；只依賴 spec 的素材規格)

**Status:** claimed

- [ ] 6 張的尺寸、格式、檔名、位置與素材清單一致；背景透明；裁成圓形不會切到主體
- [ ] 使用者目視確認：6 張風格一致、彼此容易區分、`fake`、`default` 沒有模仿任何公司的 logo、四張 Adapter 頭像是正確的官方 logo、淺色與深色背景都清楚

## Comments

- 2026-10-20 使用者決定：`claude.png`、`codex.png`、`gemini.png`、`ollama.png` 改用官方產品 logo（來源 `simple-icons` 套件）；`fake.png`、`default.png` 與 App icon 不變，仍禁止使用官方 logo。僅限本機自用；公開或散布本專案前需依各家品牌規範重新檢視。
- 2026-10-20 實作：`claude`（slug `claude`，#D97757）、`gemini`（`googlegemini`，#8E75B2）、`ollama`（`ollama`，#000000，因過深改用白色圓形＋黑色 logo 與黑色外環）已替換。
- 2026-10-20 使用者決定：`codex.png` 改用 npm 套件 `@lobehub/icons-static-svg` 的官方 logo（`simple-icons` 沒有 OpenAI／Codex 圖示）。
- 2026-10-20 實作：`codex.png` 已替換，來源 `@lobehub/icons-static-svg` 1.95.1（MIT）的 Codex 專屬圖示 `icons/codex.svg`（單色版）；圓形填色採同套件 `codex-color.svg` 的官方漸層（#B1A7FF → #7A9DFF → #3941FF，由上到下），白色 logo，風格與其他三張一致。
