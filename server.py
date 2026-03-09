#!/usr/bin/env python3
"""School Management System API + static file server (multi-school)."""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import date, datetime
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
    suffix = identifier[len(prefix) :]
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
        """
        INSERT INTO sms_courses (id, school_id, code, title, program, level, credits, seats, lecturer, active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        payload,
    )


def ensure_default_courses(conn: sqlite3.Connection) -> None:
    school_rows = conn.execute("SELECT id FROM sms_schools ORDER BY id").fetchall()
    for school in school_rows:
        create_default_courses_for_school(conn, school["id"])


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sms_schools (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT,
                address TEXT,
                password TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sms_staff (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                department TEXT NOT NULL,
                status TEXT NOT NULL,
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
                status TEXT NOT NULL,
                submitted_on TEXT NOT NULL,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sms_students (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                program TEXT NOT NULL,
                level TEXT NOT NULL,
                status TEXT NOT NULL,
                password TEXT NOT NULL,
                joined_on TEXT NOT NULL,
                approved_by TEXT,
                source_application_id TEXT,
                UNIQUE (school_id, email),
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE,
                FOREIGN KEY (approved_by) REFERENCES sms_staff(id),
                FOREIGN KEY (source_application_id) REFERENCES sms_applications(id)
            );

            CREATE TABLE IF NOT EXISTS sms_courses (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                code TEXT NOT NULL,
                title TEXT NOT NULL,
                program TEXT NOT NULL,
                level TEXT NOT NULL,
                credits INTEGER NOT NULL,
                seats INTEGER NOT NULL,
                lecturer TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
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
                FOREIGN KEY (course_id) REFERENCES sms_courses(id),
                FOREIGN KEY (taken_by) REFERENCES sms_staff(id)
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
                recorded_by TEXT,
                recorded_on TEXT NOT NULL,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES sms_students(id),
                FOREIGN KEY (recorded_by) REFERENCES sms_staff(id)
            );

            CREATE TABLE IF NOT EXISTS sms_announcements (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (school_id) REFERENCES sms_schools(id) ON DELETE CASCADE
            );
            """
        )
        seed_if_empty(conn)
        ensure_default_courses(conn)


