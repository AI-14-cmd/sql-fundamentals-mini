-- Swim Meet Performance & Relay Eligibility Analyzer
-- Runs on top of the swimmers and results tables from the sample data.
-- Pipeline: check the raw data -> clean it -> rank it -> aggregate it.
-- Every statement that starts with a "-- REPORT:" line is a report
-- the runner prints with that title.

-- =====================================================================
-- STEP 0: Data quality checks on the RAW results table.
-- We look before we clean, so problems are reported, not silently hidden.
-- =====================================================================

-- REPORT: Data quality - results with a NULL time
-- "= NULL" is never true, so a NULL check must use IS NULL.
SELECT swimmer_id, event, lane
FROM results
WHERE time_seconds IS NULL
ORDER BY event, swimmer_id;

-- REPORT: Data quality - duplicate (swimmer_id, event) pairs
-- Group by the pair that should be unique; any group bigger than 1 is a duplicate.
SELECT swimmer_id, event, COUNT(*) AS entry_count
FROM results
GROUP BY swimmer_id, event
HAVING COUNT(*) > 1
ORDER BY event, swimmer_id;

-- REPORT: Data quality - times of zero or less
-- A race cannot take zero or negative seconds: these are timing errors.
SELECT swimmer_id, event, time_seconds
FROM results
WHERE time_seconds <= 0
ORDER BY event, swimmer_id;

-- =====================================================================
-- STEP 1: The clean results, saved as a view so every later step
-- starts from the same cleaned rows.
--   * INNER JOIN keeps only results whose swimmer exists (drops id 99)
--   * IS NOT NULL drops the missing times
--   * > 0 drops the timing errors (and avoids dividing by zero)
--   * speed_rating = 100 / time; 100.0 forces decimal division
-- =====================================================================
DROP VIEW IF EXISTS ranked_results;
DROP VIEW IF EXISTS clean_results;

CREATE VIEW clean_results AS
SELECT
    s.swimmer_id,
    s.name,
    s.age,
    s.team,
    r.event,
    r.time_seconds,
    r.lane,
    ROUND(100.0 / r.time_seconds, 2) AS speed_rating
FROM results AS r
INNER JOIN swimmers AS s
    ON s.swimmer_id = r.swimmer_id
WHERE r.time_seconds IS NOT NULL
  AND r.time_seconds > 0;

-- REPORT: 1. Clean performance report
SELECT swimmer_id, name, age, team, event, time_seconds, lane, speed_rating
FROM clean_results
ORDER BY event, time_seconds, name;

-- =====================================================================
-- STEP 2: Rank swimmers within each event, fastest first.
--   best_times (CTE) keeps one time per swimmer per event, their fastest,
--   so a swimmer who swam twice cannot take two podium places.
--   RANK() OVER (PARTITION BY event ...) restarts the count for each event;
--   equal times share a rank and the next rank is skipped (1, 2, 2, 4).
-- =====================================================================
CREATE VIEW ranked_results AS
WITH best_times AS (
    SELECT swimmer_id, name, event, MIN(time_seconds) AS time_seconds
    FROM clean_results
    GROUP BY swimmer_id, name, event
)
SELECT
    swimmer_id,
    name,
    event,
    time_seconds,
    ROUND(100.0 / time_seconds, 2) AS speed_rating,
    RANK() OVER (PARTITION BY event ORDER BY time_seconds) AS rank
FROM best_times;

-- REPORT: 2. Top 3 swimmers per event
-- A window function cannot sit in WHERE, so we filter the ranked view instead.
SELECT name, event, time_seconds, rank
FROM ranked_results
WHERE rank <= 3
ORDER BY event, rank, name;

-- =====================================================================
-- STEP 3: Relay eligibility. Count each swimmer's valid results and
-- keep only swimmers with at least 2.
--   WHERE filters rows BEFORE grouping; HAVING filters groups AFTER.
--   "time_seconds > 0" is unknown (not true) for NULL, so NULL times
--   and timing errors are both left out; COUNT(time_seconds) also skips NULLs.
--   The INNER JOIN leaves out swimmer 99, who is not a club member.
-- =====================================================================

-- REPORT: 3. Relay eligibility (at least 2 valid results)
SELECT s.name, COUNT(r.time_seconds) AS result_count
FROM swimmers AS s
INNER JOIN results AS r
    ON r.swimmer_id = s.swimmer_id
WHERE r.time_seconds > 0
GROUP BY s.swimmer_id, s.name
HAVING COUNT(r.time_seconds) >= 2
ORDER BY s.name;

-- =====================================================================
-- STEP 4: The final cleaned results, sorted by event and rank.
-- =====================================================================

-- REPORT: Final cleaned results by event and rank
SELECT event, rank, name, time_seconds, speed_rating
FROM ranked_results
ORDER BY event, rank, name;