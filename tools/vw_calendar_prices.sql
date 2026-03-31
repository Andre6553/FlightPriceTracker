-- This view returns ONE row per (route, flight_date) with the cheapest price
-- from the MOST RECENT scrape session for that date.
-- It handles the Supabase 1000-row default limit problem by doing all
-- aggregation server-side.

CREATE OR REPLACE VIEW vw_calendar_prices AS
WITH latest_scrape AS (
    -- For each route + flight_date, find the most recent scrape_datetime
    SELECT route, flight_date, MAX(scrape_datetime) AS max_scrape
    FROM flight_details
    GROUP BY route, flight_date
),
latest_flights AS (
    -- Get all flights from that latest scrape (within 15 min window)
    SELECT fd.route, fd.flight_date, fd.price
    FROM flight_details fd
    INNER JOIN latest_scrape ls
        ON fd.route = ls.route
        AND fd.flight_date = ls.flight_date
        AND fd.scrape_datetime >= ls.max_scrape::timestamp - INTERVAL '15 minutes'
)
-- Return the minimum price per route + date
SELECT route, flight_date, MIN(price) AS cheapest_price
FROM latest_flights
GROUP BY route, flight_date;
