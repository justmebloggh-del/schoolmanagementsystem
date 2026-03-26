
#!/usr/bin/env python3
"""
School Management System API + Static File Server
=================================================
Enhanced version with comprehensive academic institution management:
- Student lifecycle management
- Staff management
- Course & curriculum management
- Attendance tracking
- Examination & grading
- Fee/finance management
- Library management
- Announcements & messaging
- Reports & analytics
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import date, datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse
import random

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "school.db"
HOST = "127.0.0.1"
PORT = 8000


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def parse_numeric_suffix(identifier: str, prefix: str) -> int:
    if not identifier.startswith(prefix):
        return -1
    suffix = identifier[len(prefix):]
    return int(suffix) if suffix.isdigit() else -1


def next_id(conn: sqlite3.Connection, table: str, prefix: str) -> str:
    rows = conn.execute(f"SELECT id FROM {table} WHERE id LIKE ?", (f"{prefix}%",)).fetchall()
    max_suffix = -1
    for row in rows:
        max_suffix = max(max_suffix, parse_numeric_suffix(row["id"], prefix))
    return f"{prefix}{max_suffix + 1 if max_suffix >= 0 else 1}"


def score_to_grade(score: float) -> str:
    if score >= 80: return "A"
    if score >= 70: return "B"
    if score >= 60: return "C"
    if score >= 50: return "D"
    return "F"


def score_to_grade_point(score: float) -> float:
    if score >= 80: return 4.0
    if score >= 70: return 3.5
    if score >= 60: return 3.0
    if score >= 50: return 2.5
    return 0.0


def create_default_courses_for_school(conn: sqlite3.Connection, school_id: str, lecturer: str = "Academic Team") -> None:
    starter_courses = [
        ("GST101", "Communication Skills", "General Studies", "100", 2, 220),
        ("ICT101", "Introduction to ICT", "Computer Science", "100", 3, 150),
        ("MTH101", "Basic Mathematics", "Mathematics", "100", 3, 180),
        ("BUS101", "Principles of Management", "Business Administration", "100", 3, 150),
        ("SCI101", "General Science", "Biological Sciences", "100", 3, 160),
        ("ENG101", "Engineering Fundamentals", "Electrical Engineering", "100", 3, 140),
    ]

    id_rows = conn.execute("SELECT id FROM sms_courses WHERE id LIKE 'COURSE-%'").fetchall()
    max_suffix = -1
    for row in id_rows:
        max_suffix = max(max_suffix, parse_numeric_suffix(row["id"], "COURSE-"))

    next_suffix = max_suffix + 1 if max_suffix >= 0 else 1
    payload = []
    for code, title, program, level, credits, seats in starter_courses:
        exists = conn.execute(
            "SELECT 1 FROM sms_courses WHERE school_id = ? AND code = ?",
            (school_id, code),
        ).fetchone()
        if exists:
            continue
        course_id = f"COURSE-{next_suffix}"
        next_suffix += 1
        payload.append((course_id, school_id, code, title, program, level, credits, seats, lecturer, 1))

    if not payload:
        return

    conn.executemany(
        """INSERT INTO sms_courses (id, school_id, code, title, program, level, credits, seats, lecturer, active)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        payload,
    )


