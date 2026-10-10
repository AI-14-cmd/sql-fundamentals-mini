"""Run .sql files against an in-memory SQLite database and print the reports.

SQLite ships inside Python, so no database server is needed.
Pass the .sql files in the order they must run: the data first, then the analysis.
"""
import os
import sqlite3
import sys

REPORT_MARKER = "-- REPORT:"


def split_statements(sql_text):
    """Split a script into single statements.

    sqlite3.complete_statement understands comments and quoted strings,
    so a ';' inside them does not end a statement.
    """
    statements = []
    buffer = ""
    for line in sql_text.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            statements.append(buffer.strip())
            buffer = ""
    leftover = [
        line for line in buffer.splitlines()
        if line.strip() and not line.strip().startswith("--")
    ]
    if leftover:
        raise ValueError("Statement without a closing ';': " + leftover[0].strip())
    return statements


def report_title(statement):
    """Return the text after '-- REPORT:' in a statement, or None."""
    for line in statement.splitlines():
        stripped = line.strip()
        if stripped.startswith(REPORT_MARKER):
            return stripped[len(REPORT_MARKER):].strip()
    return None


def run_script(conn, sql_text):
    """Execute every statement; return the reports as (title, columns, rows)."""
    reports = []
    for statement in split_statements(sql_text):
        cursor = conn.execute(statement)
        if cursor.description is None:
            continue  # CREATE, INSERT, DROP ... return no rows
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        reports.append((report_title(statement), columns, rows))
    conn.commit()
    return reports


def run_files(paths, conn=None):
    """Run several .sql files, in order, on one connection."""
    if conn is None:
        conn = sqlite3.connect(":memory:")
    reports = []
    for path in paths:
        # utf-8-sig skips the byte-order mark some Windows editors add;
        # splitlines() handles both "\n" and "\r\n" line endings.
        with open(path, encoding="utf-8-sig") as handle:
            reports.extend(run_script(conn, handle.read()))
    return reports


def format_value(value):
    return "NULL" if value is None else str(value)


def format_report(title, columns, rows):
    """Lay a result set out as a plain-text table."""
    cells = [[format_value(v) for v in row] for row in rows]
    widths = [len(c) for c in columns]
    for row in cells:
        widths = [max(w, len(v)) for w, v in zip(widths, row)]

    def line(values):
        return " | ".join(v.ljust(w) for v, w in zip(values, widths)).rstrip()

    out = ["== " + (title or "Result") + " =="]
    out.append(line(columns))
    out.append("-+-".join("-" * w for w in widths))
    out.extend(line(row) for row in cells)
    out.append("(%d row%s)" % (len(rows), "" if len(rows) == 1 else "s"))
    return "\n".join(out)


def main(argv):
    if not argv:
        print("Usage: python " + os.path.basename(sys.argv[0]) + " FILE.sql [MORE.sql ...]")
        return 2
    try:
        reports = run_files(argv)
    except (OSError, ValueError, sqlite3.Error) as error:
        print("Error: " + str(error))
        return 1
    print("\n\n".join(format_report(*report) for report in reports))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))