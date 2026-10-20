# 16: 美術：6 張預設頭像

**Type:** 美術（用 codex-imagegen 產生，不走 tdd）

**What to build:** 各 Adapter 的預設頭像，讓使用者一眼分辨是哪個參與者在發言。6 張在同一張 ticket 中產生，確保風格一致。

**Scope:**
- 依 spec「Further Notes / 素材規格」：`assets/avatars/` 下的 `claude.png`、`codex.png`、`gemini.png`、`ollama.png`、`fake.png`、`default.png`；256×256，PNG，透明背景，主體置中、可裁成圓形。
- 原創風格：扁平、幾何、圓角；以不同主色與不同抽象圖形區分。**不使用、不模仿任何公司或產品的 logo、商標、吉祥物或品牌配色組合**（包括 Anthropic、OpenAI、Google、Ollama）；不含文字或字母。
- `fake.png` 要明顯看得出是測試用；`default.png` 是中性的備用頭像。
- 每次產圖都附上風格指南與已完成的圖作為參考。
- 只新增素材檔，不改任何程式碼。

**Blocked by:** None (can start immediately；只依賴 spec 的素材規格)

**Status:** ready-for-human

- [ ] 6 張的尺寸、格式、檔名、位置與素材清單一致；背景透明；裁成圓形不會切到主體
- [ ] 使用者目視確認：6 張風格一致、彼此容易區分、沒有模仿任何公司的 logo、淺色與深色背景都清楚
