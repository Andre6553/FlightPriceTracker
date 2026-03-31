-- View: Price Shifts — added temporal flag
DROP VIEW IF EXISTS vw_price_shifts;
CREATE VIEW vw_price_shifts AS
SELECT 
    route,
    flight_date,
    departure_time,
    days_before_flight AS days_before,
    CASE WHEN flight_date >= CURRENT_DATE THEN 'Future' ELSE 'Past' END as period,
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
