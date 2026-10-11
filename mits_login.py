
import re
import sqlite3
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
PORTAL_URL = "http://mitsims.in/studentIndex.html"
TEXT_FILE = BASE_DIR / "mits_attendance.txt"
DB_FILE = BASE_DIR / "attendance.db"


def extract_subjects(text):
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    subjects = []
    i = 0

    while i + 4 < len(lines):
        if (
            lines[i].isdigit()
            and lines[i + 2].isdigit()
            and lines[i + 3].isdigit()
            and re.fullmatch(r"\d+(?:\.\d+)?", lines[i + 4])
        ):
            name = lines[i + 1]
            attended = int(lines[i + 2])
            total = int(lines[i + 3])

            if (
                name.upper() not in {"S.NO", "SUBJECT CODE"}
                and total > 0
                and 0 <= attended <= total
            ):
                subjects.append((name, attended, total))
                i += 5
                continue

        i += 1

    # Remove duplicate records while preserving order.
    unique_subjects = []
    seen = set()

    for subject in subjects:
        if subject[0] not in seen:
            unique_subjects.append(subject)
            seen.add(subject[0])

    return unique_subjects


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        try:
            page = browser.new_page()

            print("Opening MITS portal...")

            page.goto(
                PORTAL_URL,
                wait_until="domcontentloaded",
                timeout=60000
            )

            input(
                "\nLog in manually in the opened browser, "
                "open Attendance, then press Enter here..."
            )

            text = page.locator("body").inner_text()
            TEXT_FILE.write_text(text, encoding="utf-8")

            subjects = extract_subjects(text)

            if len(subjects) < 10:
                print(
                    f"\nOnly {len(subjects)} subjects found. "
                    "Database has NOT been changed."
                )
                print(
                    "Make sure the Attendance page is open "
                    "and the subject table is visible."
                )
                return

            print(f"\nFound {len(subjects)} subjects:\n")

            for name, attended, total in subjects:
                percentage = attended / total * 100
                print(
                    f"{name}: {attended}/{total} "
                    f"({percentage:.2f}%)"
                )

            confirm = input(
                "\nCheck the records above. "
                "Type UPDATE to replace existing subjects: "
            )

            if confirm.strip() != "UPDATE":
                print("Cancelled. Database unchanged.")
                return

            with sqlite3.connect(DB_FILE) as conn:
                conn.execute("BEGIN")
                conn.execute("DELETE FROM subjects")
                conn.executemany(
                    """
                    INSERT INTO subjects (name, attended, total)
                    VALUES (?, ?, ?)
                    """,
                    subjects
                )

            print(
                f"\nSuccess! Updated {len(subjects)} subjects "
                "in attendance.db."
            )
            print("Return to your dashboard to view attendance.")

        finally:
            try:
                browser.close()
            except Exception as error:
                print(f"Browser cleanup: {error}")


if __name__ == "__main__":
    main()
