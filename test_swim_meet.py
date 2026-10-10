import os
import sqlite3
import unittest

import run_sql

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = os.path.join(HERE, "sample_data.sql")
ANALYSIS = os.path.join(HERE, "swim_meet_analysis.sql")


def run_all():
    """Run the sample data and the analysis; return {title: (columns, rows)}."""
    reports = run_sql.run_files([SAMPLE, ANALYSIS])
    return {title: (columns, rows) for title, columns, rows in reports}


class DataQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reports = run_all()

    def test_null_times_are_reported(self):
        columns, rows = self.reports["Data quality - results with a NULL time"]
        self.assertEqual(columns, ["swimmer_id", "event", "lane"])
        self.assertEqual(rows, [(6, "100 Free", 6), (1, "50 Back", 2), (5, "50 Free", 6)])

    def test_duplicate_pairs_are_reported(self):
        columns, rows = self.reports["Data quality - duplicate (swimmer_id, event) pairs"]
        self.assertEqual(columns, ["swimmer_id", "event", "entry_count"])
        self.assertEqual(rows, [(3, "100 Free", 2)])

    def test_zero_or_negative_times_are_reported(self):
        columns, rows = self.reports["Data quality - times of zero or less"]
        self.assertEqual(columns, ["swimmer_id", "event", "time_seconds"])
        self.assertEqual(rows, [(2, "100 Free", 0), (2, "50 Back", -32)])


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reports = run_all()

    def test_script_produces_exactly_seven_reports(self):
        self.assertEqual(len(self.reports), 7)

    def test_performance_report_columns(self):
        columns, _ = self.reports["1. Clean performance report"]
        self.assertEqual(columns, ["swimmer_id", "name", "age", "team", "event",
                                   "time_seconds", "lane", "speed_rating"])

    def test_performance_report_drops_bad_rows(self):
        _, rows = self.reports["1. Clean performance report"]
        self.assertEqual(len(rows), 11)
        self.assertNotIn(99, [row[0] for row in rows])  # unknown swimmer
        self.assertTrue(all(row[5] is not None and row[5] > 0 for row in rows))

    def test_performance_report_keeps_both_duplicate_swims(self):
        _, rows = self.reports["1. Clean performance report"]
        chloe_100 = [row[5] for row in rows if row[1] == "Chloe Park" and row[4] == "100 Free"]
        self.assertEqual(chloe_100, [60.1, 60.5])

    def test_speed_rating_is_100_over_time_rounded(self):
        _, rows = self.reports["1. Clean performance report"]
        for row in rows:
            self.assertEqual(row[7], round(100 / row[5], 2))
        self.assertEqual(rows[0][1:], ("Emma Novak", 15, "Blue", "100 Free", 59.8, 2, 1.67))

    def test_top_three_per_event(self):
        columns, rows = self.reports["2. Top 3 swimmers per event"]
        self.assertEqual(columns, ["name", "event", "time_seconds", "rank"])
        self.assertEqual(rows, [
            ("Emma Novak", "100 Free", 59.8, 1),
            ("Chloe Park", "100 Free", 60.1, 2),
            ("Ava Chen", "100 Free", 61.2, 3),
            ("Finn Walsh", "50 Back", 31.4, 1),
            ("Emma Novak", "50 Back", 32.05, 2),
            ("Dev Patel", "50 Back", 33.75, 3),
            ("Ben Ortiz", "50 Free", 27.1, 1),
            ("Ava Chen", "50 Free", 27.9, 2),
            ("Dev Patel", "50 Free", 27.9, 2),
        ])

    def test_swimmer_appears_once_per_event_in_ranking(self):
        _, rows = self.reports["Final cleaned results by event and rank"]
        pairs = [(row[0], row[2]) for row in rows]
        self.assertEqual(len(pairs), len(set(pairs)))

    def test_relay_eligibility(self):
        columns, rows = self.reports["3. Relay eligibility (at least 2 valid results)"]
        self.assertEqual(columns, ["name", "result_count"])
        self.assertEqual(rows, [("Ava Chen", 2), ("Chloe Park", 3),
                                ("Dev Patel", 2), ("Emma Novak", 2)])

    def test_final_results_sorted_by_event_and_rank(self):
        columns, rows = self.reports["Final cleaned results by event and rank"]
        self.assertEqual(columns, ["event", "rank", "name", "time_seconds", "speed_rating"])
        self.assertEqual(len(rows), 10)
        self.assertEqual(rows, sorted(rows, key=lambda r: (r[0], r[1], r[2])))
        # The tie in the 50 Free skips rank 3: 1, 2, 2, 4.
        self.assertEqual([r[1] for r in rows if r[0] == "50 Free"], [1, 2, 2, 4])


class EdgeCaseTests(unittest.TestCase):
    def test_analysis_can_run_twice_on_same_database(self):
        conn = sqlite3.connect(":memory:")
        run_sql.run_files([SAMPLE, ANALYSIS], conn)
        again = run_sql.run_files([ANALYSIS], conn)
        self.assertEqual(len(again), 7)

    def test_integer_time_still_gives_decimal_speed_rating(self):
        conn = sqlite3.connect(":memory:")
        run_sql.run_files([SAMPLE], conn)
        conn.execute("INSERT INTO results VALUES (7, '50 Free', 40, 1)")
        reports = {t: rows for t, _, rows in run_sql.run_files([ANALYSIS], conn)}
        grace = [r for r in reports["1. Clean performance report"] if r[1] == "Grace Liu"]
        self.assertEqual(grace[0][7], 2.5)
        # The ranked view computes its own speed_rating, so check it too.
        final = [r for r in reports["Final cleaned results by event and rank"] if r[2] == "Grace Liu"]
        self.assertEqual(final[0][4], 2.5)

    def test_splitter_ignores_semicolons_in_comments_and_strings(self):
        sql = "-- a comment; with a semicolon\r\nSELECT 'a;b';\r\nSELECT 2;\r\n"
        self.assertEqual(len(run_sql.split_statements(sql)), 2)

    def test_splitter_rejects_missing_semicolon(self):
        with self.assertRaises(ValueError):
            run_sql.split_statements("SELECT 1;\nSELECT 2\n")

    def test_report_title_read_from_marker(self):
        self.assertEqual(run_sql.report_title("-- REPORT: Hello\nSELECT 1;"), "Hello")
        self.assertIsNone(run_sql.report_title("SELECT 1;"))


if __name__ == "__main__":
    unittest.main()