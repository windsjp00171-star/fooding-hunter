-- Add cuisine column to shops for RPG flavor text mapping
ALTER TABLE shops ADD COLUMN IF NOT EXISTS cuisine TEXT;
