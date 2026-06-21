-- =============================================================
-- 美食獵人執照 (Food Hunter License) — Initial Schema
-- v3.4 spec
-- =============================================================
-- 設計備忘：
--   * level / title 不存欄位，由 hunts.exp_gained SUM 即時算
--   * district 由 Flask 層 regex 從 address 解出，失敗存 null
--   * 時區顯示一律 Asia/Taipei（應用層轉換，DB 存 TIMESTAMPTZ UTC）
--   * 所有後端操作走 service_role key，Flask 層負責存取控管
--   * opening_hours JSONB = Places API regularOpeningHours 原始結構
--   * shops.source 讓店家池可切換（Places API / 手動 JSON 皆可灌入）
-- =============================================================

-- -------------------------------------------------------
-- 1. users
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id                TEXT PRIMARY KEY,          -- LINE user_id
  display_name      TEXT NOT NULL,
  picture_url       TEXT,
  reroll_used_today INT  NOT NULL DEFAULT 0,
  reroll_reset_date DATE,                      -- 用來判斷是否跨日 reset
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -------------------------------------------------------
-- 2. shops  (全體共用快取，不屬於任何 user)
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS shops (
  id                        UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  place_id                  TEXT    UNIQUE NOT NULL,   -- Places API place_id 或 manual_<slug>
  name                      TEXT    NOT NULL,
  address                   TEXT,
  district                  TEXT,                      -- 解析自 address，例：「中西區」；null = 解析失敗
  lat                       DOUBLE PRECISION NOT NULL,
  lng                       DOUBLE PRECISION NOT NULL,
  rating                    NUMERIC(3,1),              -- Google rating，null = 無評分
  rating_count              INT,                       -- 評論數，用於隱藏名店判斷（≥4.5 且 <100）
  cell_id                   TEXT    NOT NULL,          -- f"{round(lat,2)}_{round(lng,2)}" 約 1km 網格
  opening_hours             JSONB,                     -- Places API regularOpeningHours 原始結構
  opening_hours_fetched_at  TIMESTAMPTZ,               -- 超 30 天需補打 Place Details
  source                    TEXT    NOT NULL DEFAULT 'places_api'
                              CHECK (source IN ('places_api', 'manual')),
  created_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at                TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_shops_cell_id  ON shops(cell_id);
CREATE INDEX IF NOT EXISTS idx_shops_place_id ON shops(place_id);  -- upsert 用

-- -------------------------------------------------------
-- 3. fetch_log  (網格快取紀錄，全體共用)
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS fetch_log (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  cell_id     TEXT        NOT NULL,
  fetched_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  shop_count  INT,                                     -- 本次抓回幾間
  expires_at  TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '30 days'
);

CREATE INDEX IF NOT EXISTS idx_fetch_log_cell_id    ON fetch_log(cell_id);
CREATE INDEX IF NOT EXISTS idx_fetch_log_expires_at ON fetch_log(expires_at);

-- -------------------------------------------------------
-- 4. bounties  (每位玩家每日每來源的懸賞令)
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS bounties (
  id           UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      TEXT    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  shop_id      UUID    NOT NULL REFERENCES shops(id),
  mode         TEXT    NOT NULL CHECK (mode IN ('explore', 'expedition')),
  -- explore  → origin_key = cell_id（如 "22.99_120.20"）
  -- expedition → origin_key = district name（如 "中西區"）
  origin_key   TEXT    NOT NULL,
  grade        TEXT    NOT NULL CHECK (grade IN ('S', 'A', 'B', 'C')),
  base_reward  INT     NOT NULL,   -- S=50 A=40 B=30 C=60（C 最高為刻意設計）
  is_hidden_gem BOOLEAN NOT NULL DEFAULT FALSE,   -- rating≥4.5 且 rating_count<100 → 賞金×2
  bounty_date  DATE    NOT NULL DEFAULT CURRENT_DATE,
  status       TEXT    NOT NULL DEFAULT 'active'
                 CHECK (status IN ('active', 'completed', 'expired')),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bounties_user_id          ON bounties(user_id);
-- 同玩家同日同來源懸賞固定（種子 = user_id + date + origin_key）
CREATE INDEX IF NOT EXISTS idx_bounties_user_date_origin ON bounties(user_id, bounty_date, origin_key);

-- -------------------------------------------------------
-- 5. hunts  (討伐紀錄，EXP 由此 SUM 算等級)
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS hunts (
  id            UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       TEXT    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  shop_id       UUID    NOT NULL REFERENCES shops(id),
  bounty_id     UUID    REFERENCES bounties(id),   -- nullable：理論上都有，保留防呆
  exp_gained    INT     NOT NULL,                  -- 實際入帳 EXP（含×2/×0.3 計算後）
  player_rating INT     CHECK (player_rating BETWEEN 1 AND 5),
  review_text   TEXT,                              -- 短評，僅本人可見（Flask 層存取控管）
  district      TEXT,                              -- 快照 district（供稱號統計，允許 null）
  completed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hunts_user_id       ON hunts(user_id);
CREATE INDEX IF NOT EXISTS idx_hunts_user_shop     ON hunts(user_id, shop_id);   -- 7天冷卻 / 二刷判斷
CREATE INDEX IF NOT EXISTS idx_hunts_user_district ON hunts(user_id, district);  -- 稱號統計

-- -------------------------------------------------------
-- 6. updated_at 自動更新 trigger（僅 users / shops 需要）
-- -------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER trg_users_updated_at
  BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE TRIGGER trg_shops_updated_at
  BEFORE UPDATE ON shops
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- -------------------------------------------------------
-- 7. PostgREST schema cache reload（執行完 migration 後需手動在 Supabase 觸發）
-- 提醒：Supabase Dashboard → Settings → API → Reload schema
-- 或透過 MCP apply_migration 後自動觸發
-- -------------------------------------------------------
