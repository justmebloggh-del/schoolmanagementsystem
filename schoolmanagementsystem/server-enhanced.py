
#!/usr/bin/env python3
"""
School Management System API + Static File Server
================================================
Enhanced version with support for:
- Multi-school support
- Student management (admissions, registrations, profiles)
- Staff management
- Course management
- Attendance tracking
- Examination & grading system
- Fee management
- Library management
- Announcements & messaging
- Reports & analytics
- Academic years, terms, departments, programs, levels
- Class groups
- Events calendar

Run this instead of server.py for full functionality
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import date, datetime, timedelta
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

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
    if score >= 80:
        return "A"
    if score >= 70:
        return "B"
    if score >= 60:
        return "C"
    if score >= 50:
        return "D"
    return "F"


def score_to_grade_point(score: float) -> float:
    if score >= 80:
        return 4.0
    if score >= 70:
        return 3.5
    if score >= 60:
        return 3.0
    if score >= 50:
        return 2.5
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

    if payload:
        conn.executemany(
            "INSERT INTO sms_courses (id, school_id, code, title, program, level, credits, seats, lecturer, active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            payload,
        )


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sms_schools (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT,
                address TEXT,
                password TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sms_academic_years (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                name TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                is_current INTEGER DEFAULT 0,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sms_terms (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                academic_year_id TEXT,
                name TEXT NOT NULL,
                term_order INTEGER,
                start_date TEXT,
                end_date TEXT,
                is_current INTEGER DEFAULT 0,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sms_departments (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                name TEXT NOT NULL,
                code TEXT,
                description TEXT,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sms_programs (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                department_id TEXT,
                name TEXT NOT NULL,
                code TEXT,
                description TEXT,
                duration_years INTEGER DEFAULT 3,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sms_levels (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                name TEXT NOT NULL,
                code TEXT NOT NULL,
                order_index INTEGER,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sms_staff (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                department TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                phone TEXT,
                position TEXT,
                qualification TEXT,
                created_at TEXT NOT NULL,
                UNIQUE (school_id, email),
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

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
                status TEXT NOT NULL DEFAULT 'pending',
                submitted_on TEXT NOT NULL,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sms_students (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                program TEXT NOT NULL,
                level TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                password TEXT NOT NULL,
                gender TEXT,
                date_of_birth TEXT,
                guardian_name TEXT,
                guardian_phone TEXT,
                address TEXT,
                joined_on TEXT NOT NULL,
                approved_by TEXT,
                source_application_id TEXT,
                UNIQUE (school_id, email),
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE,
                FOREIGN KEY (approved_by) REFERENCES sms_staff(id)
            );

            CREATE TABLE IF NOT EXISTS sms_courses (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                code TEXT NOT NULL,
                title TEXT NOT NULL,
                program TEXT NOT NULL,
                level TEXT NOT NULL,
                credits INTEGER NOT NULL DEFAULT 3,
                seats INTEGER NOT NULL DEFAULT 30,
                lecturer TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                description TEXT,
                UNIQUE (school_id, code),
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sms_registrations (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                student_id TEXT NOT NULL,
                term TEXT NOT NULL,
                registered_on TEXT NOT NULL,
                UNIQUE (school_id, student_id, term),
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES sms_students(id)
            );

            CREATE TABLE IF NOT EXISTS sms_registration_courses (
                registration_id TEXT NOT NULL,
                course_id TEXT NOT NULL,
                PRIMARY KEY (registration_id, course_id),
                FOREIGN KEY (registration_id) REFERENCES sms_registrations(id) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES sms_courses(id)
            );

            CREATE TABLE IF NOT EXISTS sms_attendance (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                date TEXT NOT NULL,
                course_id TEXT NOT NULL,
                taken_by TEXT,
                UNIQUE (school_id, date, course_id),
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES sms_courses(id)
            );

            CREATE TABLE IF NOT EXISTS sms_attendance_records (
                attendance_id TEXT NOT NULL,
                student_id TEXT NOT NULL,
                present INTEGER NOT NULL,
                PRIMARY KEY (attendance_id, student_id),
                FOREIGN KEY (attendance_id) REFERENCES sms_attendance(id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES sms_students(id)
            );

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
                FOREIGN KEY (student_id) REFERENCES sms_students(id),
                FOREIGN KEY (recorded_by) REFERENCES sms_staff(id)
            );

            CREATE TABLE IF NOT EXISTS sms_grade_scales (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                name TEXT NOT NULL,
                grade TEXT NOT NULL,
                min_marks REAL,
                max_marks REAL,
                grade_point REAL,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sms_fee_categories (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                amount REAL NOT NULL,
                academic_year TEXT,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sms_payments (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                student_id TEXT NOT NULL,
                fee_category_id TEXT,
                amount_due REAL NOT NULL,
                amount_paid REAL DEFAULT 0,
                payment_date TEXT,
                payment_method TEXT,
                receipt_number TEXT,
                status TEXT DEFAULT 'pending',
                recorded_by TEXT,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES sms_students(id)
            );

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
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sms_book_issues (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                book_id TEXT NOT NULL,
                student_id TEXT NOT NULL,
                issue_date TEXT,
                due_date TEXT,
                return_date TEXT,
                status TEXT DEFAULT 'issued',
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE,
                FOREIGN KEY (book_id) REFERENCES sms_books(id),
                FOREIGN KEY (student_id) REFERENCES sms_students(id)
            );

            CREATE TABLE IF NOT EXISTS sms_announcements (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                target_audience TEXT DEFAULT 'all',
                priority TEXT DEFAULT 'normal',
                is_published INTEGER DEFAULT 0,
                created_by TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sms_events (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                event_type TEXT,
                event_date TEXT NOT NULL,
                created_by TEXT,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sms_class_groups (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                name TEXT NOT NULL,
                program TEXT,
                level TEXT,
                capacity INTEGER DEFAULT 40,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sms_messages (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                recipient_id TEXT NOT NULL,
                subject TEXT,
                body TEXT,
                is_read INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );
        """)
        seed_if_empty(conn)


