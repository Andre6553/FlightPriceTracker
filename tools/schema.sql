-- SQL Migration to create materialized views for the flight dashboard

-- View 1: Booking Window Breakdown (Avg price by days before flight per route)
CREATE OR REPLACE VIEW vw_booking_window AS
SELECT 
    route, 
    days_before_flight AS days_before, 
    AVG(price) AS avg_price, 
    MIN(price) AS min_price, 
    COUNT(*) AS data_points
FROM flight_prices 
GROUP BY route, days_before_flight;

-- View 2: Best Day of Week to Fly
CREATE OR REPLACE VIEW vw_day_fly AS
SELECT 
    route,
    EXTRACT(DOW FROM flight_date) AS day_of_week_num,
    TO_CHAR(flight_date, 'Day') AS day_name,
    AVG(price) AS avg_price
FROM flight_prices
GROUP BY route, EXTRACT(DOW FROM flight_date), TO_CHAR(flight_date, 'Day');

-- View 3: Best Hour to Book
CREATE OR REPLACE VIEW vw_hour_book AS
SELECT 
    route,
    EXTRACT(HOUR FROM scrape_datetime) AS hour_num,
    AVG(price) AS avg_price
FROM flight_prices
GROUP BY route, EXTRACT(HOUR FROM scrape_datetime);

-- View 4: Best Day of Week to Book
CREATE OR REPLACE VIEW vw_day_book AS
SELECT 
    route,
    EXTRACT(DOW FROM scrape_datetime) AS day_of_week_num,
    TO_CHAR(scrape_datetime, 'Day') AS day_name,
    AVG(price) AS avg_price
FROM flight_prices
GROUP BY route, EXTRACT(DOW FROM scrape_datetime), TO_CHAR(scrape_datetime, 'Day');

-- View 5: Route Averages (Summary Stats)
CREATE OR REPLACE VIEW vw_route_stats AS
SELECT 
    route,
    AVG(price) AS avg_price,
    MIN(price) AS min_price,
    MAX(price) AS max_price,
    COUNT(*) AS total_points
FROM flight_prices
GROUP BY route;

-- View 6: Price Heatmap (Average price by scrape hour & days before flight)
CREATE OR REPLACE VIEW vw_price_heatmap AS
SELECT 
    route,
    EXTRACT(HOUR FROM scrape_datetime) AS hour_num,
    days_before_flight AS days_before,
    AVG(price) AS avg_price
FROM flight_prices
GROUP BY route, EXTRACT(HOUR FROM scrape_datetime), days_before_flight;

-- View 7: Total Checks & Last Update Meta
-- Note: A regular view here might be slow since it counts the whole table.
-- We will just query max(scrape_datetime) and count(distinct scrape_datetime) from flight_prices instead of making a view for it.