def ensure_default_courses(conn: sqlite3.Connection) -> None:
    school_rows = conn.execute("SELECT id FROM sms_schools ORDER BY id").fetchall()
    for school in school_rows:
        create_default_courses_for_school(conn, school["id"])


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with get_conn() as conn:
        conn.executescript("""
            -- Schools table
            CREATE TABLE IF NOT EXISTS sms_schools (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT,
                address TEXT,
                password TEXT NOT NULL,
                created_at TEXT NOT NULL,
                region TEXT DEFAULT 'Greater Accra',
                country TEXT DEFAULT 'Ghana',
                tagline TEXT,
                logo_url TEXT
            );

            -- Academic Years
            CREATE TABLE IF NOT EXISTS sms_academic_years (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                name TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                is_current INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

            -- Terms/Semesters
            CREATE TABLE IF NOT EXISTS sms_terms (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                academic_year_id TEXT,
                name TEXT NOT NULL,
                term_order INTEGER,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                is_current INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE,
                FOREIGN KEY (academic_year_id) REFERENCES sms_academic_years(id)
            );

            -- Departments
            CREATE TABLE IF NOT EXISTS sms_departments (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                name TEXT NOT NULL,
                code TEXT,
                description TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

            -- Programs
            CREATE TABLE IF NOT EXISTS sms_programs (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                department_id TEXT,
                name TEXT NOT NULL,
                code TEXT,
                description TEXT,
                duration_years INTEGER DEFAULT 3,
                total_credits INTEGER DEFAULT 120,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE,
                FOREIGN KEY (department_id) REFERENCES sms_departments(id)
            );

            -- Levels
            CREATE TABLE IF NOT EXISTS sms_levels (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                name TEXT NOT NULL,
                code TEXT NOT NULL,
                order_index INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

            -- Staff
            CREATE TABLE IF NOT EXISTS sms_staff (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                department TEXT NOT NULL,
                phone TEXT,
                gender TEXT,
                qualification TEXT,
                position TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                UNIQUE (school_id, email),
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

            -- Students
            CREATE TABLE IF NOT EXISTS sms_students (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                program TEXT NOT NULL,
                level TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                password TEXT NOT NULL,
                gender TEXT,
                date_of_birth TEXT,
                guardian_name TEXT,
                guardian_phone TEXT,
                address TEXT,
                joined_on TEXT NOT NULL,
                approved_by TEXT,
                source_application_id TEXT,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

            -- Applications/Admissions
            CREATE TABLE IF NOT EXISTS sms_applications (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                full_name TEXT NOT NULL,
                dob TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                program_first_choice TEXT NOT NULL,
                program_second_choice TEXT,
                notes TEXT,
                status TEXT DEFAULT 'pending',
                submitted_on TEXT NOT NULL,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

            -- Courses
            CREATE TABLE IF NOT EXISTS sms_courses (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                code TEXT NOT NULL,
                title TEXT NOT NULL,
                program TEXT NOT NULL,
                level TEXT NOT NULL,
                credits INTEGER DEFAULT 3,
                seats INTEGER DEFAULT 30,
                lecturer TEXT NOT NULL,
                active INTEGER DEFAULT 1,
                description TEXT,
                UNIQUE (school_id, code),
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

            -- Registrations
            CREATE TABLE IF NOT EXISTS sms_registrations (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                student_id TEXT NOT NULL,
                term TEXT NOT NULL,
                registered_on TEXT NOT NULL,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES sms_students(id)
            );

            -- Registration Courses
            CREATE TABLE IF NOT EXISTS sms_registration_courses (
                registration_id TEXT NOT NULL,
                course_id TEXT NOT NULL,
                PRIMARY KEY (registration_id, course_id),
                FOREIGN KEY (registration_id) REFERENCES sms_registrations(id) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES sms_courses(id)
            );

            -- Attendance
            CREATE TABLE IF NOT EXISTS sms_attendance (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                date TEXT NOT NULL,
                course_id TEXT NOT NULL,
                taken_by TEXT,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES sms_courses(id)
            );

            -- Attendance Records
            CREATE TABLE IF NOT EXISTS sms_attendance_records (
                attendance_id TEXT NOT NULL,
                student_id TEXT NOT NULL,
                present INTEGER NOT NULL,
                PRIMARY KEY (attendance_id, student_id),
                FOREIGN KEY (attendance_id) REFERENCES sms_attendance(id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES sms_students(id)
            );

            -- Exams
            CREATE TABLE IF NOT EXISTS sms_exams (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                course_id TEXT,
                term TEXT NOT NULL,
                exam_type TEXT NOT NULL,
                title TEXT,
                exam_date TEXT NOT NULL,
                total_marks REAL NOT NULL,
                created_by TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

            -- Exam Results
            CREATE TABLE IF NOT EXISTS sms_exam_results (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                student_id TEXT NOT NULL,
                term TEXT NOT NULL,
                subject TEXT NOT NULL,
                score REAL NOT NULL,
                grade TEXT NOT NULL,
                grade_point REAL,
                recorded_by TEXT,
                recorded_on TEXT NOT NULL,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES sms_students(id)
            );

            -- Grade Scales
            CREATE TABLE IF NOT EXISTS sms_grade_scales (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                name TEXT NOT NULL,
                grade TEXT NOT NULL,
                min_marks REAL,
                max_marks REAL,
                grade_point REAL,
                description TEXT,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

            -- Fee Categories
            CREATE TABLE IF NOT EXISTS sms_fee_categories (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                amount REAL NOT NULL,
                academic_year TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

            -- Payments
            CREATE TABLE IF NOT EXISTS sms_payments (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                student_id TEXT NOT NULL,
                fee_category_id TEXT,
                amount_paid REAL NOT NULL,
                payment_date TEXT,
                payment_method TEXT,
                receipt_number TEXT,
                recorded_by TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES sms_students(id),
                FOREIGN KEY (fee_category_id) REFERENCES sms_fee_categories(id)
            );

            -- Library Books
            CREATE TABLE IF NOT EXISTS sms_books (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                isbn TEXT,
                title TEXT NOT NULL,
                author TEXT,
                publisher TEXT,
                category TEXT,
                total_copies INTEGER DEFAULT 1,
                available_copies INTEGER DEFAULT 1,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

            -- Book Issues
            CREATE TABLE IF NOT EXISTS sms_book_issues (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                book_id TEXT NOT NULL,
                student_id TEXT NOT NULL,
                issue_date TEXT NOT NULL,
                due_date TEXT NOT NULL,
                return_date TEXT,
                status TEXT DEFAULT 'issued',
                issued_by TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE,
                FOREIGN KEY (book_id) REFERENCES sms_books(id),
                FOREIGN KEY (student_id) REFERENCES sms_students(id)
            );

            -- Announcements
            CREATE TABLE IF NOT EXISTS sms_announcements (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                target_audience TEXT DEFAULT 'all',
                priority TEXT DEFAULT 'normal',
                is_published INTEGER DEFAULT 0,
                start_date TEXT,
                end_date TEXT,
                created_by TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

            -- Messages
            CREATE TABLE IF NOT EXISTS sms_messages (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                sender_type TEXT,
                recipient_id TEXT,
                recipient_type TEXT,
                subject TEXT,
                body TEXT,
                is_read INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

            -- Events/Calendar
            CREATE TABLE IF NOT EXISTS sms_events (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                event_type TEXT,
                event_date TEXT NOT NULL,
                created_by TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );
        """)
        seed_if_empty(conn)
        ensure_default_courses(conn)


