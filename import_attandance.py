import re
import sqlite3
from pathlib import Path

text = Path("mits_attendance.txt").read_text(encoding="utf-8")
lines = [line.strip() for line in text.splitlines() if line.strip()]

subjects = []

i = 0
while i < len(lines):
    # Subject records follow: serial, subject code/name,
    # classes attended, total conducted, attendance percentage.
    if (
        i + 4 < len(lines)
        and lines[i].isdigit()
        and lines[i + 2].isdigit()
        and lines[i + 3].isdigit()
        and re.fullmatch(r"\d+(?:\.\d+)?", lines[i + 4])
    ):
        serial = int(lines[i])
        name = lines[i + 1]
        attended = int(lines[i + 2])
        total = int(lines[i + 3])

        # Validate likely attendance records.
        if 0 <= attended <= total and total > 0:
            subjects.append((name, attended, total))
            i += 5
            continue

    i += 1

if not subjects:
    raise SystemExit(
        "No attendance records found. Database was not changed."
    )

print("Found these attendance records:")
for name, attended, total in subjects:
    print(f"{name}: {attended}/{total} ({attended / total * 100:.2f}%)")

confirm = input(
    "\nType IMPORT to replace the current subject records with these "
    "MITS records: "
)

if confirm != "IMPORT":
    print("Cancelled. Database unchanged.")
    raise SystemExit

db_path = Path("attendance.db")
if not db_path.exists():
    raise SystemExit("attendance.db not found. Database was not changed.")

conn = sqlite3.connect(db_path)

try:
    conn.execute("BEGIN")
    conn.execute("DELETE FROM subjects")
    conn.executemany(
        "INSERT INTO subjects (name, attended, total) VALUES (?, ?, ?)",
        subjects,
    )
    conn.commit()
    print(f"\nSuccessfully imported {len(subjects)} subjects.")
except Exception:
    conn.rollback()
    raise
finally:
    conn.close()