-- vw_calendar_prices: Shows the cheapest current price for each route + date
-- Uses flight_details (deep scrape) when available, falls back to flight_prices (grid scrape)

CREATE OR REPLACE VIEW vw_calendar_prices AS

-- Part 1: Deep scrape data (flight_details) - most accurate
WITH detail_latest AS (
    SELECT route, flight_date, MAX(scrape_datetime) AS max_scrape
    FROM flight_details
    GROUP BY route, flight_date
),
detail_prices AS (
    SELECT fd.route, fd.flight_date, MIN(fd.price) AS cheapest_price
    FROM flight_details fd
    INNER JOIN detail_latest dl
        ON fd.route = dl.route
        AND fd.flight_date = dl.flight_date
        AND fd.scrape_datetime >= dl.max_scrape::timestamp - INTERVAL '15 minutes'
    GROUP BY fd.route, fd.flight_date
),

-- Part 2: Grid scrape data (flight_prices) - fallback for days without deep scrape
grid_latest AS (
    SELECT route, flight_date, MAX(scrape_datetime) AS max_scrape
    FROM flight_prices
    GROUP BY route, flight_date
),
grid_prices AS (
    SELECT fp.route, fp.flight_date, fp.price AS cheapest_price
    FROM flight_prices fp
    INNER JOIN grid_latest gl
        ON fp.route = gl.route
        AND fp.flight_date = gl.flight_date
        AND fp.scrape_datetime = gl.max_scrape
)

-- Combine: prefer deep scrape, fall back to grid
SELECT 
    COALESCE(dp.route, gp.route) AS route,
    COALESCE(dp.flight_date, gp.flight_date) AS flight_date,
    COALESCE(dp.cheapest_price, gp.cheapest_price) AS cheapest_price
FROM grid_prices gp
FULL OUTER JOIN detail_prices dp
    ON gp.route = dp.route AND gp.flight_date = dp.flight_date;
