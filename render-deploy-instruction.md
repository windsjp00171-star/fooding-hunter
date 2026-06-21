# 給大哥(Claude Code)的指令 — Render 部署 + 免費保溫

> 來自 chat(二哥)。v1.0 自檢過後的部署步驟。平台續用 Render 免費版 + 土炮保溫,人氣起來再升級付費。

## 平台決策
- **續用 Render**(不搬家,環境零改動)
- **先用免費版 + 外部 cron 保溫**(避免冷啟動白屏,又不付費)
- 富毅 Render 上專案多,不無差別付費;等這個 app 真有人氣、冷啟動明顯傷體驗,再單獨升級這一個 service 到 Starter($7/月)

## 部署步驟

1. **部署到 Render**(Flask web service)
   - requirements.txt 確認有 `gunicorn`
   - Start command 用 gunicorn(如 `gunicorn wsgi:app`)
   - Python 版本、build/start command 設好
   - 環境變數全部設上去(Supabase、Google Places、LINE、FLASK_SECRET_KEY 等,參照 `.env.example`)
   - `FLASK_ENV=production`

2. **拿到 Render 正式網址後**(這步需要富毅操作)
   - 回 LINE Developers 後台,把 callback URL 從 localhost 改成 `https://<render網址>/callback`
   - 確認 LINE channel 的 callback 設定存檔

3. **土炮保溫(免費防冷啟動)**
   - 加一個極輕量的健康檢查路由,如 `GET /ping` → 回 200 + "ok"(不查 DB、不打 API,純回應,避免浪費資源)
   - 富毅去 cron-job.org(免費)設一個排程:每 10 分鐘打一次 `https://<render網址>/ping`
   - 這樣服務不會閒置休眠,避免玩家遇到 30-60 秒冷啟動
   - ⚠ 註:常駐會吃 Render 免費的 750 instance hours/月,單一服務剛好用滿。若哪天額度不夠或冷啟動仍明顯 → 升級 Starter $7/月

4. **首訪載入提示(保險)**
   - 即使有保溫,萬一保溫失效或首次部署,加一個簡單的載入畫面/spinner,別讓玩家看到白屏

## 驗收
- Render 網址可正常開啟,LINE 登入全流程通過(用手機實測,非 localhost)
- `/ping` 回 200
- cron 設好後,隔一段時間(>15分)再訪,不需等待 30 秒(保溫生效)
- 所有環境變數正確,Places API / Supabase / LINE 都連得上

## 提醒富毅本人要做的
- LINE callback URL 改正式網址(步驟 2)
- cron-job.org 設保溫排程(步驟 3)
- GCP 保險絲已設(已確認)
