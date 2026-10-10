-- Dolphin Swim Club: sample data from the recent swim meet.
-- Load this file first, then run the analysis script on top of it.
-- The data is deliberately messy so the quality checks have something to find:
--   * three results with no time (NULL)
--   * one swimmer who swam the 100 Free twice (duplicate swimmer_id + event)
--   * two impossible times (0 and a negative number)
--   * two results for swimmer 99, who is not in the swimmers table

-- Start from a clean slate so the file can be loaded more than once.
DROP TABLE IF EXISTS results;
DROP TABLE IF EXISTS swimmers;

-- One row per club member.
CREATE TABLE swimmers (
    swimmer_id INTEGER PRIMARY KEY,
    name       VARCHAR(50) NOT NULL,
    age        INTEGER,
    team       VARCHAR(20)
);

-- One row per swim. No foreign key on purpose: the timing system
-- sometimes records a swimmer_id the club does not know about.
CREATE TABLE results (
    swimmer_id   INTEGER,
    event        VARCHAR(20),
    time_seconds DECIMAL(6, 2),
    lane         INTEGER
);

INSERT INTO swimmers (swimmer_id, name, age, team) VALUES
    (1, 'Ava Chen',    14, 'Blue'),
    (2, 'Ben Ortiz',   15, 'Gold'),
    (3, 'Chloe Park',  14, 'Blue'),
    (4, 'Dev Patel',   16, 'Gold'),
    (5, 'Emma Novak',  15, 'Blue'),
    (6, 'Finn Walsh',  13, 'Gold'),
    (7, 'Grace Liu',   12, 'Blue');

INSERT INTO results (swimmer_id, event, time_seconds, lane) VALUES
    -- 50 Free
    (1,  '50 Free',  27.90, 3),
    (2,  '50 Free',  27.10, 4),
    (3,  '50 Free',  29.10, 5),
    (4,  '50 Free',  27.90, 2),
    (5,  '50 Free',  NULL,  6),
    (99, '50 Free',  26.50, 1),
    -- 100 Free
    (1,  '100 Free', 61.20, 4),
    (2,  '100 Free', 0,     5),
    (3,  '100 Free', 60.50, 3),
    (3,  '100 Free', 60.10, 3),
    (5,  '100 Free', 59.80, 2),
    (6,  '100 Free', NULL,  6),
    -- 50 Back
    (1,  '50 Back',  NULL,  2),
    (2,  '50 Back',  -32.00, 3),
    (4,  '50 Back',  33.75, 5),
    (5,  '50 Back',  32.05, 4),
    (6,  '50 Back',  31.40, 1),
    (99, '50 Back',  30.00, 6);