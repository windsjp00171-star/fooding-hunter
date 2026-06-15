# 給大哥(Claude Code)的整合指令 — 第二輪視覺強化

> 來自 chat(二哥)。共四件事,可依序做,每件做完 checkpoint 再下一件(Rule 10)。
> 檔案都在 repo 同層。標「視覺參照」的**不要覆蓋**進專案,是給你抄樣式的;標「程式」的才放進 app/。

---

## 任務 1 — 🗺 地圖按鈕(優先,這是漏掉的核心功能)

**問題**:目前懸賞卡只有「接令 →」進詳情頁,但沒有「直接開 Google Maps 導航去這間店」的入口。美食獵人的核心動作就是真的走過去吃,不能少這個。

**做法**:純 URL,**不打任何 API、零成本**。`shops.place_id` 已經存著,直接組連結:

```
https://www.google.com/maps/search/?api=1&query={URL編碼的店名}&query_place_id={place_id}
```

**放哪**:
- 懸賞詳情頁 `/bounty/<shop_id>` 放一個明顯的「🗺 出發討伐(開地圖)」按鈕
- (可選)懸賞卡上也放一個小地圖 icon,讓人不進詳情也能直接導航

**注意**:用 `target="_blank" rel="noopener"` 開新分頁;店名記得 URL 編碼(Jinja 的 `| urlencode`)。

---

## 任務 2 — ✨ 風味文案 + 懸賞板動畫

**檔案**:
- `flavor.py`(**程式**)→ 放進 `app/flavor.py`
- `board_flavor_anim_demo.html`(**視覺參照**)→ 抄動畫,不覆蓋

**2a. 接風味文案**:
```python
from app.flavor import make_flavor
flavor = make_flavor(shop, grade, is_hidden_gem)  # → {quest_title, quest_desc, monster_tag}
```
在 `board.py` 組懸賞 dict 時呼叫,把 `flavor` 塞進每個 bounty,讓 `board.html` 能用 `b.flavor.quest_title` 等。

**前置確認**:`flavor.py` 靠 `shop.cuisine` 判斷類型。請確認抓 Places API 時有把 `shops.cuisine` 從 Places `types` 映射成中文(「咖啡」「麵食」「便當」「火鍋」「日式」「燒烤」「甜點」「早午餐」「小吃」)。若沒做,請補;cuisine 為 None 會 fallback 到「無名魔物」(可用但無針對性)。

**2b. 卡片版面改成**(參照 demo):委託標題(大,RPG)→ 店名(小,附註)→ 風味敘述(斜體左側線)→ 地點 → 分隔線 → 賞金/接令。店名保留但縮小,不當主標題。

**2c. 動畫**(參照 demo,全包進 `@media (prefers-reduced-motion:reduce)` 停用):
- 懸賞令入場:一張張從上「釘落」帶回彈(`pin-drop` + stagger delay)
- S 級火漆章金光呼吸 + S 級賞金數字發光
- 隱藏名店 ×2 標籤輕微搖晃
- 接令鈕 hover 掃光

---

## 任務 3 — 🪵 實體木頭告示板外框

**檔案**:`notice_board_frame_demo.html`(**視覺參照**)→ 抄外框,不覆蓋

**做什麼**:現在懸賞令是直接釘在木紋背景上,缺「一塊獨立告示板」的層次。請把所有懸賞令用一個 `.notice-board` 容器框起來,讓它變成「掛在牆上的公會告示板」。

**參照 demo 的關鍵構造**:
- 厚木框(`border-image` 漸層做立體木邊)
- 四角大鉚釘(`.rivet`)
- 板面內凹陰影 + 板子浮牆投影(`box-shadow` 多層)
- **後牆背景刻意調暗**(demo 把牆調比現在更暗),靠對比讓亮色告示板「跳」出來——這是「明顯」的關鍵
- 板頂「獵人公會・委託」烙印小標

**注意**:四態裡只有 normal/border(有懸賞令)需要這塊板子;sleeping/desolate(眾店皆眠/荒涼)維持原本的空狀態畫面,不套告示板框。

---

## 任務 4 — 🎬 登入動畫 A + B

**檔案**:
- `tavern_door_intro_demo.html`(**視覺參照**)→ A 段「推開門」用這個
- `login_experience_demo.html`(**視覺參照**)→ B 段「核發執照」用這個的後半

**A. 推開酒館門**(改 `login.html`,參照 `tavern_door_intro_demo.html`):
- 開場是關著的雙扇木門(鑲板、鐵環門把、門上招牌)
- 點擊 → 雙扇門 3D 往兩側開啟(`rotateY` 帶景深)→ 門後暖光酒館顯露 → 招牌/副標/LINE 鈕依序浮現
- demo 預設「點擊開門」(儀式感強);若要免點自動開門,script 末有註解可開啟。建議先用點擊版

**B. 核發執照過場**(參照 `login_experience_demo.html` 的後半 `#sceneIssue`,時機要對):
- 過場內容:執照卡飛入 → 名字/等級打上 → **「公會認證」鋼印旋轉砸下** → 「歡迎...」→ 進酒館
- **時機**:B 接在 **LINE callback 驗證成功之後**。完整一條龍:推開門(A)→ 按 LINE 鈕 → LINE OAuth → callback 驗證 → 顯示 B 過場 → 跑完 `window.location='/'` 進酒館
- **新人 vs 老手文案不同**:首次登入(users 表新建 row)顯示「核發執照」;老玩家回訪顯示「歡迎回來,○○獵人」

---

## 不要動(避免手癢)

- 後端四態邏輯、Haversine、EXP 公式、種子抽取、`is_open_now`、schema → 都正確,別重構
- `tavern.html` → 已達標,別動
- 刻意設計:C=60、二刷×0.3、隱藏名店×2、等級不存欄位 → 全部保留

## 建議順序

1(地圖,最有用) → 2(文案+動畫,延續上輪) → 3(告示板框) → 4(登入動畫)

每件做完跑起來確認沒破版、reduced-motion 動畫停用、手機 390px 寬正常,再下一件。
