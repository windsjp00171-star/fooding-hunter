# 給大哥(Claude Code)的指令 — 系統正式落地

> 來自 chat(二哥)。目標:把核心閉環補完 + 填掉兩個「施工中」頁面。
> 按優先序做,每件 checkpoint 再下一件(Rule 10)。

---

## 優先序(由高到低)

1. 討伐完成流程(核心閉環最後一塊,最優先)
2. 遠征選區頁(填掉施工中)
3. 基本圖鑑(填掉施工中,先求能用)
4. 三店主切換 + 大圖背景(視覺強化,立繪已備)

---

## 任務 1 — 討伐完成流程 ⭐ 最優先

目前點「接令 →」後沒有真正能完成任務、拿 EXP 的流程。補完:

**1a. `/bounty/<shop_id>` 詳情頁**
- 顯示:委託標題(用 flavor)、店名、分級章、賞金、店家評分/地址
- **🗺 地圖按鈕**(這是之前漏的!):`https://www.google.com/maps/search/?api=1&query={店名urlencode}&query_place_id={place_id}`,`target="_blank" rel="noopener"`
- 「討伐完成」按鈕(自評 1-5 星 + 可選短評文字)
- 視覺對齊酒館木質風(羊皮紙委託單質感),別做成白底表單

**1b. POST `/bounty/<shop_id>/complete`**
- **EXP 計算必須在這個 transaction 內即時查 revisit count**(查 hunts 既有同店次數),不可先查後寫:
  ```
  base = S:50/A:40/B:30/C:60
  multiplier = (2 if is_hidden_gem else 1) * (0.3 if visit_count >= 1 else 1)
  exp_gained = round(base * multiplier)
  ```
- 寫入 hunts(含 exp_gained、player_rating、review_text、district 快照)
- **防重複提交**:按鈕送出後 disable;後端擋「同 bounty 已 completed 就不再受理」
- **升級偵測在後端做**:比較「加 EXP 前的等級」vs「加後的等級」,跨門檻 = 升級,把結果傳給結果畫面(前端不自己算等級,維持 EXP 為單一真相源)

**1c. 結果畫面**
- 顯示獲得 EXP、是否升級(升級則觸發升級儀式:執照翻面/鋼印,參照之前登入過場的鋼印動效)
- 純 CSS 分享卡(Canvas 拍立得照片版之後做,但**版面先預留照片位置**避免之後重排)
- 回酒館 / 看圖鑑入口

**成功標準**:接令→完成→EXP入帳→寫入hunts→等級正確更新;二刷×0.3、隱藏名店×2正確;重複點擊不會灌兩次EXP;升級時有儀式反饋。

---

## 任務 2 — 遠征選區頁 `/expedition`

- 台南 37 區清單(資料已在 `app/tainan_districts.py`),做成可點選的格狀/列表
- 點一區 → 導向 `/board?mode=expedition&district=<區>`
- 視覺對齊酒館木質風(像「攤開一張羊皮紙地圖」),**別做成白底下拉選單**
- (可選加分)各區旁顯示該區已討伐數,呼應地區制霸動機

---

## 任務 3 — 基本圖鑑 `/dex`(先求能用,別過度設計)

MVP 版先做核心,華麗收集設計之後再加:
- 已討伐店家清單(店名、分級、自評星、討伐日期),可依區分組
- 區域稱號進度(各區討伐數 + 距下一稱號:10次地頭蛇/25次制霸者 的進度條)
- 視覺對齊木質風
- **先不做**:未獵店家剪影、3D 圖鑑效果這類(留待二哥後續設計)

---

## 任務 4 — 三店主切換 + 大圖背景

**檔案**:`tavern_keeper_switch_demo.html`(視覺參照)

**立繪**:富毅會提供三張像素店主圖(憨厚大叔/陽光帥哥/紅衣女主人),放進 `static/`,檔名如 `keeper_dad.png`/`keeper_hunk.png`/`keeper_lady.png`。

**做法**(參照 demo):
- 店主圖當酒館**全幅背景大圖**(`background-size:cover`)
- **下半部疊由下往上的暗色漸層**(`.scrim`),讓 UI 沉在下方、人物臉部在上方露出
- UI(對話框/執照/搜索鈕)排在下半部,避開人物臉
- 右上角「⟳ 換店主」鈕,切換背景圖 + 對應台詞 + NPC 稱呼
- 選的店主存 `users` 表(加一欄 `keeper_id TEXT DEFAULT 'dad'`),跨 session 記住
- 每位店主有專屬台詞組(demo 裡有範例文案,可沿用),依時段+隨機挑一句

**注意**:demo 用色塊佔位代表立繪,真實版換成 `background-image:url(...)`。台詞 demo 裡寫好了三套人設(大叔豪邁/帥哥殷勤/女主人神祕),可直接用。

---

## 不要動

- 後端四態、Haversine、EXP 公式、種子抽取、is_open_now、schema 既有欄位 → 正確,別重構
- 已完成的酒館/懸賞板/登入動畫 → 別動
- 刻意設計:C=60、二刷×0.3、隱藏名店×2、等級不存欄位 → 保留

每件做完跑起來確認、手機 390px 不破版、reduced-motion 動畫停用,再下一件。
