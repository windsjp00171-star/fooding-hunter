-- Store preferred tavern keeper per user
ALTER TABLE users ADD COLUMN IF NOT EXISTS keeper_id TEXT DEFAULT 'dad';
