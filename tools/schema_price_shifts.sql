-- View: Price Shifts — tracks price changes between consecutive scrapes for the same flight
-- Run this in the Supabase SQL Editor

CREATE OR REPLACE VIEW vw_price_shifts AS
SELECT 
    route,
    days_before_flight AS days_before,
    price_change,
    ABS(price_change) AS abs_change,
    price
FROM (
    SELECT 
        route,
        flight_date,
        days_before_flight,
        departure_time,
        price,
        price - LAG(price) OVER (
            PARTITION BY route, flight_date, departure_time 
            ORDER BY scrape_datetime
        ) AS price_change
    FROM flight_prices
    WHERE price IS NOT NULL
) sub
WHERE price_change IS NOT NULL AND price_change != 0;