def seed_if_empty(conn: sqlite3.Connection) -> None:
    if conn.execute("SELECT COUNT(*) FROM sms_schools").fetchone()[0] > 0:
        return

    school_id = "SCH-1001"
    today = date.today().isoformat()

    conn.execute("INSERT INTO sms_schools (id, name, email, phone, address, password, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (school_id, "Greenfield College Ghana", "admin@greenfield.edu.gh", "+233 24 000 0000", "Accra, Greater Accra", "School@123", today))

    # Academic Year
    ay_id = "AY-2025"
    conn.execute("INSERT INTO sms_academic_years (id, school_id, name, start_date, end_date, is_current) VALUES (?, ?, ?, ?, ?, ?)",
        (ay_id, school_id, "2025-2026", "2025-09-01", "2026-08-31", 1))

    # Terms
    conn.execute("INSERT INTO sms_terms (id, school_id, academic_year_id, name, term_order, start_date, end_date, is_current) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("TERM-1", school_id, ay_id, "First Term", 1, "2025-09-01", "2025-12-15", 1))
    conn.execute("INSERT INTO sms_terms (id, school_id, academic_year_id, name, term_order, start_date, end_date, is_current) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("TERM-2", school_id, ay_id, "Second Term", 2, "2026-01-10", "2026-04-15", 0))

    # Departments
    conn.execute("INSERT INTO sms_departments (id, school_id, name, code) VALUES (?, ?, ?, ?)",
        ("DEPT-CS", school_id, "Computer Science", "CS"))
    conn.execute("INSERT INTO sms_departments (id, school_id, name, code) VALUES (?, ?, ?, ?)",
        ("DEPT-BUS", school_id, "Business Administration", "BUS"))
    conn.execute("INSERT INTO sms_departments (id, school_id, name, code) VALUES (?, ?, ?, ?)",
        ("DEPT-MTH", school_id, "Mathematics", "MTH"))

    # Programs
    conn.execute("INSERT INTO sms_programs (id, school_id, department_id, name, code) VALUES (?, ?, ?, ?, ?)",
        ("PROG-CS", school_id, "DEPT-CS", "Computer Science", "CS"))
    conn.execute("INSERT INTO sms_programs (id, school_id, department_id, name, code) VALUES (?, ?, ?, ?, ?)",
        ("PROG-BUS", school_id, "DEPT-BUS", "Business Administration", "BA"))

    # Levels
    conn.execute("INSERT INTO sms_levels (id, school_id, name, code, order_index) VALUES (?, ?, ?, ?, ?)",
        ("LVL-100", school_id, "Level 100", "100", 1))
    conn.execute("INSERT INTO sms_levels (id, school_id, name, code, order_index) VALUES (?, ?, ?, ?, ?)",
        ("LVL-200", school_id, "Level 200", "200", 2))
    conn.execute("INSERT INTO sms_levels (id, school_id, name, code, order_index) VALUES (?, ?, ?, ?, ?)",
        ("LVL-300", school_id, "Level 300", "300", 3))
    conn.execute("INSERT INTO sms_levels (id, school_id, name, code, order_index) VALUES (?, ?, ?, ?, ?)",
        ("LVL-400", school_id, "Level 400", "400", 4))

    conn.execute("INSERT INTO sms_staff (id, school_id, name, email, password, role, department, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("STF-1001", school_id, "Ms. Hannah Reed", "teacher@greenfield.edu.gh", "Teach@123", "Academic Officer", "Computer Science", "active", today))
    conn.execute("INSERT INTO sms_staff (id, school_id, name, email, password, role, department, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("STF-1002", school_id, "Mr. Kofi Mensah", "admin@greenfield.edu.gh", "School@123", "Administrator", "Administration", "active", today))

    conn.executemany("INSERT INTO sms_students (id, school_id, name, email, phone, program, level, status, password, joined_on) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [("STU-1001", school_id, "Daniel Agyekum", "daniel.agyekum@student.edu.gh", "+233 20 001 0081", "Computer Science", "200", "active", "Student@123", "2025-08-20"),
         ("STU-1002", school_id, "Lila Mensah", "lila.mensah@student.edu.gh", "+233 20 001 0082", "Business Administration", "100", "active", "Student@123", "2025-08-20"),
         ("STU-1003", school_id, "Kojo Tetteh", "kojo.tetteh@student.edu.gh", "+233 20 001 0083", "Computer Science", "100", "active", "Student@123", "2025-08-20")])

    conn.executemany("INSERT INTO sms_applications (id, school_id, full_name, dob, email, phone, address, program_first_choice, program_second_choice, notes, status, submitted_on) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [("APP-2001", school_id, "Esi Boateng", "2008-11-02", "esi.boateng@example.com", "+233 24 111 1001", "14 Cedar Street, Kumasi", "Biological Sciences", "Mathematics", "Science club lead", "pending", "2026-03-06"),
         ("APP-2002", school_id, "Jonah Mills", "2008-04-12", "jonah.mills@example.com", "+233 24 111 1002", "99 River Lane, Accra", "Computer Science", "Electrical Engineering", "Olympiad participant", "pending", "2026-03-07")])

    conn.executemany("INSERT INTO sms_courses (id, school_id, code, title, program, level, credits, seats, lecturer, active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [("COURSE-301", school_id, "CSC201", "Software Engineering Basics", "Computer Science", "200", 3, 40, "Ms. Hannah Reed", 1),
         ("COURSE-302", school_id, "BUS105", "Principles of Management", "Business Administration", "100", 3, 50, "Mr. Kofi Mensah", 1),
         ("COURSE-303", school_id, "CSC101", "Introduction to Programming", "Computer Science", "100", 3, 35, "Ms. Hannah Reed", 1)])

    conn.execute("INSERT INTO sms_registrations (id, school_id, student_id, term, registered_on) VALUES (?, ?, ?, ?, ?)",
        ("REG-5001", school_id, "STU-1001", "2026 Spring", "2026-02-11T10:12:00.000Z"))
    conn.execute("INSERT INTO sms_registration_courses (registration_id, course_id) VALUES (?, ?)", ("REG-5001", "COURSE-301"))

    conn.executemany("INSERT INTO sms_exam_results (id, school_id, student_id, term, subject, score, grade, grade_point, recorded_by, recorded_on) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [("RES-9001", school_id, "STU-1001", "2026 Spring", "CSC201", 78, "B", 3.5, "STF-1001", "2026-03-08"),
         ("RES-9002", school_id, "STU-1002", "2026 Spring", "BUS105", 85, "A", 4.0, "STF-1002", "2026-03-08")])

    # Grade Scales
    conn.executemany("INSERT INTO sms_grade_scales (id, school_id, name, grade, min_marks, max_marks, grade_point) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [("GS-1", school_id, "Standard", "A", 80, 100, 4.0),
         ("GS-2", school_id, "Standard", "B", 70, 79, 3.5),
         ("GS-3", school_id, "Standard", "C", 60, 69, 3.0),
         ("GS-4", school_id, "Standard", "D", 50, 59, 2.5),
         ("GS-5", school_id, "Standard", "F", 0, 49, 0.0)])

    # Fee Categories
    conn.executemany("INSERT INTO sms_fee_categories (id, school_id, name, description, amount, academic_year) VALUES (?, ?, ?, ?, ?, ?)",
        [("FEE-1", school_id, "Tuition", "Full tuition fee for academic year", 2500.00, "2025-2026"),
         ("FEE-2", school_id, "Registration", "Registration and admission fee", 150.00, "2025-2026"),
         ("FEE-3", school_id, "Library", "Library and resource fee", 100.00, "2025-2026")])

    # Payments
    conn.execute("INSERT INTO sms_payments (id, school_id, student_id, fee_category_id, amount_due, amount_paid, payment_date, payment_method, receipt_number, status, recorded_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("PAY-1", school_id, "STU-1001", "FEE-1", 2500.00, 2500.00, "2025-08-25", "Bank Transfer", "RCT-001", "paid", "STF-1002"))
    conn.execute("INSERT INTO sms_payments (id, school_id, student_id, fee_category_id, amount_due, amount_paid, payment_date, payment_method, receipt_number, status, recorded_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("PAY-2", school_id, "STU-1002", "FEE-1", 2500.00, 1500.00, "2025-08-26", "Mobile Money", "RCT-002", "partial", "STF-1002"))

    # Books
    conn.executemany("INSERT INTO sms_books (id, school_id, isbn, title, author, publisher, category, total_copies, available_copies) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [("BOOK-1", school_id, "978-0134685991", "Effective Java", "Joshua Bloch", "Addison-Wesley", "Programming", 3, 2),
         ("BOOK-2", school_id, "978-0135957059", "The Pragmatic Programmer", "David Thomas", "Addison-Wesley", "Programming", 2, 2),
         ("BOOK-3", school_id, "978-0321125217", "Domain-Driven Design", "Eric Evans", "Addison-Wesley", "Software Engineering", 2, 2)])

    # Announcements
    conn.executemany("INSERT INTO sms_announcements (id, school_id, title, content, target_audience, priority, is_published, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [("ANN-1", school_id, "Welcome to 2025-2026 Academic Year", "We are excited to welcome all students to the new academic year.", "all", "high", 1, "STF-1002", "2025-08-20"),
         ("ANN-2", school_id, "Course Registration Open", "Course registration for First Term is now open.", "students", "normal", 1, "STF-1001", "2025-09-01"),
         ("ANN-3", school_id, "Mid-Term Examinations", "Mid-term examinations will be held from November 15-20, 2025.", "students", "normal", 1, "STF-1001", "2025-10-15")])

    # Events
    conn.executemany("INSERT INTO sms_events (id, school_id, title, description, event_type, event_date, created_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [("EVT-1", school_id, "First Term Begins", "Start of academic year", "academic", "2025-09-01", "STF-1002"),
         ("EVT-2", school_id, "Mid-Term Break", "Mid-term holiday", "holiday", "2025-11-10", "STF-1002"),
         ("EVT-3", school_id, "Parent-Teacher Meeting", "Quarterly PTM", "meeting", "2025-10-25", "STF-1001")])

    # Class Groups
    conn.executemany("INSERT INTO sms_class_groups (id, school_id, name, program, level, capacity) VALUES (?, ?, ?, ?, ?, ?)",
        [("CLS-1", school_id, "CS Year 1 Group A", "Computer Science", "100", 35),
         ("CLS-2", school_id, "CS Year 2 Group A", "Computer Science", "200", 30)])

    # Create default courses
    create_default_courses_for_school(conn, school_id, "Academic Team")


