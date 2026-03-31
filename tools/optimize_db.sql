-- ============================================
-- 🚀 FlySafair Tracker - Database Performance Kit 
-- ============================================
-- Run this in your Supabase SQL Editor to speed up your dashboard.

-- 1. Create Indexes (This makes searching for prices 10-100x faster)
CREATE INDEX IF NOT EXISTS idx_fp_route ON flight_prices(route);
CREATE INDEX IF NOT EXISTS idx_fp_flight_date ON flight_prices(flight_date);
CREATE INDEX IF NOT EXISTS idx_fp_scrape_datetime ON flight_prices(scrape_datetime);

-- 2. Fast Metadata View (Instant dashboard stats)
-- This replaces the slow looping and multiple requests in the dashboard.
DROP VIEW IF EXISTS vw_dashboard_meta;
CREATE VIEW vw_dashboard_meta AS
SELECT 
    MAX(scrape_datetime) as last_scrape,
    COUNT(DISTINCT scrape_datetime) as total_checks,
    COUNT(*) as total_rows
FROM flight_prices;

-- Hint: After running this, your dashboard will load significantly faster!
