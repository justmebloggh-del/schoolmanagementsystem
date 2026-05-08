-- ============================================================
-- Run this in your Supabase SQL editor ONCE to create tables.
-- Dashboard → SQL Editor → New Query → paste → Run
-- ============================================================

CREATE TABLE IF NOT EXISTS sms_schools (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    address TEXT,
    password TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sms_staff (
    id TEXT PRIMARY KEY,
    school_id TEXT NOT NULL REFERENCES sms_schools(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    role TEXT NOT NULL,
    department TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    password TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(school_id, email)
);

CREATE TABLE IF NOT EXISTS sms_students (
    id TEXT PRIMARY KEY,
    school_id TEXT NOT NULL REFERENCES sms_schools(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    program TEXT NOT NULL,
    level TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    password TEXT NOT NULL,
    joined_on TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sms_applications (
    id TEXT PRIMARY KEY,
    school_id TEXT NOT NULL REFERENCES sms_schools(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    dob TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    address TEXT NOT NULL,
    program_first_choice TEXT NOT NULL,
    program_second_choice TEXT,
    notes TEXT,
    status TEXT DEFAULT 'pending',
    submitted_on TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sms_courses (
    id TEXT PRIMARY KEY,
    school_id TEXT NOT NULL REFERENCES sms_schools(id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    title TEXT NOT NULL,
    program TEXT NOT NULL,
    level TEXT NOT NULL,
    credits INTEGER DEFAULT 3,
    seats INTEGER DEFAULT 30,
    lecturer TEXT NOT NULL,
    active BOOLEAN DEFAULT true,
    description TEXT,
    UNIQUE(school_id, code)
);

CREATE TABLE IF NOT EXISTS sms_registrations (
    id TEXT PRIMARY KEY,
    school_id TEXT NOT NULL,
    student_id TEXT NOT NULL,
    term TEXT NOT NULL,
    registered_on TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sms_registration_courses (
    registration_id TEXT NOT NULL,
    course_id TEXT NOT NULL,
    PRIMARY KEY (registration_id, course_id)
);

CREATE TABLE IF NOT EXISTS sms_attendance (
    id TEXT PRIMARY KEY,
    school_id TEXT NOT NULL,
    date TEXT NOT NULL,
    course_id TEXT NOT NULL,
    taken_by TEXT
);

CREATE TABLE IF NOT EXISTS sms_attendance_records (
    attendance_id TEXT NOT NULL,
    student_id TEXT NOT NULL,
    present BOOLEAN NOT NULL DEFAULT false,
    PRIMARY KEY (attendance_id, student_id)
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
    recorded_on TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sms_job_applications (
    id TEXT PRIMARY KEY,
    school_id TEXT NOT NULL,
    school_name TEXT,
    position TEXT NOT NULL,
    full_name TEXT NOT NULL,
    dob TEXT,
    email TEXT NOT NULL,
    phone TEXT,
    address TEXT,
    qualification TEXT,
    experience INTEGER DEFAULT 0,
    department TEXT,
    cv_file_name TEXT,
    notes TEXT,
    status TEXT DEFAULT 'pending',
    submitted_on TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sms_announcements (
    id TEXT PRIMARY KEY,
    school_id TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    created_at TEXT NOT NULL
);
