# 美食獵人執照 (Food Hunter License) — CLAUDE.md

## 專案定位
單機美食狩獵 RPG。走進酒館 → 搜索此地 → 取懸賞令 → 討伐（吃）→ 升級執照。
完整規格見 `food-hunter-license-handoff-v3.md`（在 Claude.ai 對話中提供）。

## 開發規則（Rule 摘要）

- **Rule 1 先想再寫**：改任何邏輯前先說明思路，等確認再動手
- **Rule 2 簡單優先**：三行能解決的不要抽 helper
- **Rule 3 只動該動的**：修 A 不動 B，除非 B 是 A 的直接依賴
- **Rule 5 schema 先行**：先建表再寫程式（已完成）
- **Rule 6 衝突浮上來講**：規格有矛盾先說，不要默默平均
- **Rule 7 失敗要大聲**：跑不過、打不通、API 報錯，直說，不假裝完成
- **Rule 10 每步 checkpoint**：每個功能做完就停，等確認再往下
- **Rule 13 Session Snapshot**：每次 session 結束輸出快照（完成項、待辦、阻塞）

## 明確不做（冷凍庫）
- 玩家互動（好友/排行/留言）
- 地圖任意落點（遠征僅選行政區清單）
- 照片上傳伺服器
- GPS 到店驗證
- LLM 生成文字
- PostGIS（網格 + Haversine 足夠）
- 被動技能 perk / 技能點（Phase 2）
- 推播 / PWA 離線功能（manifest+icon 除外）

## 刻意設計（不要「修正」）
- C 級賞金最高（C=60）：高風險高報酬，笑點設計
- 二刷同店 ×0.3（不是 bug）
- 隱藏名店 ×2（rating≥4.5 且 rating_count<100）
- 等級不存欄位，由 `hunts.exp_gained` SUM 即時算
- 7 天內同店不再抽出（冷卻），懸賞板若出現曾討伐店以「已討伐」樣式呈現（不消失）

## 架構重點
- 後端：Flask + Jinja2（行動優先，390px 第一設計目標）
- 資料庫：Supabase (Postgres)，後端走 `service_role` key
- 店家來源抽象：`shops.source IN ('places_api', 'manual')`，兩者共用同一張表
- 分享卡：前端 Canvas 合成，照片全程不上傳
- PWA-lite：manifest.json + icon，不做 service worker

## Schema 說明

| 表 | 重點 |
|---|---|
| `users` | id = LINE user_id；reroll_used_today + reroll_reset_date 管每日重抽配額 |
| `shops` | place_id unique（可 upsert）；cell_id 索引；opening_hours JSONB；source 欄位供切換 |
| `fetch_log` | 以 cell_id + expires_at 判斷是否需要重打 API（30 天 TTL）|
| `bounties` | mode（explore/expedition）+ origin_key（cell_id/district）；種子 = user+date+origin |
| `hunts` | exp_gained 含所有倍率計算後的值；district 快照供稱號統計 |

## EXP 計算公式
```
base = S:50 / A:40 / B:30 / C:60
is_hidden_gem = (rating >= 4.5 AND rating_count < 100)
visit_count = hunts WHERE user_id=? AND shop_id=?
multiplier = (2 if is_hidden_gem else 1) * (0.3 if visit_count >= 1 else 1)
exp_gained = round(base * multiplier)
```

## 等級門檻
```
0    → 見習獵人     (reroll/day: 1)
300  → 青銅獵人     (reroll/day: 2)
800  → 白銀獵人     (reroll/day: 3)
1600 → 黃金獵人     (reroll/day: 4)
3000 → 美食獵人     (reroll/day: 5)
5000 → 傳說級獵人   (reroll/day: 6)
```

## 區域稱號
- 同 district 累計 10 次討伐 → 「○○區地頭蛇」
- 同 district 累計 25 次討伐 → 「○○區制霸者」
- district = null 的 hunts 不計入稱號

## 技術備忘
- Supabase 查單筆用 `fetch_one(query)`（app/supabase_client.py），**不要用 `maybe_single()`**：某些 supabase-py 版本在 0 筆時回 HTTP 406 並丟例外，會把「查無資料」變成 500（曾導致所有新用戶登入 500）
- 改 schema 後需 reload PostgREST schema cache
- Places API 欄位回應可能為 None，務必防呆
- Geolocation 需 HTTPS（本機 localhost 例外，或用 ngrok）
- Render 冷啟動：首訪等待約 30 秒，列為觀察項

## 當前進度
- [x] Schema migration SQL (`migrations/001_initial_schema.sql`)
- [ ] Supabase 專案建立（等使用者）
- [ ] Migration 套用到 Supabase
- [ ] 假資料驗證 CRUD
- [ ] Flask app 骨架
