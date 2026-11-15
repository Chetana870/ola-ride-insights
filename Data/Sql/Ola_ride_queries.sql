-- PostgreSQL. Table: ola_rides (loaded from ola_clean.csv)

-- Table definition
CREATE TABLE IF NOT EXISTS ola_rides (
    booking_id              VARCHAR(20) PRIMARY KEY,
    booking_status          VARCHAR(30),
    customer_id             VARCHAR(15),
    vehicle_type            VARCHAR(20),
    pickup_location         VARCHAR(60),
    drop_location           VARCHAR(60),
    v_tat                   NUMERIC,
    c_tat                   NUMERIC,
    cancel_reason_customer  VARCHAR(60),
    cancel_reason_driver    VARCHAR(60),
    is_incomplete           VARCHAR(3),
    incomplete_reason       VARCHAR(40),
    booking_value           INT,
    payment_method          VARCHAR(20),
    ride_distance           INT,
    driver_ratings          NUMERIC(2,1),
    customer_rating         NUMERIC(2,1),
    booking_datetime        TIMESTAMP,
    booking_date            DATE,
    hour                    SMALLINT,
    day_of_week             VARCHAR(10),
    day                     SMALLINT,
    time_of_day             VARCHAR(12),
    is_success              SMALLINT,
    is_completed            SMALLINT
);
-- Load:  \copy ola_rides FROM 'ola_clean.csv' CSV HEADER

-- Q1. All successful bookings
SELECT * FROM ola_rides WHERE booking_status = 'Success';

-- Q2. Average ride distance per vehicle type (successful rides only; cancelled rides have distance 0)
SELECT vehicle_type, ROUND(AVG(ride_distance), 2) AS avg_distance_km
FROM ola_rides
WHERE booking_status = 'Success'
GROUP BY vehicle_type
ORDER BY avg_distance_km DESC;

-- Q3. Total rides cancelled by customers
SELECT COUNT(*) AS cancelled_by_customers
FROM ola_rides WHERE booking_status = 'Canceled by Customer';

-- Q4. Top 5 customers by number of rides (ties at the cut-off are possible -> add a tie-breaker)
SELECT customer_id, COUNT(*) AS total_rides
FROM ola_rides
GROUP BY customer_id
ORDER BY total_rides DESC, customer_id
LIMIT 5;

-- Q5. Rides cancelled by drivers for personal & car-related issues
SELECT COUNT(*) AS driver_cancel_personal_car
FROM ola_rides
WHERE booking_status = 'Canceled by Driver'
  AND cancel_reason_driver = 'Personal & Car related issue';

-- Q6. Max and min driver rating for Prime Sedan
SELECT MAX(driver_ratings) AS max_rating, MIN(driver_ratings) AS min_rating
FROM ola_rides
WHERE vehicle_type = 'Prime Sedan' AND driver_ratings IS NOT NULL;

-- Q7. Rides paid via UPI
SELECT * FROM ola_rides WHERE payment_method = 'UPI';

-- Q8. Average customer rating per vehicle type
SELECT vehicle_type, ROUND(AVG(customer_rating), 2) AS avg_customer_rating
FROM ola_rides
WHERE customer_rating IS NOT NULL
GROUP BY vehicle_type
ORDER BY avg_customer_rating DESC;

-- Q9. Total booking value of successfully completed rides
SELECT SUM(booking_value) AS total_booking_value
FROM ola_rides
WHERE booking_status = 'Success';
-- Stricter version (excludes rides flagged incomplete):
-- ... WHERE booking_status = 'Success' AND is_incomplete = 'No';

-- Q10. Incomplete rides with reason
SELECT booking_id, customer_id, vehicle_type, incomplete_reason
FROM ola_rides
WHERE is_incomplete = 'Yes';