def serialize_school(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "name": row["name"], "email": row["email"], "phone": row.get("phone", ""), "address": row.get("address", ""), "createdAt": row["created_at"]}


def serialize_staff(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "name": row["name"], "email": row["email"], "role": row["role"], "department": row["department"], "phone": row.get("phone", ""), "position": row.get("position", ""), "status": row["status"], "createdAt": row["created_at"]}


def serialize_student(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "name": row["name"], "email": row["email"], "phone": row.get("phone", ""), "program": row["program"], "level": row["level"], "gender": row.get("gender", ""), "status": row["status"], "guardianName": row.get("guardian_name", ""), "address": row.get("address", ""), "joinedOn": row["joined_on"]}


def find_school_for_login(conn, email: str, password: str):
    return conn.execute("SELECT * FROM sms_schools WHERE LOWER(email) = ? AND password = ?", (email.strip().lower(), password)).fetchone()


def find_staff_for_login(conn, school_id: str, identifier: str, password: str):
    normalized = identifier.strip().lower()
    return conn.execute("SELECT * FROM sms_staff WHERE school_id = ? AND (LOWER(email) = ? OR LOWER(id) = ?) AND password = ? AND status = 'active'",
        (school_id, normalized, normalized, password)).fetchone()


def find_student_for_login(conn, school_id: str, identifier: str, password: str):
    normalized = identifier.strip().lower()
    return conn.execute("SELECT * FROM sms_students WHERE school_id = ? AND (LOWER(id) = ? OR LOWER(email) = ?) AND password = ?",
        (school_id, normalized, normalized, password)).fetchone()


def unique_student_email(conn, school_id: str, desired_email: str, app_id: str) -> str:
    desired = desired_email.strip().lower()
    exists = conn.execute("SELECT 1 FROM sms_students WHERE school_id = ? AND LOWER(email) = ?", (school_id, desired)).fetchone()
    if not exists:
        return desired
    if "@" in desired:
        local_part, domain = desired.split("@", 1)
        return f"{local_part}+{app_id.lower()}@{domain}"
    return f"{app_id.lower()}@student.local"


