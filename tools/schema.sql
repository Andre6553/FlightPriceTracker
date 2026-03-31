-- SQL Migration: Add 'period' column to all views for temporal filtering (Past vs Future flights)

-- View 1: Booking Window Breakdown
DROP VIEW IF EXISTS vw_booking_window;
CREATE VIEW vw_booking_window AS
SELECT 
    route, 
    days_before_flight AS days_before, 
    CASE WHEN flight_date >= CURRENT_DATE THEN 'Future' ELSE 'Past' END as period,
    AVG(price) AS avg_price, 
    MIN(price) AS min_price, 
    COUNT(*) AS data_points
FROM flight_prices 
GROUP BY route, days_before_flight, period;

-- View 2: Best Day of Week to Fly
DROP VIEW IF EXISTS vw_day_fly;
CREATE VIEW vw_day_fly AS
SELECT 
    route,
    EXTRACT(DOW FROM flight_date) AS day_of_week_num,
    TO_CHAR(flight_date, 'Day') AS day_name,
    CASE WHEN flight_date >= CURRENT_DATE THEN 'Future' ELSE 'Past' END as period,
    AVG(price) AS avg_price
FROM flight_prices
GROUP BY route, EXTRACT(DOW FROM flight_date), TO_CHAR(flight_date, 'Day'), period;

-- View 3: Best Hour to Book
DROP VIEW IF EXISTS vw_hour_book;
CREATE VIEW vw_hour_book AS
SELECT 
    route,
    EXTRACT(HOUR FROM scrape_datetime) AS hour_num,
    CASE WHEN flight_date >= CURRENT_DATE THEN 'Future' ELSE 'Past' END as period,
    AVG(price) AS avg_price
FROM flight_prices
GROUP BY route, EXTRACT(HOUR FROM scrape_datetime), period;

-- View 4: Best Day of Week to Book
DROP VIEW IF EXISTS vw_day_book;
CREATE VIEW vw_day_book AS
SELECT 
    route,
    EXTRACT(DOW FROM scrape_datetime) AS day_of_week_num,
    TO_CHAR(scrape_datetime, 'Day') AS day_name,
    CASE WHEN flight_date >= CURRENT_DATE THEN 'Future' ELSE 'Past' END as period,
    AVG(price) AS avg_price
FROM flight_prices
GROUP BY route, EXTRACT(DOW FROM scrape_datetime), TO_CHAR(scrape_datetime, 'Day'), period;

-- View 5: Route statistics
DROP VIEW IF EXISTS vw_route_stats;
CREATE VIEW vw_route_stats AS
SELECT 
    route,
    CASE WHEN flight_date >= CURRENT_DATE THEN 'Future' ELSE 'Past' END as period,
    AVG(price) AS avg_price,
    MIN(price) AS min_price,
    MAX(price) AS max_price,
    COUNT(*) AS total_points
FROM flight_prices
GROUP BY route, period;

-- View 6: Price Heatmap
DROP VIEW IF EXISTS vw_price_heatmap;
CREATE VIEW vw_price_heatmap AS
SELECT 
    route,
    EXTRACT(HOUR FROM scrape_datetime) AS hour_num,
    days_before_flight AS days_before,
    CASE WHEN flight_date >= CURRENT_DATE THEN 'Future' ELSE 'Past' END as period,
    AVG(price) AS avg_price
FROM flight_prices
GROUP BY route, EXTRACT(HOUR FROM scrape_datetime), days_before_flight, period;
