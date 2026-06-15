# 給大哥(Claude Code)的指令 — 第三輪微調

> 來自 chat(二哥)。兩件小事,都是「已經做了但體驗不對」的修正,不是新功能。

---

## 任務 1 — 🗺 地圖按鈕要「看得見」

**問題**:地圖功能**已經實作且正常運作**(地點「📍 安南區」旁那個小圖示點下去確實會開 Google Maps),但它太小、太隱晦,使用者根本沒發現能點。地圖是核心動作(獵人要真的走過去吃),不能藏成米粒大的圖示。

**做法**:**把現有那個小地圖連結,換成一顆明顯的按鈕**,放在每張懸賞卡的「接令 →」按鈕旁邊並排;詳情頁 `/bounty/<id>` 也放一顆。用這段取代現有的小圖示(URL 邏輯不變,只是改外觀和位置):

```html
<a href="https://www.google.com/maps/search/?api=1&query={{ shop.name | urlencode }}&query_place_id={{ shop.place_id }}"
   target="_blank" rel="noopener" class="map-btn">🗺 地圖</a>
```

```css
.map-btn{
  font-family:'DotGothic16'; font-size:13px; color:#5a3818;
  background:linear-gradient(180deg,#efe3c0,#e0cfa0);
  border:1.5px solid #b59a64; border-radius:3px;
  padding:9px 14px; text-decoration:none; white-space:nowrap;
  box-shadow:0 2px 0 #9a8050; display:inline-flex; align-items:center; gap:4px;
}
.map-btn:active{ transform:translateY(2px); box-shadow:0 0 0 #9a8050; }
```

**要點**:
- 「接令」(主色紅)和「地圖」(羊皮紙色,次要)兩顆鈕並排在卡片底部
- `shop.place_id` = schema 的 `place_id` 欄位;`shop.name` 記得 `| urlencode`
- `target="_blank" rel="noopener"` 開新分頁
- **移除地點旁原本那個小圖示**,改用這個明顯版本(別留兩個地圖連結,URL 邏輯沿用你原本就在用的那組,正常運作不用改)

---

## 任務 2 — 🎭 酒館店主不要被 UI 遮住

**問題**:酒館主畫面的店主立繪,上半身被 UI(對話框/執照/按鈕)蓋掉一大半,只剩一顆頭露出來,可惜了立繪。

**目標**:讓店主**完整露出上半身**,UI 避開人物、不正面重疊。

**做法**(現有立繪是「人物置中」構圖,以下二擇一,挑不破版的):

- **做法 A(優先試):UI 整體下沉 + 對話框半透明**
  - 把對話框/執照/按鈕整組往畫面**下半部**壓,上半部留給立繪完整露出
  - 對話框背景改半透明(如 `rgba(240,226,192,.88)` + `backdrop-filter:blur(2px)`),即使輕微疊到人物下緣也透得出來
  - 立繪用 `background-size:cover; background-position:center top;` 確保臉在上方露出
  - 由下往上加一層暗色漸層 scrim(底部深、上部透),讓下半 UI 區沉下來、人物區透亮(參考 `tavern_keeper_switch_demo.html` 的 `.scrim`)

- **做法 B(若使用者想要「JRPG 命令選單」感):立繪偏左 + 選單靠右**
  - `background-position` 把立繪推向左側顯示,右側與下方留給 UI 直排
  - ⚠ 注意:現有圖是置中構圖,硬偏左可能切到人物右半邊。若切太多不好看,退回做法 A

**建議**:手機 390px 直式螢幕,做法 A 通常比較不破版(純右側命令欄是橫式螢幕的構圖,豎屏會擠)。請以「店主完整露出 + UI 好點不破版」為準,A 不行再試 B。

---

## 驗收

1. 懸賞卡和詳情頁都有明顯的「🗺 地圖」鈕,點了正確跳轉 Google Maps 到該店
2. 地點旁不再有重複的小地圖圖示
3. 酒館店主立繪上半身完整露出,UI 不正面蓋住臉
4. 三位店主切換時,排版都不破版(大叔/帥哥/女主人立繪比例可能不同,需各別確認)
5. 手機 390px 寬正常,reduced-motion 動畫停用

## 不要動
- 後端邏輯、EXP 公式、schema、已完成的討伐流程/遠征/圖鑑 → 別重構
- 刻意設計:C=60、二刷×0.3、隱藏名店×2、等級不存欄位 → 保留