def seed_if_empty(conn: sqlite3.Connection) -> None:
    school_count = conn.execute("SELECT COUNT(*) AS count FROM sms_schools").fetchone()["count"]
    if school_count > 0:
        return

    school_id = "SCH-1001"
    today = date.today().isoformat()

    conn.execute(
        """
        INSERT INTO sms_schools (id, name, email, phone, address, password, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            school_id,
            "Greenfield College Ghana",
            "admin@greenfield.edu.gh",
            "+233 24 000 0000",
            "Accra, Greater Accra",
            "School@123",
            today,
        ),
    )

    conn.execute(
        """
        INSERT INTO sms_staff (id, school_id, name, email, password, role, department, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "STF-1001",
            school_id,
            "Ms. Hannah Reed",
            "teacher@greenfield.edu.gh",
            "Teach@123",
            "Academic Officer",
            "Academic Affairs",
            "active",
            today,
        ),
    )

    conn.executemany(
        """
        INSERT INTO sms_students (id, school_id, name, email, phone, program, level, status, password, joined_on)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "STU-1001",
                school_id,
                "Daniel Agyekum",
                "daniel.agyekum@student.edu.gh",
                "+233 20 001 0081",
                "Computer Science",
                "200",
                "active",
                "Student@123",
                "2025-08-20",
            ),
            (
                "STU-1002",
                school_id,
                "Lila Mensah",
                "lila.mensah@student.edu.gh",
                "+233 20 001 0082",
                "Business Administration",
                "100",
                "active",
                "Student@123",
                "2025-08-20",
            ),
        ],
    )

    conn.executemany(
        """
        INSERT INTO sms_applications (
            id, school_id, full_name, dob, email, phone, address,
            program_first_choice, program_second_choice, notes, status, submitted_on
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "APP-2001",
                school_id,
                "Esi Boateng",
                "2008-11-02",
                "esi.boateng@example.com",
                "+233 24 111 1001",
                "14 Cedar Street, Kumasi",
                "Biological Sciences",
                "Mathematics",
                "Science club lead",
                "pending",
                "2026-03-06",
            ),
            (
                "APP-2002",
                school_id,
                "Jonah Mills",
                "2008-04-12",
                "jonah.mills@example.com",
                "+233 24 111 1002",
                "99 River Lane, Accra",
                "Computer Science",
                "Electrical Engineering",
                "Olympiad participant",
                "pending",
                "2026-03-07",
            ),
        ],
    )

    conn.executemany(
        """
        INSERT INTO sms_courses (id, school_id, code, title, program, level, credits, seats, lecturer, active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "COURSE-301",
                school_id,
                "CSC201",
                "Software Engineering Basics",
                "Computer Science",
                "200",
                3,
                40,
                "Ms. Hannah Reed",
                1,
            ),
            (
                "COURSE-302",
                school_id,
                "BUS105",
                "Principles of Management",
                "Business Administration",
                "100",
                3,
                50,
                "Ms. Hannah Reed",
                1,
            ),
        ],
    )

    conn.execute(
        """
        INSERT INTO sms_registrations (id, school_id, student_id, term, registered_on)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "REG-5001",
            school_id,
            "STU-1001",
            "2026 Spring",
            "2026-02-11T10:12:00.000Z",
        ),
    )

    conn.executemany(
        """
        INSERT INTO sms_registration_courses (registration_id, course_id)
        VALUES (?, ?)
        """,
        [("REG-5001", "COURSE-301")],
    )

    conn.execute(
        """
        INSERT INTO sms_exam_results (id, school_id, student_id, term, subject, score, grade, recorded_by, recorded_on)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "RES-9001",
            school_id,
            "STU-1001",
            "2026 Spring",
            "CSC201",
            78,
            "B",
            "STF-1001",
            "2026-03-08",
        ),
    )

    conn.executemany(
        """
        INSERT INTO sms_announcements (id, school_id, title, created_at)
        VALUES (?, ?, ?, ?)
        """,
        [
            ("ANN-1", school_id, "Admissions interview window opens March 22.", "2026-03-05"),
            ("ANN-2", school_id, "Course registration closes April 5, 2026.", "2026-03-06"),
            ("ANN-3", school_id, "Mid-term exam recording starts April 10, 2026.", "2026-03-07"),
        ],
    )


def serialize_school(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "phone": row["phone"] or "",
        "address": row["address"] or "",
        "createdAt": row["created_at"],
    }


def serialize_staff(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "role": row["role"],
        "department": row["department"],
        "status": row["status"],
        "createdAt": row["created_at"],
    }


def serialize_student(row: sqlite3.Row, include_password: bool = False) -> dict:
    payload = {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "phone": row["phone"],
        "program": row["program"],
        "level": row["level"],
        "status": row["status"],
        "joinedOn": row["joined_on"],
        "sourceApplicationId": row["source_application_id"] or "",
    }
    if include_password:
        payload["password"] = row["password"]
    return payload


def find_school_for_login(conn: sqlite3.Connection, email: str, password: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM sms_schools WHERE LOWER(email) = ? AND password = ?",
        (email.strip().lower(), password),
    ).fetchone()


def find_staff_for_login(conn: sqlite3.Connection, school_id: str, identifier: str, password: str) -> sqlite3.Row | None:
    normalized = identifier.strip().lower()
    return conn.execute(
        """
        SELECT * FROM sms_staff
        WHERE school_id = ?
          AND (LOWER(email) = ? OR LOWER(id) = ?)
          AND password = ?
          AND status = 'active'
        """,
        (school_id, normalized, normalized, password),
    ).fetchone()


def find_student_for_login(conn: sqlite3.Connection, school_id: str, identifier: str, password: str) -> sqlite3.Row | None:
    normalized = identifier.strip().lower()
    return conn.execute(
        """
        SELECT * FROM sms_students
        WHERE school_id = ?
          AND (LOWER(id) = ? OR LOWER(email) = ?)
          AND password = ?
        """,
        (school_id, normalized, normalized, password),
    ).fetchone()


def unique_student_email(conn: sqlite3.Connection, school_id: str, desired_email: str, app_id: str) -> str:
    desired = desired_email.strip().lower()
    exists = conn.execute(
        "SELECT 1 FROM sms_students WHERE school_id = ? AND LOWER(email) = ?",
        (school_id, desired),
    ).fetchone()
    if not exists:
        return desired

    if "@" in desired:
        local_part, domain = desired.split("@", 1)
        return f"{local_part}+{app_id.lower()}@{domain}"
    return f"{app_id.lower()}@student.local"


def serialize_data(conn: sqlite3.Connection, school: sqlite3.Row) -> dict:
    school_id = school["id"]

    staff = [
        serialize_staff(row)
        for row in conn.execute(
            "SELECT * FROM sms_staff WHERE school_id = ? ORDER BY created_at DESC, id DESC",
            (school_id,),
        ).fetchall()
    ]

    students = [
        serialize_student(row)
        for row in conn.execute(
            "SELECT * FROM sms_students WHERE school_id = ? ORDER BY id",
            (school_id,),
        ).fetchall()
    ]

    applications = []
    for row in conn.execute(
        "SELECT * FROM sms_applications WHERE school_id = ? ORDER BY submitted_on DESC, id DESC",
        (school_id,),
    ).fetchall():
        applications.append(
            {
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
                "submittedOn": row["submitted_on"],
            }
        )

    courses = []
    for row in conn.execute(
        "SELECT * FROM sms_courses WHERE school_id = ? ORDER BY code",
        (school_id,),
    ).fetchall():
        courses.append(
            {
                "id": row["id"],
                "code": row["code"],
                "title": row["title"],
                "program": row["program"],
                "level": row["level"],
                "credits": row["credits"],
                "seats": row["seats"],
                "lecturer": row["lecturer"],
                "active": bool(row["active"]),
            }
        )

    registrations: list[dict] = []
    reg_rows = conn.execute(
        """
        SELECT r.id, r.student_id, r.term, r.registered_on, rc.course_id
        FROM sms_registrations r
        LEFT JOIN sms_registration_courses rc ON rc.registration_id = r.id
        WHERE r.school_id = ?
        ORDER BY r.registered_on DESC, r.id DESC
        """,
        (school_id,),
    ).fetchall()
    reg_map: dict[str, dict] = {}
    for row in reg_rows:
        reg = reg_map.get(row["id"])
        if not reg:
            reg = {
                "id": row["id"],
                "studentId": row["student_id"],
                "term": row["term"],
                "registeredOn": row["registered_on"],
                "courseIds": [],
            }
            reg_map[row["id"]] = reg
        if row["course_id"]:
            reg["courseIds"].append(row["course_id"])
    registrations = list(reg_map.values())

    attendance_payload = []
    for row in conn.execute(
        "SELECT * FROM sms_attendance WHERE school_id = ? ORDER BY date DESC, id DESC",
        (school_id,),
    ).fetchall():
        records = conn.execute(
            "SELECT student_id, present FROM sms_attendance_records WHERE attendance_id = ?",
            (row["id"],),
        ).fetchall()
        present = [record["student_id"] for record in records if record["present"] == 1]
        absent = [record["student_id"] for record in records if record["present"] == 0]
        attendance_payload.append(
            {
                "id": row["id"],
                "date": row["date"],
                "courseId": row["course_id"],
                "presentStudentIds": present,
                "absentStudentIds": absent,
                "takenBy": row["taken_by"] or "",
            }
        )

    exam_results = []
    for row in conn.execute(
        """
        SELECT er.*, s.name AS student_name, st.name AS recorded_by_name
        FROM sms_exam_results er
        JOIN sms_students s ON s.id = er.student_id
        LEFT JOIN sms_staff st ON st.id = er.recorded_by
        WHERE er.school_id = ?
        ORDER BY er.recorded_on DESC, er.id DESC
        """,
        (school_id,),
    ).fetchall():
        exam_results.append(
            {
                "id": row["id"],
                "studentId": row["student_id"],
                "studentName": row["student_name"],
                "term": row["term"],
                "subject": row["subject"],
                "score": row["score"],
                "grade": row["grade"],
                "recordedBy": row["recorded_by"] or "",
                "recordedByName": row["recorded_by_name"] or "",
                "recordedOn": row["recorded_on"],
            }
        )

    announcements = [
        {"id": row["id"], "title": row["title"], "createdAt": row["created_at"]}
        for row in conn.execute(
            "SELECT * FROM sms_announcements WHERE school_id = ? ORDER BY created_at DESC, id DESC",
            (school_id,),
        ).fetchall()
    ]

    return {
        "meta": {
            "schoolId": school_id,
            "schoolName": school["name"],
            "generatedAt": datetime.utcnow().isoformat() + "Z",
        },
        "staff": staff,
        "teachers": staff,
        "students": students,
        "applications": applications,
        "courses": courses,
        "registrations": registrations,
        "attendance": attendance_payload,
        "examResults": exam_results,
        "announcements": announcements,
    }


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
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def require_school(self) -> sqlite3.Row | None:
        school_id = self.headers.get("X-School-ID", "").strip()
        if not school_id:
            self.send_json(
                {"ok": False, "message": "Select your school account first."},
                HTTPStatus.BAD_REQUEST,
            )
            return None

        with get_conn() as conn:
            school = conn.execute(
                "SELECT * FROM sms_schools WHERE id = ?",
                (school_id,),
            ).fetchone()

        if not school:
            self.send_json(
                {"ok": False, "message": "School account not found. Please sign in again."},
                HTTPStatus.NOT_FOUND,
            )
            return None
        return school

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path

        if path == "/api/health":
            self.send_json({"ok": True, "message": "API is healthy."})
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
                row = conn.execute(
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