def serialize_data(conn, school: sqlite3.Row) -> dict:
    school_id = school["id"]

    staff = [serialize_staff(r) for r in conn.execute("SELECT * FROM sms_staff WHERE school_id = ? ORDER BY created_at DESC", (school_id,)).fetchall()]
    students = [serialize_student(r) for r in conn.execute("SELECT * FROM sms_students WHERE school_id = ? ORDER BY id", (school_id,)).fetchall()]

    applications = []
    for r in conn.execute("SELECT * FROM sms_applications WHERE school_id = ? ORDER BY submitted_on DESC", (school_id,)).fetchall():
        applications.append({"id": r["id"], "fullName": r["full_name"], "dob": r["dob"], "email": r["email"], "phone": r["phone"], "address": r["address"], "programFirstChoice": r["program_first_choice"], "programSecondChoice": r.get("program_second_choice", ""), "notes": r.get("notes", ""), "status": r["status"], "submittedOn": r["submitted_on"]})

    courses = []
    for r in conn.execute("SELECT * FROM sms_courses WHERE school_id = ? ORDER BY code", (school_id,)).fetchall():
        courses.append({"id": r["id"], "code": r["code"], "title": r["title"], "program": r["program"], "level": r["level"], "credits": r["credits"], "seats": r["seats"], "lecturer": r["lecturer"], "active": bool(r["active"]), "description": r.get("description", "")})

    registrations = []
    for r in conn.execute("SELECT r.id, r.student_id, r.term, r.registered_on, GROUP_CONCAT(rc.course_id) as course_ids FROM sms_registrations r LEFT JOIN sms_registration_courses rc ON rc.registration_id = r.id WHERE r.school_id = ? GROUP BY r.id", (school_id,)).fetchall():
        registrations.append({"id": r["id"], "studentId": r["student_id"], "term": r["term"], "registeredOn": r["registered_on"], "courseIds": r["course_ids"].split(",") if r["course_ids"] else []})

    attendance_payload = []
    for r in conn.execute("SELECT * FROM sms_attendance WHERE school_id = ? ORDER BY date DESC", (school_id,)).fetchall():
        records = conn.execute("SELECT student_id, present FROM sms_attendance_records WHERE attendance_id = ?", (r["id"],)).fetchall()
        attendance_payload.append({"id": r["id"], "date": r["date"], "courseId": r["course_id"], "presentStudentIds": [rec["student_id"] for rec in records if rec["present"] == 1], "absentStudentIds": [rec["student_id"] for rec in records if rec["present"] == 0], "takenBy": r.get("taken_by", "")})

    exam_results = []
    for r in conn.execute("SELECT er.*, s.name as student_name, st.name as recorded_by_name FROM sms_exam_results er JOIN sms_students s ON s.id = er.student_id LEFT JOIN sms_staff st ON st.id = er.recorded_by WHERE er.school_id = ? ORDER BY er.recorded_on DESC", (school_id,)).fetchall():
        exam_results.append({"id": r["id"], "studentId": r["student_id"], "studentName": r["student_name"], "term": r["term"], "subject": r["subject"], "score": r["score"], "grade": r["grade"], "gradePoint": r.get("grade_point", 0), "recordedBy": r.get("recorded_by", ""), "recordedByName": r.get("recorded_by_name", ""), "recordedOn": r["recorded_on"]})

    departments = [{"id": r["id"], "name": r["name"], "code": r.get("code", ""), "description": r.get("description", "")} for r in conn.execute("SELECT * FROM sms_departments WHERE school_id = ?", (school_id,)).fetchall()]
    programs = [{"id": r["id"], "name": r["name"], "code": r.get("code", ""), "description": r.get("description", ""), "departmentId": r.get("department_id", "")} for r in conn.execute("SELECT * FROM sms_programs WHERE school_id = ?", (school_id,)).fetchall()]
    levels = [{"id": r["id"], "name": r["name"], "code": r["code"], "orderIndex": r.get("order_index", 0)} for r in conn.execute("SELECT * FROM sms_levels WHERE school_id = ? ORDER BY order_index", (school_id,)).fetchall()]
    academic_years = [{"id": r["id"], "name": r["name"], "startDate": r.get("start_date", ""), "endDate": r.get("end_date", ""), "isCurrent": bool(r.get("is_current", 0))} for r in conn.execute("SELECT * FROM sms_academic_years WHERE school_id = ?", (school_id,)).fetchall()]
    terms = [{"id": r["id"], "name": r["name"], "academicYearId": r.get("academic_year_id", ""), "termOrder": r.get("term_order", 0), "startDate": r.get("start_date", ""), "endDate": r.get("end_date", ""), "isCurrent": bool(r.get("is_current", 0))} for r in conn.execute("SELECT * FROM sms_terms WHERE school_id = ? ORDER BY term_order", (school_id,)).fetchall()]
    fee_categories = [{"id": r["id"], "name": r["name"], "description": r.get("description", ""), "amount": r["amount"], "academicYear": r.get("academic_year", "")} for r in conn.execute("SELECT * FROM sms_fee_categories WHERE school_id = ?", (school_id,)).fetchall()]
    
    payments = []
    for r in conn.execute("SELECT p.*, s.name as student_name FROM sms_payments p JOIN sms_students s ON s.id = p.student_id WHERE p.school_id = ? ORDER BY p.payment_date DESC", (school_id,)).fetchall():
        payments.append({"id": r["id"], "studentId": r["student_id"], "studentName": r["student_name"], "amountDue": r["amount_due"], "amountPaid": r.get("amount_paid", 0), "paymentDate": r.get("payment_date", ""), "paymentMethod": r.get("payment_method", ""), "receiptNumber": r.get("receipt_number", ""), "status": r.get("status", "pending")})

    books = [{"id": r["id"], "isbn": r.get("isbn", ""), "title": r["title"], "author": r.get("author", ""), "publisher": r.get("publisher", ""), "category": r.get("category", ""), "totalCopies": r.get("total_copies", 0), "availableCopies": r.get("available_copies", 0)} for r in conn.execute("SELECT * FROM sms_books WHERE school_id = ?", (school_id,)).fetchall()]
    announcements = [{"id": r["id"], "title": r["title"], "content": r.get("content", ""), "targetAudience": r.get("target_audience", "all"), "priority": r.get("priority", "normal"), "isPublished": bool(r.get("is_published", 0)), "createdAt": r["created_at"]} for r in conn.execute("SELECT * FROM sms_announcements WHERE school_id = ? ORDER BY created_at DESC", (school_id,)).fetchall()]
    events = [{"id": r["id"], "title": r["title"], "description": r.get("description", ""), "eventType": r.get("event_type", ""), "eventDate": r["event_date"]} for r in conn.execute("SELECT * FROM sms_events WHERE school_id = ? ORDER BY event_date", (school_id,)).fetchall()]
    class_groups = [{"id": r["id"], "name": r["name"], "program": r.get("program", ""), "level": r.get("level", ""), "capacity": r.get("capacity", 40)} for r in conn.execute("SELECT * FROM sms_class_groups WHERE school_id = ?", (school_id,)).fetchall()]
    grade_scales = [{"id": r["id"], "name": r["name"], "grade": r["grade"], "minMarks": r.get("min_marks", 0), "maxMarks": r.get("max_marks", 100), "gradePoint": r.get("grade_point", 0)} for r in conn.execute("SELECT * FROM sms_grade_scales WHERE school_id = ? ORDER BY min_marks DESC", (school_id,)).fetchall()]

    return {"meta": {"schoolId": school_id, "schoolName": school["name"], "generatedAt": datetime.utcnow().isoformat() + "Z"}, "staff": staff, "students": students, "applications": applications, "courses": courses, "registrations": registrations, "attendance": attendance_payload, "examResults": exam_results, "departments": departments, "programs": programs, "levels": levels, "academicYears": academic_years, "terms": terms, "feeCategories": fee_categories, "payments": payments, "books": books, "announcements": announcements, "events": events, "classGroups": class_groups, "gradeScales": grade_scales}


class SMSRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8")) if raw else {}

    def require_school(self):
        school_id = self.headers.get("X-School-ID", "").strip()
        if not school_id:
            self.send_json({"ok": False, "message": "Select your school account first."}, HTTPStatus.BAD_REQUEST)
            return None
        with get_conn() as conn:
            school = conn.execute("SELECT * FROM sms_schools WHERE id = ?", (school_id,)).fetchone()
        if not school:
            self.send_json({"ok": False, "message": "School account not found."}, HTTPStatus.NOT_FOUND)
            return None
        return school

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            self.send_json({"ok": True, "message": "School Management API is running."})
            return
        if path == "/api/data":
            school = self.require_school()
            if not school:
                return
            with get_conn() as conn:
                data = serialize_data(conn, school)
            self.send_json({"ok": True, "data": data})
            return
        if path.startswith("/api/schools/"):
            school_id = unquote(path.split("/api/schools/", 1)[1])
            with get_conn() as conn:
                school = conn.execute("SELECT * FROM sms_schools WHERE id = ?", (school_id,)).fetchone()
            if not school:
                self.send_json({"ok": False, "message": "School not found."}, HTTPStatus.NOT_FOUND)
                return
            self.send_json({"ok": True, "school": serialize_school(school)})
            return
        if path.startswith("/api/students/"):
            school = self.require_school()
            if not school:
                return
            student_id = unquote(path.split("/api/students/", 1)[1])
            with get_conn() as conn:
                row = conn.execute("SELECT * FROM sms_students WHERE id = ? AND school_id = ?", (student_id, school["id"])).fetchone()
            if not row:
                self.send_json({"ok": False, "message": "Student not found."}, HTTPStatus.NOT_FOUND)
                return
            self.send_json({"ok": True, "student": serialize_student(row)})
            return
        if path.startswith("/api/staff/"):
            school = self.require_school()
            if not school:
                return
            staff_id = unquote(path.split("/", 3)[3])
            with get_conn() as conn:
                row = conn.execute("SELECT * FROM sms_staff WHERE id = ? AND school_id = ?", (staff_id, school["id"])).fetchone()
            if not row:
                self.send_json({"ok": False, "message": "Staff not found."}, HTTPStatus.NOT_FOUND)
                return
            self.send_json({"ok": True, "staff": serialize_staff(row)})
            return
        # New endpoints
        if path == "/api/departments":
            school = self.require_school()
            if not school:
                return
            with get_conn() as conn:
                depts = [{"id": r["id"], "name": r["name"], "code": r.get("code", "")} for r in conn.execute("SELECT * FROM sms_departments WHERE school_id = ?", (school["id"],)).fetchall()]
            self.send_json({"ok": True, "departments": depts})
            return
        if path == "/api/programs":
            school = self.require_school()
            if not school:
                return
            with get_conn() as conn:
                progs = [{"id": r["id"], "name": r["name"], "code": r.get("code", "")} for r in conn.execute("SELECT * FROM sms_programs WHERE school_id = ?", (school["id"],)).fetchall()]
            self.send_json({"ok": True, "programs": progs})
            return
        if path == "/api/levels":
            school = self.require_school()
            if not school:
                return
            with get_conn() as conn:
                lvls = [{"id": r["id"], "name": r["name"], "code": r["code"]} for r in conn.execute("SELECT * FROM sms_levels WHERE school_id = ? ORDER BY order_index", (school["id"],)).fetchall()]
            self.send_json({"ok": True, "levels": lvls})
            return
        if path == "/api/events":
            school = self.require_school()
            if not school:
                return
            with get_conn() as conn:
                evts = [{"id": r["id"], "title": r["title"], "eventDate": r["event_date"], "eventType": r.get("event_type", "")} for r in conn.execute("SELECT * FROM sms_events WHERE school_id = ? ORDER BY event_date", (school["id"],)).fetchall()]
            self.send_json({"ok": True, "events": evts})
            return
        if path == "/api/class-groups":
            school = self.require_school()
            if not school:
                return
            with get_conn() as conn:
                cgs = [{"id": r["id"], "name": r["name"], "program": r.get("program", ""), "level": r.get("level", "")} for r in conn.execute("SELECT * FROM sms_class_groups WHERE school_id = ?", (school["id"],)).fetchall()]
            self.send_json({"ok": True, "classGroups": cgs})
            return
        super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            body = self.read_json_body()
        except json.JSONDecodeError:
            self.send_json({"ok": False, "message": "Invalid JSON body."}, HTTPStatus.BAD_REQUEST)
            return

        # School Auth
        if path == "/api/schools/register":
            self.handle_school_register(body)
            return
        if path == "/api/schools/login":
            self.handle_school_login(body)
            return

        # Admissions
        if path == "/api/admissions":
            self.handle_admissions(body)
            return

        # Auth
        if path == "/api/auth/student-login":
            self.handle_student_login(body)
            return
        if path in {"/api/auth/staff-login", "/api/auth/teacher-login"}:
            self.handle_staff_login(body)
            return

        # Course registration
        if path == "/api/registrations":
            self.handle_registrations(body)
            return

        # Staff
        if path == "/api/staff":
            self.handle_add_staff(body)
            return

        # Exams
        if path == "/api/exam-results":
            self.handle_exam_results(body)
            return

        # Applications
        match = re.match(r"^/api/applications/([^/]+)/approve$", path)
        if match:
            self.handle_approve_application(unquote(match.group(1)), body)
            return
        match = re.match(r"^/api/applications/([^/]+)/reject$", path)
        if match:
            self.handle_reject_application(unquote(match.group(1)))
            return

        # Courses
        if path == "/api/courses":
            self.handle_add_course(body)
            return
        match = re.match(r"^/api/courses/([^/]+)/toggle$", path)
        if match:
            self.handle_toggle_course(unquote(match.group(1)))
            return

        # Attendance
        if path == "/api/attendance":
            self.handle_attendance(body)
            return

        # NEW ENDPOINTS
        
        # Departments
        if path == "/api/departments":
            self.handle_add_department(body)
            return
        
        # Programs
        if path == "/api/programs":
            self.handle_add_program(body)
            return
        
        # Levels
        if path == "/api/levels":
            self.handle_add_level(body)
            return
        
        # Fee Categories
        if path == "/api/fee-categories":
            self.handle_add_fee_category(body)
            return
        
        # Payments
        if path == "/api/payments":
            self.handle_add_payment(body)
            return
        
        # Books
        if path == "/api/books":
            self.handle_add_book(body)
            return
        
        # Book Issues
        if path == "/api/book-issues":
            self.handle_issue_book(body)
            return
        
        # Announcements
        if path == "/api/announcements":
            self.handle_add_announcement(body)
            return
        
        # Events
        if path == "/api/events":
            self.handle_add_event(body)
            return
        
        # Class Groups
        if path == "/api/class-groups":
            self.handle_add_class_group(body)
            return
        
        # Grade Scales
        if path == "/api/grade-scales":
            self.handle_add_grade_scale(body)
            return

        self.send_json({"ok": False, "message": "Unknown endpoint."}, HTTPStatus.NOT_FOUND)

    def handle_school_register(self, body: dict) -> None:
        school_name = str(body.get("schoolName", "")).strip()
        school_email = str(body.get("schoolEmail", "")).strip().lower()
        school_password = str(body.get("password", ""))
        admin_name = str(body.get("adminName", "")).strip() or "School Admin"
        admin_email = str(body.get("adminEmail", "")).strip().lower() or school_email
        admin_password = str(body.get("adminPassword", "")).strip() or "Staff@123"

        if not school_name or not school_email or not school_password:
            self.send_json({"ok": False, "message": "School name, email and password are required."}, HTTPStatus.BAD_REQUEST)
            return

        with get_conn() as conn:
            if conn.execute("SELECT 1 FROM sms_schools WHERE LOWER(email) = ?", (school_email,)).fetchone():
                self.send_json({"ok": False, "message": "School account already exists."}, HTTPStatus.BAD_REQUEST)
                return
            school_id = next_id(conn, "sms_schools", "SCH-")
            staff_id = next_id(conn, "sms_staff", "STF-")
            created_at = date.today().isoformat()
            conn.execute("INSERT INTO sms_schools (id, name, email, phone, address, password, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (school_id, school_name, school_email, str(body.get("schoolPhone", "")).strip(), str(body.get("schoolAddress", "")).strip(), school_password, created_at))
            conn.execute("INSERT INTO sms_staff (id, school_id, name, email, password, role, department, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?)",
                (staff_id, school_id, admin_name, admin_email, admin_password, "Administrator", "Administration", created_at))
            create_default_courses_for_school(conn, school_id, admin_name)

        self.send_json({"ok": True, "message": "School account created.", "school": {"id": school_id, "name": school_name}, "defaultStaff": {"id": staff_id, "email": admin_email, "password": admin_password}})

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
        if any(not str(body.get(f, "")).strip() for f in required):
            self.send_json({"ok": False, "message": "Please fill all required fields."}, HTTPStatus.BAD_REQUEST)
            return
        with get_conn() as conn:
            app_id = next_id(conn, "sms_applications", "APP-")
            conn.execute("INSERT INTO sms_applications (id, school_id, full_name, dob, email, phone, address, program_first_choice, program_second_choice, notes, status, submitted_on) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)",
                (app_id, school["id"], body["fullName"].strip(), body["dob"], body["email"].strip().lower(), body["phone"].strip(), body["address"].strip(), body["programFirstChoice"].strip(), str(body.get("programSecondChoice", "")).strip(), str(body.get("notes", "")).strip(), date.today().isoformat()))
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
        self.send_json({"ok": True, "staff": serialize_staff(row), "teacher": serialize_staff(row)})

    def handle_registrations(self, body: dict) -> None:
        school = self.require_school()
        if not school:
            return
        identifier = str(body.get("studentIdentifier", "")).strip()
        password = str(body.get("password", ""))
        term = str(body.get("term", "")).strip()
        course_ids = body.get("courseIds", [])
        if not term or not course_ids:
            self.send_json({"ok": False, "message": "Term and courses are required."}, HTTPStatus.BAD_REQUEST)
            return
        with get_conn() as conn:
            student = find_student_for_login(conn, school["id"], identifier, password)
            if not student:
                self.send_json({"ok": False, "message": "Student authentication failed."}, HTTPStatus.UNAUTHORIZED)
                return
            placeholders = ",".join("?" for _ in course_ids)
            active_rows = conn.execute(f"SELECT id FROM sms_courses WHERE school_id = ? AND id IN ({placeholders}) AND active = 1", tuple([school["id"]] + list(course_ids))).fetchall()
            active_ids = {r["id"] for r in active_rows}
            if len(active_ids) != len(set(course_ids)):
                self.send_json({"ok": False, "message": "One or more courses are invalid."}, HTTPStatus.BAD_REQUEST)
                return
            existing = conn.execute("SELECT id FROM sms_registrations WHERE school_id = ? AND student_id = ? AND term = ?", (school["id"], student["id"], term)).fetchone()
            if existing:
                conn.execute("DELETE FROM sms_registration_courses WHERE registration_id = ?", (existing["id"],))
                conn.execute("DELETE FROM sms_registrations WHERE id = ?", (existing["id"],))
            reg_id = next_id(conn, "sms_registrations", "REG-")
            conn.execute("INSERT INTO sms_registrations (id, school_id, student_id, term, registered_on) VALUES (?, ?, ?, ?, ?)", (reg_id, school["id"], student["id"], term, datetime.utcnow().isoformat() + "Z"))
            conn.executemany("INSERT INTO sms_registration_courses (registration_id, course_id) VALUES (?, ?)", [(reg_id, c) for c in course_ids])
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
            if conn.execute("SELECT 1 FROM sms_staff WHERE school_id = ? AND LOWER(email) = ?", (school["id"], email)).fetchone():
                self.send_json({"ok": False, "message": "Staff email already exists."}, HTTPStatus.BAD_REQUEST)
                return
            staff_id = next_id(conn, "sms_staff", "STF-")
            conn.execute("INSERT INTO sms_staff (id, school_id, name, email, password, role, department, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?)",
                (staff_id, school["id"], name, email, password, role, department, date.today().isoformat()))
        self.send_json({"ok": True, "message": "Staff account added.", "staffId": staff_id, "defaultPassword": password})

    def handle_exam_results(self, body: dict) -> None:
        school = self.require_school()
        if not school:
            return
        student_id = str(body.get("studentId", "")).strip()
        term = str(body.get("term", "")).strip()
        subject = str(body.get("subject", "")).strip()
        try:
            score = float(body.get("score", 0))
        except (TypeError, ValueError):
            self.send_json({"ok": False, "message": "Score must be numeric."}, HTTPStatus.BAD_REQUEST)
            return
        if score < 0 or score > 100:
            self.send_json({"ok": False, "message": "Score must be between 0 and 100."}, HTTPStatus.BAD_REQUEST)
            return
        grade = str(body.get("grade", "")).strip().upper() or score_to_grade(score)
        with get_conn() as conn:
            if not conn.execute("SELECT 1 FROM sms_students WHERE id = ? AND school_id = ?", (student_id, school["id"])).fetchone():
                self.send_json({"ok": False, "message": "Student not found."}, HTTPStatus.NOT_FOUND)
                return
            result_id = next_id(conn, "sms_exam_results", "RES-")
            conn.execute("INSERT INTO sms_exam_results (id, school_id, student_id, term, subject, score, grade, grade_point, recorded_by, recorded_on) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (result_id, school["id"], student_id, term, subject, score, grade, score_to_grade_point(score), str(body.get("staffId", "")).strip() or None, date.today().isoformat()))
        self.send_json({"ok": True, "message": "Exam result recorded."})

    def handle_approve_application(self, app_id: str, body: dict) -> None:
        school = self.require_school()
        if not school:
            return
        staff_id = str(body.get("teacherId", "")).strip() or str(body.get("staffId", "")).strip()
        with get_conn() as conn:
            app = conn.execute("SELECT * FROM sms_applications WHERE id = ? AND school_id = ?", (app_id, school["id"])).fetchone()
            if not app:
                self.send_json({"ok": False, "message": "Application not found."}, HTTPStatus.NOT_FOUND)
                return
            if app["status"] != "pending":
                self.send_json({"ok": False, "message": "Application already processed."}, HTTPStatus.BAD_REQUEST)
                return
            student_id = next_id(conn, "sms_students", "STU-")
            student_email = unique_student_email(conn, school["id"], app["email"], app_id)
            conn.execute("UPDATE sms_applications SET status = 'approved' WHERE id = ?", (app_id,))
            conn.execute("INSERT INTO sms_students (id, school_id, name, email, phone, program, level, status, password, joined_on, approved_by, source_application_id) VALUES (?, ?, ?, ?, ?, ?, '100', 'active', 'Student@123', ?, ?, ?)",
                (student_id, school["id"], app["full_name"], student_email, app["phone"], app["program_first_choice"], date.today().isoformat(), staff_id or None, app_id))
            ann_id = next_id(conn, "sms_announcements", "ANN-")
            conn.execute("INSERT INTO sms_announcements (id, school_id, title, content, target_audience, priority, is_published, created_by, created_at) VALUES (?, ?, ?, ?, 'all', 'normal', 1, ?, ?)",
                (ann_id, school["id"], f"{app['full_name']} admitted", f"New student admitted to {app['program_first_choice']}", staff_id or None, date.today().isoformat()))
        self.send_json({"ok": True, "message": "Application approved. Student account created with password Student@123."})

    def handle_reject_application(self, app_id: str) -> None:
        school = self.require_school()
        if not school:
            return
        with get_conn() as conn:
            app = conn.execute("SELECT * FROM sms_applications WHERE id = ? AND school_id = ?", (app_id, school["id"])).fetchone()
            if not app:
                self.send_json({"ok": False, "message": "Application not found."}, HTTPStatus.NOT_FOUND)
                return
            if app["status"] != "pending":
                self.send_json({"ok": False, "message": "Application already processed."}, HTTPStatus.BAD_REQUEST)
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
        if not code or not title or not program or not level:
            self.send_json({"ok": False, "message": "Fill all required course fields."}, HTTPStatus.BAD_REQUEST)
            return
        with get_conn() as conn:
            try:
                course_id = next_id(conn, "sms_courses", "COURSE-")
                conn.execute("INSERT INTO sms_courses (id, school_id, code, title, program, level, credits, seats, lecturer, active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
                    (course_id, school["id"], code, title, program, level, int(body.get("credits", 3)), int(body.get("seats", 30)), str(body.get("teacherName", "")).strip() or "Faculty"))
            except sqlite3.IntegrityError:
                self.send_json({"ok": False, "message": "Course code already exists."}, HTTPStatus.BAD_REQUEST)
                return
        self.send_json({"ok": True, "message": "Course added."})

    def handle_toggle_course(self, course_id: str) -> None:
        school = self.require_school()
        if not school:
            return
        with get_conn() as conn:
            course = conn.execute("SELECT active FROM sms_courses WHERE id = ? AND school_id = ?", (course_id, school["id"])).fetchone()
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
        with get_conn() as conn:
            if not conn.execute("SELECT 1 FROM sms_courses WHERE id = ? AND school_id = ?", (course_id, school["id"])).fetchone():
                self.send_json({"ok": False, "message": "Course not found."}, HTTPStatus.NOT_FOUND)
                return
            existing = conn.execute("SELECT id FROM sms_attendance WHERE school_id = ? AND date = ? AND course_id = ?", (school["id"], attendance_date, course_id)).fetchone()
            if existing:
                conn.execute("DELETE FROM sms_attendance_records WHERE attendance_id = ?", (existing["id"],))
                conn.execute("DELETE FROM sms_attendance WHERE id = ?", (existing["id"],))
            attendance_id = next_id(conn, "sms_attendance", "ATT-")
            conn.execute("INSERT INTO sms_attendance (id, school_id, date, course_id, taken_by) VALUES (?, ?, ?, ?, ?)", (attendance_id, school["id"], attendance_date, course_id, staff_id or None))
            students = conn.execute("SELECT id FROM sms_students WHERE school_id = ?", (school["id"],)).fetchall()
            present_set = {str(p) for p in present_ids}
            conn.executemany("INSERT INTO sms_attendance_records (attendance_id, student_id, present) VALUES (?, ?, ?)",
                [(attendance_id, s["id"], 1 if s["id"] in present_set else 0) for s in students])
        self.send_json({"ok": True, "message": "Attendance saved."})

    # NEW HANDLERS
    
    def handle_add_department(self, body: dict) -> None:
        school = self.require_school()
        if not school:
            return
        name = str(body.get("name", "")).strip()
        code = str(body.get("code", "")).strip().upper()
        if not name:
            self.send_json({"ok": False, "message": "Department name is required."}, HTTPStatus.BAD_REQUEST)
            return
        with get_conn() as conn:
            dept_id = next_id(conn, "sms_departments", "DEPT-")
            conn.execute("INSERT INTO sms_departments (id, school_id, name, code) VALUES (?, ?, ?, ?)", (dept_id, school["id"], name, code))
        self.send_json({"ok": True, "message": "Department added.", "departmentId": dept_id})

    def handle_add_program(self, body: dict) -> None:
        school = self.require_school()
        if not school:
            return
        name = str(body.get("name", "")).strip()
        code = str(body.get("code", "")).strip().upper()
        if not name:
            self.send_json({"ok": False, "message": "Program name is required."}, HTTPStatus.BAD_REQUEST)
            return
        with get_conn() as conn:
            prog_id = next_id(conn, "sms_programs", "PROG-")
            conn.execute("INSERT INTO sms_programs (id, school_id, name, code, department_id) VALUES (?, ?, ?, ?, ?)", (prog_id, school["id"], name, code, str(body.get("departmentId", "")).strip() or None))
        self.send_json({"ok": True, "message": "Program added.", "programId": prog_id})

    def handle_add_level(self, body: dict) -> None:
        school = self.require_school()
        if not school:
            return
        name = str(body.get("name", "")).strip()
        code = str(body.get("code", "")).strip()
        if not name or not code:
            self.send_json({"ok": False, "message": "Level name and code are required."}, HTTPStatus.BAD_REQUEST)
            return
        with get_conn() as conn:
            lvl_id = next_id(conn, "sms_levels", "LVL-")
            conn.execute("INSERT INTO sms_levels (id, school_id, name, code, order_index) VALUES (?, ?, ?, ?, ?)", (lvl_id, school["id"], name, code, int(body.get("orderIndex", 1))))
        self.send_json({"ok": True, "message": "Level added.", "levelId": lvl_id})

    def handle_add_fee_category(self, body: dict) -> None:
        school = self.require_school()
        if not school:
            return
        name = str(body.get("name", "")).strip()
        amount = float(body.get("amount", 0))
        if not name or amount <= 0:
            self.send_json({"ok": False, "message": "Valid fee name and amount are required."}, HTTPStatus.BAD_REQUEST)
            return
        with get_conn() as conn:
            fee_id = next_id(conn, "sms_fee_categories", "FEE-")
            conn.execute("INSERT INTO sms_fee_categories (id, school_id, name, description, amount, academic_year) VALUES (?, ?, ?, ?, ?, ?)",
                (fee_id, school["id"], name, str(body.get("description", "")).strip(), amount, str(body.get("academicYear", "")).strip()))
        self.send_json({"ok": True, "message": "Fee category added.", "feeCategoryId": fee_id})

    def handle_add_payment(self, body: dict) -> None:
        school = self.require_school()
        if not school:
            return
        student_id = str(body.get("studentId", "")).strip()
        amount_paid = float(body.get("amountPaid", 0))
        if not student_id or amount_paid <= 0:
            self.send_json({"ok": False, "message": "Student ID and amount paid are required."}, HTTPStatus.BAD_REQUEST)
            return
        with get_conn() as conn:
            if not conn.execute("SELECT 1 FROM sms_students WHERE id = ? AND school_id = ?", (student_id, school["id"])).fetchone():
                self.send_json({"ok": False, "message": "Student not found."}, HTTPStatus.NOT_FOUND)
                return
            pay_id = next_id(conn, "sms_payments", "PAY-")
            receipt = f"RCT-{next_id(conn, 'sms_payments', 'PAY-').split('-')[1].zfill(4)}"
            conn.execute("INSERT INTO sms_payments (id, school_id, student_id, amount_due, amount_paid, payment_date, payment_method, receipt_number, status, recorded_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'paid', ?)",
                (pay_id, school["id"], student_id, float(body.get("amountDue", amount_paid)), amount_paid, date.today().isoformat(), str(body.get("paymentMethod", "")).strip() or "Cash", receipt, str(body.get("staffId", "")).strip() or None))
        self.send_json({"ok": True, "message": "Payment recorded.", "paymentId": pay_id, "receiptNumber": receipt})

    def handle_add_book(self, body: dict) -> None:
        school = self.require_school()
        if not school:
            return
        title = str(body.get("title", "")).strip()
        if not title:
            self.send_json({"ok": False, "message": "Book title is required."}, HTTPStatus.BAD_REQUEST)
            return
        with get_conn() as conn:
            book_id = next_id(conn, "sms_books", "BOOK-")
            conn.execute("INSERT INTO sms_books (id, school_id, isbn, title, author, publisher, category, total_copies, available_copies) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (book_id, school["id"], str(body.get("isbn", "")).strip(), title, str(body.get("author", "")).strip(), str(body.get("publisher", "")).strip(), str(body.get("category", "")).strip(), int(body.get("totalCopies", 1)), int(body.get("availableCopies", 1))))
        self.send_json({"ok": True, "message": "Book added.", "bookId": book_id})

    def handle_issue_book(self, body: dict) -> None:
        school = self.require_school()
        if not school:
            return
        book_id = str(body.get("bookId", "")).strip()
        student_id = str(body.get("studentId", "")).strip()
        if not book_id or not student_id:
            self.send_json({"ok": False, "message": "Book ID and Student ID are required."}, HTTPStatus.BAD_REQUEST)
            return
        with get_conn() as conn:
            book = conn.execute("SELECT * FROM sms_books WHERE id = ? AND school_id = ?", (book_id, school["id"])).fetchone()
            if not book or book["available_copies"] < 1:
                self.send_json({"ok": False, "message": "Book not available."}, HTTPStatus.BAD_REQUEST)
                return
            issue_id = next_id(conn, "sms_book_issues", "ISSU-")
            due_date = (date.today() + timedelta(days=14)).isoformat()
            conn.execute("INSERT INTO sms_book_issues (id, school_id, book_id, student_id, issue_date, due_date, status) VALUES (?, ?, ?, ?, ?, ?, 'issued')",
                (issue_id, school["id"], book_id, student_id, date.today().isoformat(), due_date))
            conn.execute("UPDATE sms_books SET available_copies = available_copies - 1 WHERE id = ?", (book_id,))
        self.send_json({"ok": True, "message": "Book issued.", "issueId": issue_id, "dueDate": due_date})

    def handle_add_announcement(self, body: dict) -> None:
        school = self.require_school()
        if not school:
            return
        title = str(body.get("title", "")).strip()
        if not title:
            self.send_json({"ok": False, "message": "Announcement title is required."}, HTTPStatus.BAD_REQUEST)
            return
        with get_conn() as conn:
            ann_id = next_id(conn, "sms_announcements", "ANN-")
            conn.execute("INSERT INTO sms_announcements (id, school_id, title, content, target_audience, priority, is_published, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)",
                (ann_id, school["id"], title, str(body.get("content", "")).strip(), str(body.get("targetAudience", "all")).strip(), str(body.get("priority", "normal")).strip(), str(body.get("staffId", "")).strip() or None, date.today().isoformat()))
        self.send_json({"ok": True, "message": "Announcement published.", "announcementId": ann_id})

    def handle_add_event(self, body: dict) -> None:
        school = self.require_school()
        if not school:
            return
        title = str(body.get("title", "")).strip()
        event_date = str(body.get("eventDate", "")).strip()
        if not title or not event_date:
            self.send_json({"ok": False, "message": "Event title and date are required."}, HTTPStatus.BAD_REQUEST)
            return
        with get_conn() as conn:
            evt_id = next_id(conn, "sms_events", "EVT-")
            conn.execute("INSERT INTO sms_events (id, school_id, title, description, event_type, event_date, created_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (evt_id, school["id"], title, str(body.get("description", "")).strip(), str(body.get("eventType", "")).strip(), event_date, str(body.get("staffId", "")).strip() or None))
        self.send_json({"ok": True, "message": "Event created.", "eventId": evt_id})

    def handle_add_class_group(self, body: dict) -> None:
        school = self.require_school()
        if not school:
            return
        name = str(body.get("name", "")).strip()
        if not name:
            self.send_json({"ok": False, "message": "Class group name is required."}, HTTPStatus.BAD_REQUEST)
            return
        with get_conn() as conn:
            cls_id = next_id(conn, "sms_class_groups", "CLS-")
            conn.execute("INSERT INTO sms_class_groups (id, school_id, name, program, level, capacity) VALUES (?, ?, ?, ?, ?, ?)",
                (cls_id, school["id"], name, str(body.get("program", "")).strip(), str(body.get("level", "")).strip(), int(body.get("capacity", 40))))
        self.send_json({"ok": True, "message": "Class group created.", "classGroupId": cls_id})

    def handle_add_grade_scale(self, body: dict) -> None:
        school = self.require_school()
        if not school:
            return
        grade = str(body.get("grade", "")).strip().upper()
        min_marks = float(body.get("minMarks", 0))
        if not grade:
            self.send_json({"ok": False, "message": "Grade is required."}, HTTPStatus.BAD_REQUEST)
            return
        with get_conn() as conn:
            gs_id = next_id(conn, "sms_grade_scales", "GS-")
            conn.execute("INSERT INTO sms_grade_scales (id, school_id, name, grade, min_marks, max_marks, grade_point) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (gs_id, school["id"], str(body.get("name", "")).strip() or "Standard", grade, min_marks, float(body.get("maxMarks", 100)), float(body.get("gradePoint", 0))))
        self.send_json({"ok": True, "message": "Grade scale added.", "gradeScaleId": gs_id})


def run_server() -> None:
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), SMSRequestHandler)
    print(f"School Management System Server running at http://{HOST}:{PORT}")
    print(f"Database file: {DB_PATH}")
    print("Enhanced features: Academic Years, Terms, Departments, Programs, Levels, Fee Management, Library, Events, Class Groups")
    server.serve_forever()


if __name__ == "__main__":
    run_server()