def seed_if_empty(conn: sqlite3.Connection) -> None:
    school_count = conn.execute("SELECT COUNT(*) AS count FROM sms_schools").fetchone()["count"]
    if school_count > 0:
        return

    school_id = "SCH-1001"
    today = date.today().isoformat()

    # Seed school
    conn.execute("""INSERT INTO sms_schools (id, name, email, phone, address, password, created_at, tagline)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (school_id, "Greenfield College Ghana", "admin@greenfield.edu.gh", "+233 24 000 0000",
         "Accra, Greater Accra", "School@123", today, "Excellence in Education"))

    # Seed academic year
    academic_year_id = "AY-2025"
    conn.execute("""INSERT INTO sms_academic_years (id, school_id, name, start_date, end_date, is_current, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (academic_year_id, school_id, "2025-2026", "2025-09-01", "2026-08-31", 1, "active", today))

    # Seed terms
    conn.execute("""INSERT INTO sms_terms (id, school_id, academic_year_id, name, term_order, start_date, end_date, is_current, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("TERM-1", school_id, academic_year_id, "First Term", 1, "2025-09-01", "2025-12-15", 1, "active", today))
    conn.execute("""INSERT INTO sms_terms (id, school_id, academic_year_id, name, term_order, start_date, end_date, is_current, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("TERM-2", school_id, academic_year_id, "Second Term", 2, "2026-01-10", "2026-04-15", 0, "active", today))

    # Seed departments
    conn.execute("""INSERT INTO sms_departments (id, school_id, name, code, description, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("DEPT-1", school_id, "Computer Science", "CS", "Department of Computer Science", "active", today))
    conn.execute("""INSERT INTO sms_departments (id, school_id, name, code, description, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("DEPT-2", school_id, "Business Administration", "BUS", "Department of Business Studies", "active", today))
    conn.execute("""INSERT INTO sms_departments (id, school_id, name, code, description, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("DEPT-3", school_id, "Mathematics", "MTH", "Department of Mathematics", "active", today))

    # Seed programs
    conn.execute("""INSERT INTO sms_programs (id, school_id, department_id, name, code, description, duration_years, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("PROG-1", school_id, "DEPT-1", "Computer Science", "CS", "Bachelor of Science in Computer Science", 4, "active", today))
    conn.execute("""INSERT INTO sms_programs (id, school_id, department_id, name, code, description, duration_years, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("PROG-2", school_id, "DEPT-2", "Business Administration", "BA", "Bachelor of Business Administration", 4, "active", today))

    # Seed levels
    conn.execute("""INSERT INTO sms_levels (id, school_id, name, code, order_index, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
        ("LVL-1", school_id, "Level 100", "100", 1, today))
    conn.execute("""INSERT INTO sms_levels (id, school_id, name, code, order_index, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
        ("LVL-2", school_id, "Level 200", "200", 2, today))
    conn.execute("""INSERT INTO sms_levels (id, school_id, name, code, order_index, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
        ("LVL-3", school_id, "Level 300", "300", 3, today))
    conn.execute("""INSERT INTO sms_levels (id, school_id, name, code, order_index, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
        ("LVL-4", school_id, "Level 400", "400", 4, today))

    # Seed staff
    conn.execute("""INSERT INTO sms_staff (id, school_id, name, email, password, role, department, phone, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("STF-1001", school_id, "Ms. Hannah Reed", "teacher@greenfield.edu.gh", "Teach@123",
         "Academic Officer", "Computer Science", "+233 24 123 4567", "active", today))
    conn.execute("""INSERT INTO sms_staff (id, school_id, name, email, password, role, department, phone, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("STF-1002", school_id, "Kofi Mensah", "kofi.mensah@greenfield.edu.gh", "Staff@123",
         "Teacher", "Business Administration", "+233 24 234 5678", "active", today))
    conn.execute("""INSERT INTO sms_staff (id, school_id, name, email, password, role, department, phone, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("STF-1003", school_id, "Ama Osei", "ama.osei@greenfield.edu.gh", "Staff@123",
         "Accountant", "Finance", "+233 24 345 6789", "active", today))

    # Seed students
    conn.execute("""INSERT INTO sms_students (id, school_id, name, email, phone, program, level, status, password, joined_on)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("STU-1001", school_id, "Daniel Agyekum", "daniel.agyekum@student.edu.gh", "+233 20 001 0001",
         "Computer Science", "200", "active", "Student@123", "2025-08-20"))
    conn.execute("""INSERT INTO sms_students (id, school_id, name, email, phone, program, level, status, password, joined_on)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("STU-1002", school_id, "Lila Mensah", "lila.mensah@student.edu.gh", "+233 20 001 0002",
         "Business Administration", "100", "active", "Student@123", "2025-08-20"))
    conn.execute("""INSERT INTO sms_students (id, school_id, name, email, phone, program, level, status, password, joined_on)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("STU-1003", school_id, "Kojo Tetteh", "kojo.tetteh@student.edu.gh", "+233 20 001 0003",
         "Computer Science", "100", "active", "Student@123", "2025-08-20"))

    # Seed applications
    conn.execute("""INSERT INTO sms_applications (id, school_id, full_name, dob, email, phone, address, program_first_choice, program_second_choice, notes, status, submitted_on)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("APP-2001", school_id, "Esi Boateng", "2008-11-02", "esi.boateng@example.com", "+233 24 111 1001",
         "14 Cedar Street, Kumasi", "Biological Sciences", "Mathematics", "Science club lead", "pending", "2026-03-06"))
    conn.execute("""INSERT INTO sms_applications (id, school_id, full_name, dob, email, phone, address, program_first_choice, program_second_choice, notes, status, submitted_on)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("APP-2002", school_id, "Jonah Mills", "2008-04-12", "jonah.mills@example.com", "+233 24 111 1002",
         "99 River Lane, Accra", "Computer Science", "Electrical Engineering", "Olympiad participant", "pending", "2026-03-07"))

    # Seed courses
    conn.execute("""INSERT INTO sms_courses (id, school_id, code, title, program, level, credits, seats, lecturer, active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("COURSE-301", school_id, "CSC201", "Software Engineering Basics", "Computer Science", "200", 3, 40, "Ms. Hannah Reed", 1))
    conn.execute("""INSERT INTO sms_courses (id, school_id, code, title, program, level, credits, seats, lecturer, active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("COURSE-302", school_id, "BUS105", "Principles of Management", "Business Administration", "100", 3, 50, "Kofi Mensah", 1))

    # Seed grade scales
    conn.execute("""INSERT INTO sms_grade_scales (id, school_id, name, grade, min_marks, max_marks, grade_point, description)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ("GS-1", school_id, "Standard", "A", 80, 100, 4.0, "Excellent"))
    conn.execute("""INSERT INTO sms_grade_scales (id, school_id, name, grade, min_marks, max_marks, grade_point, description)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ("GS-2", school_id, "Standard", "B", 70, 79, 3.5, "Very Good"))
    conn.execute("""INSERT INTO sms_grade_scales (id, school_id, name, grade, min_marks, max_marks, grade_point, description)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ("GS-3", school_id, "Standard", "C", 60, 69, 3.0, "Good"))
    conn.execute("""INSERT INTO sms_grade_scales (id, school_id, name, grade, min_marks, max_marks, grade_point, description)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ("GS-4", school_id, "Standard", "D", 50, 59, 2.5, "Pass"))
    conn.execute("""INSERT INTO sms_grade_scales (id, school_id, name, grade, min_marks, max_marks, grade_point, description)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ("GS-5", school_id, "Standard", "F", 0, 49, 0.0, "Fail"))

    # Seed fee categories
    conn.execute("""INSERT INTO sms_fee_categories (id, school_id, name, description, amount, academic_year, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ("FEE-1", school_id, "Tuition", "Full tuition fees for academic year", 5000.00, "2025-2026", "active", today))
    conn.execute("""INSERT INTO sms_fee_categories (id, school_id, name, description, amount, academic_year, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ("FEE-2", school_id, "Registration", "Registration and administration fees", 500.00, "2025-2026", "active", today))
    conn.execute("""INSERT INTO sms_fee_categories (id, school_id, name, description, amount, academic_year, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ("FEE-3", school_id, "Library", "Library membership and resources", 200.00, "2025-2026", "active", today))
    conn.execute("""INSERT INTO sms_fee_categories (id, school_id, name, description, amount, academic_year, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ("FEE-4", school_id, "Sports", "Sports and recreational facilities", 150.00, "2025-2026", "active", today))

    # Seed library books
    conn.execute("""INSERT INTO sms_books (id, school_id, isbn, title, author, publisher, category, total_copies, available_copies, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("BOOK-1", school_id, "978-0134685991", "Effective Java", "Joshua Bloch", "Addison-Wesley", "Programming", 5, 4, "active", today))
    conn.execute("""INSERT INTO sms_books (id, school_id, isbn, title, author, publisher, category, total_copies, available_copies, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("BOOK-2", school_id, "978-0321573513", "Algorithms", "Robert Sedgewick", "Addison-Wesley", "Computer Science", 3, 3, "active", today))
    conn.execute("""INSERT INTO sms_books (id, school_id, isbn, title, author, publisher, category, total_copies, available_copies, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("BOOK-3", school_id, "978-0132350884", "Clean Code", "Robert Martin", "Prentice Hall", "Programming", 4, 4, "active", today))

    # Seed announcements
    conn.execute("""INSERT INTO sms_announcements (id, school_id, title, content, target_audience, priority, is_published, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (school_id, "ANN-1", "Welcome to 2025-2026 Academic Year", "We are excited to welcome all students to the new academic year. Classes begin on September 1, 2025.", "all", "high", 1, today))
    conn.execute("""INSERT INTO sms_announcements (id, school_id, title, content, target_audience, priority, is_published, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (school_id, "ANN-2", "Course Registration Open", "Course registration for First Term is now open. Please register before the deadline.", "students", "normal", 1, today))
    conn.execute("""INSERT INTO sms_announcements (id, school_id, title, content, target_audience, priority, is_published, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (school_id, "ANN-3", "Mid-Term Examinations", "Mid-term examinations will be held from November 15-20, 2025.", "students", "normal", 1, today))


def serialize_school(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "phone": row["phone"] or "",
        "address": row["address"] or "",
        "createdAt": row["created_at"],
        "region": row.get("region", ""),
        "country": row.get("country", "Ghana"),
        "tagline": row.get("tagline", "")
    }


def serialize_staff(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "role": row["role"],
        "department": row["department"],
        "phone": row.get("phone", ""),
        "gender": row.get("gender", ""),
        "qualification": row.get("qualification", ""),
        "position": row.get("position", ""),
        "status": row["status"],
        "createdAt": row["created_at"]
    }


def serialize_student(row: sqlite3.Row, include_password: bool = False) -> dict:
    payload = {
        "id": row["id"],
        "name": row["name"],
        "email": row.get("email", ""),
        "phone": row.get("phone", ""),
        "program": row["program"],
        "level": row["level"],
        "status": row["status"],
        "gender": row.get("gender", ""),
        "guardianName": row.get("guardian_name", ""),
        "guardianPhone": row.get("guardian_phone", ""),
        "address": row.get("address", ""),
        "joinedOn": row["joined_on"]
    }
    if include_password:
        payload["password"] = row["password"]
    return payload


def serialize_data(conn: sqlite3.Connection, school: sqlite3.Row) -> dict:
    school_id = school["id"]

    # Staff
    staff = [serialize_staff(row) for row in conn.execute(
        "SELECT * FROM sms_staff WHERE school_id = ? ORDER BY created_at DESC", (school_id,)
    ).fetchall()]

    # Students
    students = [serialize_student(row) for row in conn.execute(
        "SELECT * FROM sms_students WHERE school_id = ? ORDER BY id", (school_id,)
    ).fetchall()]

    # Applications
    applications = []
    for row in conn.execute(
        "SELECT * FROM sms_applications WHERE school_id = ? ORDER BY submitted_on DESC", (school_id,)
    ).fetchall():
        applications.append({
            "id": row["id"],
            "fullName": row["full_name"],
            "dob": row["dob"],
            "email": row["email"],
            "phone": row["phone"],
            "address": row["address"],
            "programFirstChoice": row["program_first_choice"],
            "programSecondChoice": row["program_second_choice"] or "",
            "notes": row["notes"] or "",
            "status": row["status"],
            "submittedOn": row["submitted_on"]
        })

    # Courses
    courses = []
    for row in conn.execute(
        "SELECT * FROM sms_courses WHERE school_id = ? ORDER BY code", (school_id,)
    ).fetchall():
        courses.append({
            "id": row["id"],
            "code": row["code"],
            "title": row["title"],
            "program": row["program"],
            "level": row["level"],
            "credits": row["credits"],
            "seats": row["seats"],
            "lecturer": row["lecturer"],
            "active": bool(row["active"]),
            "description": row.get("description", "")
        })

    # Registrations
    registrations = []
    reg_rows = conn.execute(
        "SELECT r.*, rc.course_id FROM sms_registrations r LEFT JOIN sms_registration_courses rc ON rc.registration_id = r.id WHERE r.school_id = ? ORDER BY r.registered_on DESC",
        (school_id,)
    ).fetchall()
    reg_map = {}
    for row in reg_rows:
        reg = reg_map.get(row["id"])
        if not reg:
            reg = {"id": row["id"], "studentId": row["student_id"], "term": row["term"], "registeredOn": row["registered_on"], "courseIds": []}
            reg_map[row["id"]] = reg
        if row["course_id"]:
            reg["courseIds"].append(row["course_id"])
    registrations = list(reg_map.values())

    # Attendance
    attendance = []
    for row in conn.execute(
        "SELECT * FROM sms_attendance WHERE school_id = ? ORDER BY date DESC", (school_id,)
    ).fetchall():
        records = conn.execute(
            "SELECT student_id, present FROM sms_attendance_records WHERE attendance_id = ?", (row["id"],)
        ).fetchall()
        present = [r["student_id"] for r in records if r["present"] == 1]
        absent = [r["student_id"] for r in records if r["present"] == 0]
        attendance.append({
            "id": row["id"],
            "date": row["date"],
            "courseId": row["course_id"],
            "presentStudentIds": present,
            "absentStudentIds": absent,
            "takenBy": row.get("taken_by", "")
        })

    # Exam Results
    exam_results = []
    for row in conn.execute(
                    "SELECT * FROM sms_students WHERE id = ? AND school_id = ?",
                    (student_id, school["id"]),
                ).fetchone()
            if not row:
                self.send_json({"ok": False, "message": "Student not found."}, HTTPStatus.NOT_FOUND)
                return
            self.send_json({"ok": True, "student": serialize_student(row)})
            return

        if path.startswith("/api/staff/") or path.startswith("/api/teachers/"):
            school = self.require_school()
            if not school:
                return
            staff_id = unquote(path.split("/", 3)[3])
            with get_conn() as conn:
                row = conn.execute(
                    "SELECT * FROM sms_staff WHERE id = ? AND school_id = ?",
                    (staff_id, school["id"]),
                ).fetchone()
            if not row:
                self.send_json({"ok": False, "message": "Staff not found."}, HTTPStatus.NOT_FOUND)
                return
            self.send_json({"ok": True, "staff": serialize_staff(row), "teacher": serialize_staff(row)})
            return

        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path

        try:
            body = self.read_json_body()
        except json.JSONDecodeError:
            self.send_json({"ok": False, "message": "Invalid JSON body."}, HTTPStatus.BAD_REQUEST)
            return

        if path == "/api/schools/register":
            self.handle_school_register(body)
            return

        if path == "/api/schools/login":
            self.handle_school_login(body)
            return

        if path == "/api/admissions":
            self.handle_admissions(body)
            return

        if path == "/api/auth/student-login":
            self.handle_student_login(body)
            return

        if path in {"/api/auth/staff-login", "/api/auth/teacher-login"}:
            self.handle_staff_login(body)
            return

        if path == "/api/registrations":
            self.handle_registrations(body)
            return

        if path == "/api/staff":
            self.handle_add_staff(body)
            return

        if path == "/api/exam-results":
            self.handle_exam_results(body)
            return

        match = re.match(r"^/api/applications/([^/]+)/approve$", path)
        if match:
            self.handle_approve_application(unquote(match.group(1)), body)
            return

        match = re.match(r"^/api/applications/([^/]+)/reject$", path)
        if match:
            self.handle_reject_application(unquote(match.group(1)))
            return

        if path == "/api/courses":
            self.handle_add_course(body)
            return

        match = re.match(r"^/api/courses/([^/]+)/toggle$", path)
        if match:
            self.handle_toggle_course(unquote(match.group(1)))
            return

        if path == "/api/attendance":
            self.handle_attendance(body)
            return

        self.send_json({"ok": False, "message": "Unknown endpoint."}, HTTPStatus.NOT_FOUND)

    def handle_school_register(self, body: dict) -> None:
        school_name = str(body.get("schoolName", "")).strip()
        school_email = str(body.get("schoolEmail", "")).strip().lower()
        school_phone = str(body.get("schoolPhone", "")).strip()
        school_address = str(body.get("schoolAddress", "")).strip()
        school_password = str(body.get("password", ""))

        admin_name = str(body.get("adminName", "")).strip() or "School Admin"
        admin_email = str(body.get("adminEmail", "")).strip().lower() or school_email
        admin_password = str(body.get("adminPassword", "")).strip() or "Staff@123"

        if not school_name or not school_email or not school_password:
            self.send_json(
                {"ok": False, "message": "School name, email and password are required."},
                HTTPStatus.BAD_REQUEST,
            )
            return

        with get_conn() as conn:
            if conn.execute(
                "SELECT 1 FROM sms_schools WHERE LOWER(email) = ?",
                (school_email,),
            ).fetchone():
                self.send_json(
                    {"ok": False, "message": "A school account already exists with that email."},
                    HTTPStatus.BAD_REQUEST,
                )
                return

            school_id = next_id(conn, "sms_schools", "SCH-")
            staff_id = next_id(conn, "sms_staff", "STF-")
            created_at = date.today().isoformat()

            conn.execute(
                """
                INSERT INTO sms_schools (id, name, email, phone, address, password, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    school_id,
                    school_name,
                    school_email,
                    school_phone,
                    school_address,
                    school_password,
                    created_at,
                ),
            )
            conn.execute(
                """
                INSERT INTO sms_staff (id, school_id, name, email, password, role, department, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?)
                """,
                (
                    staff_id,
                    school_id,
                    admin_name,
                    admin_email,
                    admin_password,
                    "Administrator",
                    "Administration",
                    created_at,
                ),
            )
            create_default_courses_for_school(conn, school_id, admin_name or "Academic Team")

        self.send_json(
            {
                "ok": True,
                "message": "School account created successfully. Starter courses are ready for registration.",
                "school": {
                    "id": school_id,
                    "name": school_name,
                    "email": school_email,
                    "phone": school_phone,
                    "address": school_address,
                    "createdAt": created_at,
                },
                "defaultStaff": {
                    "id": staff_id,
                    "email": admin_email,
                    "password": admin_password,
                },
            }
        )

    def handle_school_login(self, body: dict) -> None:
        email = str(body.get("email", "")).strip()
        password = str(body.get("password", ""))

        with get_conn() as conn:
            school = find_school_for_login(conn, email, password)
        if not school:
            self.send_json({"ok": False, "message": "Invalid school credentials."}, HTTPStatus.UNAUTHORIZED)
            return

        self.send_json({"ok": True, "school": serialize_school(school)})

    def handle_admissions(self, body: dict) -> None:
        school = self.require_school()
        if not school:
            return

        required = ["fullName", "dob", "email", "phone", "address", "programFirstChoice"]
        if any(not str(body.get(field, "")).strip() for field in required):
            self.send_json({"ok": False, "message": "Please fill all required fields."}, HTTPStatus.BAD_REQUEST)
            return

        with get_conn() as conn:
            app_id = next_id(conn, "sms_applications", "APP-")
            conn.execute(
                """
                INSERT INTO sms_applications (
                    id, school_id, full_name, dob, email, phone, address,
                    program_first_choice, program_second_choice, notes, status, submitted_on
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                """,
                (
                    app_id,
                    school["id"],
                    body["fullName"].strip(),
                    body["dob"],
                    body["email"].strip().lower(),
                    body["phone"].strip(),
                    body["address"].strip(),
                    body["programFirstChoice"].strip(),
                    str(body.get("programSecondChoice", "")).strip(),
                    str(body.get("notes", "")).strip(),
                    date.today().isoformat(),
                ),
            )

        self.send_json({"ok": True, "message": "Application submitted.", "applicationId": app_id})

    def handle_student_login(self, body: dict) -> None:
        school = self.require_school()
        if not school:
            return

        identifier = str(body.get("identifier", "")).strip()
        password = str(body.get("password", ""))

        with get_conn() as conn:
            row = find_student_for_login(conn, school["id"], identifier, password)
        if not row:
            self.send_json({"ok": False, "message": "Invalid student credentials."}, HTTPStatus.UNAUTHORIZED)
            return

        self.send_json({"ok": True, "student": serialize_student(row)})

    def handle_staff_login(self, body: dict) -> None:
        school = self.require_school()
        if not school:
            return

        identifier = str(body.get("identifier", "")).strip()
        password = str(body.get("password", ""))

        with get_conn() as conn:
            row = find_staff_for_login(conn, school["id"], identifier, password)
        if not row:
            self.send_json({"ok": False, "message": "Invalid staff credentials."}, HTTPStatus.UNAUTHORIZED)
            return

        staff_payload = serialize_staff(row)
        self.send_json({"ok": True, "staff": staff_payload, "teacher": staff_payload})

    def handle_registrations(self, body: dict) -> None:
        school = self.require_school()
        if not school:
            return

        identifier = str(body.get("studentIdentifier", "")).strip()
        password = str(body.get("password", ""))
        term = str(body.get("term", "")).strip()
        course_ids = body.get("courseIds", [])

        if not term:
            self.send_json({"ok": False, "message": "Please choose a term."}, HTTPStatus.BAD_REQUEST)
            return

        if not isinstance(course_ids, list) or not course_ids:
            self.send_json({"ok": False, "message": "Select at least one course."}, HTTPStatus.BAD_REQUEST)
            return

        with get_conn() as conn:
            student = find_student_for_login(conn, school["id"], identifier, password)
            if not student:
                self.send_json({"ok": False, "message": "Student authentication failed."}, HTTPStatus.UNAUTHORIZED)
                return

            placeholders = ",".join("?" for _ in course_ids)
            query = f"""
                SELECT id FROM sms_courses
                WHERE school_id = ? AND id IN ({placeholders}) AND active = 1
            """
            active_rows = conn.execute(query, tuple([school["id"], *course_ids])).fetchall()
            active_ids = {row["id"] for row in active_rows}
            if len(active_ids) != len(set(course_ids)):
                self.send_json({"ok": False, "message": "One or more courses are invalid."}, HTTPStatus.BAD_REQUEST)
                return

            existing = conn.execute(
                """
                SELECT id FROM sms_registrations
                WHERE school_id = ? AND student_id = ? AND term = ?
                """,
                (school["id"], student["id"], term),
            ).fetchone()
            if existing:
                conn.execute("DELETE FROM sms_registration_courses WHERE registration_id = ?", (existing["id"],))
                conn.execute("DELETE FROM sms_registrations WHERE id = ?", (existing["id"],))

            reg_id = next_id(conn, "sms_registrations", "REG-")
            conn.execute(
                """
                INSERT INTO sms_registrations (id, school_id, student_id, term, registered_on)
                VALUES (?, ?, ?, ?, ?)
                """,
                (reg_id, school["id"], student["id"], term, datetime.utcnow().isoformat() + "Z"),
            )
            conn.executemany(
                "INSERT INTO sms_registration_courses (registration_id, course_id) VALUES (?, ?)",
                [(reg_id, course_id) for course_id in course_ids],
            )

        self.send_json({"ok": True, "message": f"Registration saved for {student['name']}."})

    def handle_add_staff(self, body: dict) -> None:
        school = self.require_school()
        if not school:
            return

        name = str(body.get("name", "")).strip()
        email = str(body.get("email", "")).strip().lower()
        role = str(body.get("role", "")).strip()
        department = str(body.get("department", "")).strip()
        password = str(body.get("password", "")).strip() or "Staff@123"

        if not name or not email or not role or not department:
            self.send_json({"ok": False, "message": "Fill all required staff fields."}, HTTPStatus.BAD_REQUEST)
            return

        with get_conn() as conn:
            if conn.execute(
                "SELECT 1 FROM sms_staff WHERE school_id = ? AND LOWER(email) = ?",
                (school["id"], email),
            ).fetchone():
                self.send_json({"ok": False, "message": "Staff email already exists."}, HTTPStatus.BAD_REQUEST)
                return

            staff_id = next_id(conn, "sms_staff", "STF-")
            conn.execute(
                """
                INSERT INTO sms_staff (id, school_id, name, email, password, role, department, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?)
                """,
                (staff_id, school["id"], name, email, password, role, department, date.today().isoformat()),
            )

        self.send_json(
            {
                "ok": True,
                "message": "Staff account added.",
                "staffId": staff_id,
                "defaultPassword": password,
            }
        )

    def handle_exam_results(self, body: dict) -> None:
        school = self.require_school()
        if not school:
            return

        student_id = str(body.get("studentId", "")).strip()
        term = str(body.get("term", "")).strip()
        subject = str(body.get("subject", "")).strip()
        score_raw = body.get("score")
        grade = str(body.get("grade", "")).strip().upper()
        recorded_by = str(body.get("staffId", "")).strip()

        try:
            score = float(score_raw)
        except (TypeError, ValueError):
            self.send_json({"ok": False, "message": "Score must be numeric."}, HTTPStatus.BAD_REQUEST)
            return

        if not student_id or not term or not subject:
            self.send_json({"ok": False, "message": "Student, term and subject are required."}, HTTPStatus.BAD_REQUEST)
            return

        if score < 0 or score > 100:
            self.send_json({"ok": False, "message": "Score must be between 0 and 100."}, HTTPStatus.BAD_REQUEST)
            return

        with get_conn() as conn:
            student = conn.execute(
                "SELECT id FROM sms_students WHERE id = ? AND school_id = ?",
                (student_id, school["id"]),
            ).fetchone()
            if not student:
                self.send_json({"ok": False, "message": "Student not found."}, HTTPStatus.NOT_FOUND)
                return

            if recorded_by:
                staff = conn.execute(
                    "SELECT id FROM sms_staff WHERE id = ? AND school_id = ?",
                    (recorded_by, school["id"]),
                ).fetchone()
                if not staff:
                    self.send_json({"ok": False, "message": "Staff record not found."}, HTTPStatus.BAD_REQUEST)
                    return

            result_id = next_id(conn, "sms_exam_results", "RES-")
            conn.execute(
                """
                INSERT INTO sms_exam_results (id, school_id, student_id, term, subject, score, grade, recorded_by, recorded_on)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result_id,
                    school["id"],
                    student_id,
                    term,
                    subject,
                    score,
                    grade or score_to_grade(score),
                    recorded_by or None,
                    date.today().isoformat(),
                ),
            )

        self.send_json({"ok": True, "message": "Exam result recorded."})

    def handle_approve_application(self, app_id: str, body: dict) -> None:
        school = self.require_school()
        if not school:
            return

        staff_id = str(body.get("teacherId", "")).strip() or str(body.get("staffId", "")).strip()

        with get_conn() as conn:
            app = conn.execute(
                "SELECT * FROM sms_applications WHERE id = ? AND school_id = ?",
                (app_id, school["id"]),
            ).fetchone()
            if not app:
                self.send_json({"ok": False, "message": "Application not found."}, HTTPStatus.NOT_FOUND)
                return
            if app["status"] != "pending":
                self.send_json({"ok": False, "message": "Application is already processed."}, HTTPStatus.BAD_REQUEST)
                return

            if staff_id:
                staff = conn.execute(
                    "SELECT id FROM sms_staff WHERE id = ? AND school_id = ?",
                    (staff_id, school["id"]),
                ).fetchone()
                if not staff:
                    self.send_json({"ok": False, "message": "Approving staff not found."}, HTTPStatus.BAD_REQUEST)
                    return

            student_id = next_id(conn, "sms_students", "STU-")
            student_email = unique_student_email(conn, school["id"], app["email"], app_id)

            conn.execute("UPDATE sms_applications SET status = 'approved' WHERE id = ?", (app_id,))
            conn.execute(
                """
                INSERT INTO sms_students (
                    id, school_id, name, email, phone, program, level, status,
                    password, joined_on, approved_by, source_application_id
                )
                VALUES (?, ?, ?, ?, ?, ?, '100', 'active', 'Student@123', ?, ?, ?)
                """,
                (
                    student_id,
                    school["id"],
                    app["full_name"],
                    student_email,
                    app["phone"],
                    app["program_first_choice"],
                    date.today().isoformat(),
                    staff_id or None,
                    app_id,
                ),
            )

            ann_id = next_id(conn, "sms_announcements", "ANN-")
            conn.execute(
                "INSERT INTO sms_announcements (id, school_id, title, created_at) VALUES (?, ?, ?, ?)",
                (
                    ann_id,
                    school["id"],
                    f"{app['full_name']} admitted to {app['program_first_choice']}.",
                    date.today().isoformat(),
                ),
            )

        self.send_json(
            {
                "ok": True,
                "message": "Application approved. Student account created with default password Student@123.",
            }
        )

    def handle_reject_application(self, app_id: str) -> None:
        school = self.require_school()
        if not school:
            return

        with get_conn() as conn:
            app = conn.execute(
                "SELECT * FROM sms_applications WHERE id = ? AND school_id = ?",
                (app_id, school["id"]),
            ).fetchone()
            if not app:
                self.send_json({"ok": False, "message": "Application not found."}, HTTPStatus.NOT_FOUND)
                return
            if app["status"] != "pending":
                self.send_json({"ok": False, "message": "Application is already processed."}, HTTPStatus.BAD_REQUEST)
                return
            conn.execute("UPDATE sms_applications SET status = 'rejected' WHERE id = ?", (app_id,))

        self.send_json({"ok": True, "message": "Application rejected."})

    def handle_add_course(self, body: dict) -> None:
        school = self.require_school()
        if not school:
            return

        code = str(body.get("code", "")).strip().upper()
        title = str(body.get("title", "")).strip()
        program = str(body.get("program", "")).strip()
        level = str(body.get("level", "")).strip()
        lecturer = str(body.get("teacherName", "")).strip() or str(body.get("staffName", "")).strip() or "Faculty"

        try:
            credits = int(body.get("credits", 3))
            seats = int(body.get("seats", 30))
        except (TypeError, ValueError):
            self.send_json({"ok": False, "message": "Credits and seats must be numeric."}, HTTPStatus.BAD_REQUEST)
            return

        if not code or not title or not program or not level:
            self.send_json({"ok": False, "message": "Fill all required course fields."}, HTTPStatus.BAD_REQUEST)
            return

        with get_conn() as conn:
            try:
                course_id = next_id(conn, "sms_courses", "COURSE-")
                conn.execute(
                    """
                    INSERT INTO sms_courses (id, school_id, code, title, program, level, credits, seats, lecturer, active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (course_id, school["id"], code, title, program, level, credits, seats, lecturer),
                )
            except sqlite3.IntegrityError:
                self.send_json({"ok": False, "message": "Course code already exists."}, HTTPStatus.BAD_REQUEST)
                return

        self.send_json({"ok": True, "message": "Course added."})

    def handle_toggle_course(self, course_id: str) -> None:
        school = self.require_school()
        if not school:
            return

        with get_conn() as conn:
            course = conn.execute(
                "SELECT active FROM sms_courses WHERE id = ? AND school_id = ?",
                (course_id, school["id"]),
            ).fetchone()
            if not course:
                self.send_json({"ok": False, "message": "Course not found."}, HTTPStatus.NOT_FOUND)
                return
            new_value = 0 if course["active"] == 1 else 1
            conn.execute("UPDATE sms_courses SET active = ? WHERE id = ?", (new_value, course_id))

        self.send_json({"ok": True, "message": "Course status updated."})

    def handle_attendance(self, body: dict) -> None:
        school = self.require_school()
        if not school:
            return

        attendance_date = str(body.get("date", "")).strip()
        course_id = str(body.get("courseId", "")).strip()
        present_ids = body.get("presentStudentIds", [])
        staff_id = str(body.get("teacherId", "")).strip() or str(body.get("staffId", "")).strip()

        if not attendance_date or not course_id:
            self.send_json({"ok": False, "message": "Date and course are required."}, HTTPStatus.BAD_REQUEST)
            return

        if not isinstance(present_ids, list):
            self.send_json({"ok": False, "message": "Invalid attendance payload."}, HTTPStatus.BAD_REQUEST)
            return

        with get_conn() as conn:
            course = conn.execute(
                "SELECT id FROM sms_courses WHERE id = ? AND school_id = ?",
                (course_id, school["id"]),
            ).fetchone()
            if not course:
                self.send_json({"ok": False, "message": "Course not found."}, HTTPStatus.NOT_FOUND)
                return

            existing = conn.execute(
                "SELECT id FROM sms_attendance WHERE school_id = ? AND date = ? AND course_id = ?",
                (school["id"], attendance_date, course_id),
            ).fetchone()
            if existing:
                conn.execute("DELETE FROM sms_attendance_records WHERE attendance_id = ?", (existing["id"],))
                conn.execute("DELETE FROM sms_attendance WHERE id = ?", (existing["id"],))

            attendance_id = next_id(conn, "sms_attendance", "ATT-")
            conn.execute(
                """
                INSERT INTO sms_attendance (id, school_id, date, course_id, taken_by)
                VALUES (?, ?, ?, ?, ?)
                """,
                (attendance_id, school["id"], attendance_date, course_id, staff_id or None),
            )

            students = conn.execute(
                "SELECT id FROM sms_students WHERE school_id = ? ORDER BY id",
                (school["id"],),
            ).fetchall()
            present_set = {str(item) for item in present_ids}
            conn.executemany(
                "INSERT INTO sms_attendance_records (attendance_id, student_id, present) VALUES (?, ?, ?)",
                [
                    (attendance_id, student["id"], 1 if student["id"] in present_set else 0)
                    for student in students
                ],
            )

        self.send_json({"ok": True, "message": "Attendance saved."})


def run_server() -> None:
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), SMSRequestHandler)
    print(f"Server running at http://{HOST}:{PORT}")
    print(f"Database file: {DB_PATH}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
