
import sqlite3
import subprocess
import sys
from pathlib import Path
from flask import Flask, render_template, request, redirect

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "attendance.db"
SCRIPT_FILE = BASE_DIR / "mits_login.py"

# Keep track of the attendance update process.
attendance_process = None


def create_database():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                attended INTEGER NOT NULL,
                total INTEGER NOT NULL
            )
        """)


@app.route("/")
def home():
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        subjects = conn.execute(
            "SELECT * FROM subjects ORDER BY id"
        ).fetchall()

    attended = sum(subject["attended"] for subject in subjects)
    total = sum(subject["total"] for subject in subjects)
    percentage = attended / total * 100 if total else 0

    return render_template(
        "index.html",
        subjects=subjects,
        overall=round(percentage, 2),
        total_attended=attended,
        total_classes=total
    )


@app.route("/add", methods=["POST"])
def add_subject():
    name = request.form.get("name", "").strip()

    try:
        attended = int(request.form.get("attended", ""))
        total = int(request.form.get("total", ""))
    except ValueError:
        return "Please enter valid attendance numbers.", 400

    if not name or total <= 0 or attended < 0 or attended > total:
        return "Invalid attendance details.", 400

    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            """
            INSERT INTO subjects (name, attended, total)
            VALUES (?, ?, ?)
            """,
            (name, attended, total)
        )

    return redirect("/")


@app.route("/delete/<int:subject_id>", methods=["POST"])
def delete_subject(subject_id):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "DELETE FROM subjects WHERE id = ?",
            (subject_id,)
        )

    return redirect("/")


@app.route("/refresh-attendance", methods=["POST"])
def refresh_attendance():
    global attendance_process

    if not SCRIPT_FILE.exists():
        return "mits_login.py was not found.", 500

    # Do not start a second update while one is running.
    if (
        attendance_process is not None
        and attendance_process.poll() is None
    ):
        return """
        <h2>Attendance update already running</h2>
        <p>Finish the login and confirmation in its terminal.</p>
        <p><a href="/">Return to dashboard</a></p>
        """

    try:
        options = {}
        if sys.platform == "win32":
            options["creationflags"] = subprocess.CREATE_NEW_CONSOLE

        attendance_process = subprocess.Popen(
            [sys.executable, str(SCRIPT_FILE)],
            cwd=str(BASE_DIR),
            **options
        )

    except OSError as error:
        return f"Could not start the update: {error}", 500

    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Attendance Update</title>
    </head>
    <body>
        <h2>MITS attendance update started</h2>
        <ol>
            <li>Log in manually in the Playwright browser.</li>
            <li>Open the Attendance page.</li>
            <li>Return to the new terminal and press Enter.</li>
            <li>Check the subject records carefully.</li>
            <li>Type UPDATE only if the records are correct.</li>
        </ol>
        <p>After the script confirms success, return to the dashboard.</p>
        <p><a href="/">Return to dashboard</a></p>
    </body>
    </html>
    """


if __name__ == "__main__":
    create_database()
    app.run(debug=True, use_reloader=False)
