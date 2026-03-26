
-- ============================================================================
-- School Management System - Supabase Database Schema
-- ============================================================================
-- This schema covers all aspects of managing an academic institution
-- Including: Students, Staff, Courses, Attendance, Exams, Finance, Library
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- 1. SCHOOLS (Multi-tenant support)
-- ============================================================================
CREATE TABLE IF NOT EXISTS schools (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    phone TEXT,
    address TEXT,
    logo_url TEXT,
    tagline TEXT,
    established_date DATE,
    website TEXT,
    region TEXT,
    country TEXT DEFAULT 'Ghana',
    timezone TEXT DEFAULT 'Africa/Accra',
    currency TEXT DEFAULT 'GHS',
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 2. ACADEMIC YEARS
-- ============================================================================
CREATE TABLE IF NOT EXISTS academic_years (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID REFERENCES schools(id) ON DELETE CASCADE,
    name TEXT NOT NULL, -- e.g., "2025-2026"
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_current BOOLEAN DEFAULT false,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(school_id, name)
);

-- ============================================================================
-- 3. TERMS/SEMESTERS
-- ============================================================================
CREATE TABLE IF NOT EXISTS terms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID REFERENCES schools(id) ON DELETE CASCADE,
    academic_year_id UUID REFERENCES academic_years(id) ON DELETE CASCADE,
    name TEXT NOT NULL, -- "First Term", "Second Semester"
    term_order INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_current BOOLEAN DEFAULT false,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(academic_year_id, name)
);

-- ============================================================================
-- 4. DEPARTMENTS/FACULTIES
-- ============================================================================
CREATE TABLE IF NOT EXISTS departments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID REFERENCES schools(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    code TEXT,
    description TEXT,
    head_id UUID, -- Will reference staff table
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(school_id, code)
);

-- ============================================================================
-- 5. PROGRAMS/COURSES OF STUDY
-- ============================================================================
CREATE TABLE IF NOT EXISTS programs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID REFERENCES schools(id) ON DELETE CASCADE,
    department_id UUID REFERENCES departments(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    code TEXT,
    description TEXT,
    duration_years INT DEFAULT 3,
    total_credits INT DEFAULT 120,
    tuition_fee NUMERIC DEFAULT 0,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(school_id, code)
);

-- ============================================================================
-- 6. LEVELS/YEAR GROUPS
-- ============================================================================
CREATE TABLE IF NOT EXISTS levels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID REFERENCES schools(id) ON DELETE CASCADE,
    name TEXT NOT NULL, -- "Year 1", "Level 100"
    code TEXT NOT NULL, -- "100", "200"
    order_index INT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(school_id, code)
);

-- ============================================================================
-- 7. STAFF/EMPLOYEES
-- ============================================================================
CREATE TABLE IF NOT EXISTS staff (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID REFERENCES schools(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id), -- Supabase Auth
    staff_id TEXT, -- Staff ID like "STF-1001"
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    gender TEXT,
    date_of_birth DATE,
    department_id UUID REFERENCES departments(id),
    role TEXT NOT NULL, -- "Teacher", "Admin", "Accountant", "Librarian", "Principal"
    position TEXT,
    qualification TEXT,
    specialization TEXT,
    employment_date DATE,
    salary NUMERIC,
    status TEXT DEFAULT 'active', -- active, on_leave, suspended, terminated
    photo_url TEXT,
    emergency_contact_name TEXT,
    emergency_contact_phone TEXT,
    address TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(school_id, staff_id)
);

-- ============================================================================
-- 8. STUDENTS
-- ============================================================================
CREATE TABLE IF NOT EXISTS students (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID REFERENCES schools(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id), -- Supabase Auth
    student_id TEXT, -- Student ID like "STU-1001"
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    gender TEXT,
    date_of_birth DATE,
    place_of_birth TEXT,
    program_id UUID REFERENCES programs(id),
    level_id UUID REFERENCES levels(id),
    academic_year_id UUID REFERENCES academic_years(id), -- Year of entry
    entry_term_id UUID REFERENCES terms(id),
    status TEXT DEFAULT 'active', -- active, graduated, suspended, withdrawn, deferred
    student_type TEXT DEFAULT 'regular', -- regular, transfer, visiting
    photo_url TEXT,
    guardian_name TEXT,
    guardian_relationship TEXT,
    guardian_phone TEXT,
    guardian_email TEXT,
    guardian_occupation TEXT,
    guardian_address TEXT,
    emergency_contact_name TEXT,
    emergency_contact_phone TEXT,
    address TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(school_id, student_id)
);

-- ============================================================================
-- 9. COURSES/SUBJECTS
-- ============================================================================
CREATE TABLE IF NOT EXISTS courses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID REFERENCES schools(id) ON DELETE CASCADE,
    program_id UUID REFERENCES programs(id) ON DELETE SET NULL,
    level_id UUID REFERENCES levels(id),
    department_id UUID REFERENCES departments(id),
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    credits INT DEFAULT 3,
    lecture_hours INT DEFAULT 2,
    practical_hours INT DEFAULT 1,
    teacher_id UUID REFERENCES staff(id),
    seats INT DEFAULT 30,
    is_active BOOLEAN DEFAULT true,
    is_elective BOOLEAN DEFAULT false,
    prerequisite TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(school_id, code)
);

-- ============================================================================
-- 10. CLASS GROUPS
-- ============================================================================
CREATE TABLE IF NOT EXISTS class_groups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID REFERENCES schools(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    program_id UUID REFERENCES programs(id),
    level_id UUID REFERENCES levels(id),
    academic_year_id UUID REFERENCES academic_years(id),
    term_id UUID REFERENCES terms(id),
    capacity INT DEFAULT 40,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(school_id, name, academic_year_id)
);

-- ============================================================================
-- 11. CLASS GROUP MEMBERS (Students in a class)
-- ============================================================================
CREATE TABLE IF NOT EXISTS class_group_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    class_group_id UUID REFERENCES class_groups(id) ON DELETE CASCADE,
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    role TEXT DEFAULT 'student', -- student, representative
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(class_group_id, student_id)
);

-- ============================================================================
-- 12. COURSE REGISTRATIONS
-- ============================================================================
CREATE TABLE IF NOT EXISTS course_registrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID REFERENCES schools(id) ON DELETE CASCADE,
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    term_id UUID REFERENCES terms(id),
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'registered', -- registered, dropped, completed
    registered_by UUID REFERENCES staff(id),
    registration_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(student_id, term_id, course_id)
);

-- ============================================================================
-- 13. TEACHING ASSIGNMENTS
-- ============================================================================
CREATE TABLE IF NOT EXISTS teaching_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID REFERENCES schools(id) ON DELETE CASCADE,
    teacher_id UUID REFERENCES staff(id) ON DELETE CASCADE,
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    term_id UUID REFERENCES terms(id),
    class_group_id UUID REFERENCES class_groups(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(teacher_id, course_id, term_id)
);

-- ============================================================================
-- 14. DAILY ATTENDANCE
-- ============================================================================
CREATE TABLE IF NOT EXISTS attendance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID REFERENCES schools(id) ON DELETE CASCADE,
    term_id UUID REFERENCES terms(id),
    course_id UUID REFERENCES courses(id),
    class_group_id UUID REFERENCES class_groups(id),
    date DATE NOT NULL,
    status TEXT NOT NULL, -- present, absent, late, excused
    remarks TEXT,
    marked_by UUID REFERENCES staff(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 15. STUDENT ATTENDANCE RECORDS
-- ============================================================================
CREATE TABLE IF NOT EXISTS attendance_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    attendance_id UUID REFERENCES attendance(id) ON DELETE CASCADE,
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    status TEXT NOT NULL, -- present, absent, late, excused
    remarks TEXT,
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(attendance_id, student_id)
);

-- ============================================================================
-- 16. EXAMINATIONS
-- ============================================================================
CREATE TABLE IF NOT EXISTS exams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID REFERENCES schools(id) ON DELETE CASCADE,
    term_id UUID REFERENCES terms(id),
    course_id UUID REFERENCES courses(id),
    exam_type TEXT NOT NULL, -- Midterm, Final, Quiz, Assignment, Project
    title TEXT,
    description TEXT,
    exam_date DATE NOT NULL,
    start_time TIME,
    end_time TIME,
    total_marks NUMERIC NOT NULL,
    passing_marks NUMERIC,
    is_active BOOLEAN DEFAULT true,
    created_by UUID REFERENCES staff(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 17. EXAM RESULTS/GRADES
-- ============================================================================
CREATE TABLE IF NOT EXISTS exam_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID REFERENCES schools(id) ON DELETE CASCADE,
    exam_id UUID REFERENCES exams(id) ON DELETE CASCADE,
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    marks_obtained NUMERIC,
    grade TEXT,
    grade_point NUMERIC,
    remarks TEXT,
    is_released BOOLEAN DEFAULT false,
    recorded_by UUID REFERENCES staff(id),
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(exam_id, student_id)
);

-- ============================================================================
-- 18. GRADE SCALES
-- ============================================================================
CREATE TABLE IF NOT EXISTS grade_scales (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID REFERENCES schools(id) ON DELETE CASCADE,
    name TEXT NOT NULL, -- "Standard A-F", "Percentage"
    grade TEXT NOT NULL,
    min_marks NUMERIC,
    max_marks NUMERIC,
    grade_point NUMERIC,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(school_id, name, grade)
);

-- ============================================================================
-- 19. FEE CATEGORIES
-- ============================================================================
CREATE TABLE IF NOT EXISTS fee_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID REFERENCES schools(id) ON DELETE CASCADE,
    name TEXT NOT NULL, -- Tuition, Registration, Library, Sports, Hostel
    description TEXT,
    amount NUMERIC NOT NULL,
    academic_year_id UUID REFERENCES academic_years(id),
    program_id UUID REFERENCES programs(id), -- null = all programs
    level_id UUID REFERENCES levels(id), -- null = all levels
    is_mandatory BOOLEAN DEFAULT true,
    due_date DATE,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 20. FEE PAYMENTS
-- ============================================================================
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID REFERENCES schools(id) ON DELETE CASCADE,
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    academic_year_id UUID REFERENCES academic_years(id),
    amount_due NUMERIC NOT NULL,
    amount_paid NUMERIC DEFAULT 0,
    payment_date DATE,
    payment_method TEXT, -- cash, bank_transfer, mobile_money
    transaction_ref TEXT,
    receipt_number TEXT,
    recorded_by UUID REFERENCES staff(id),
    status TEXT DEFAULT 'partial', -- pending, partial, paid
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 21. PAYMENT ITEMS
-- ============================================================================
CREATE TABLE IF NOT EXISTS payment_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    payment_id UUID REFERENCES payments(id) ON DELETE CASCADE,
    fee_category_id UUID REFERENCES fee_categories(id),
    amount_due NUMERIC NOT NULL,
    amount_paid NUMERIC DEFAULT 0,
    UNIQUE(payment_id, fee_category_id)
);

-- ============================================================================
-- 22. LIBRARY BOOKS
-- ============================================================================
CREATE TABLE IF NOT EXISTS books (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID REFERENCES schools(id) ON DELETE CASCADE,
    isbn TEXT,
    title TEXT NOT NULL,
    author TEXT,
    publisher TEXT,
    edition TEXT,
    category TEXT,
    total_copies INT DEFAULT 1,
    available_copies INT DEFAULT 1,
    shelf_location TEXT,
    cost NUMERIC,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 23. BOOK ISSUES
-- ============================================================================
CREATE TABLE IF NOT EXISTS book_issues (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID REFERENCES schools(id) ON DELETE CASCADE,
    book_id UUID REFERENCES books(id) ON DELETE CASCADE,
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    issue_date DATE DEFAULT CURRENT_DATE,
    due_date DATE NOT NULL,
    return_date DATE,
    return_status TEXT DEFAULT 'pending', -- pending, returned, lost, damaged
    fine_amount NUMERIC DEFAULT 0,
    remarks TEXT,
    issued_by UUID REFERENCES staff(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 24. ANNOUNCEMENTS
-- ============================================================================
CREATE TABLE IF NOT EXISTS announcements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID REFERENCES schools(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT,
    target_audience TEXT, -- all, students, staff, parents
    priority TEXT DEFAULT 'normal', -- urgent, high, normal, low
    attachment_url TEXT,
    start_date DATE,
    end_date DATE,
    is_published BOOLEAN DEFAULT false,
    created_by UUID REFERENCES staff(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 25. MESSAGES
-- ============================================================================
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID REFERENCES schools(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL,
    sender_type TEXT, -- staff, student
    recipient_id UUID NOT NULL,
    recipient_type TEXT,
    subject TEXT,
    body TEXT,
    is_read BOOLEAN DEFAULT false,
    is_archived BOOLEAN DEFAULT false,
    parent_id UUID REFERENCES messages(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 26. EVENTS/CALENDAR
-- ============================================================================
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID REFERENCES schools(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    event_type TEXT, -- academic, exam, holiday, meeting
    start_date DATE NOT NULL,
    end_date DATE,
    all_day BOOLEAN DEFAULT true,
    color TEXT,
    created_by UUID REFERENCES staff(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 27. USER ROLES & PERMISSIONS
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID REFERENCES schools(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL, -- admin, teacher, student, parent, accountant
    can_manage_students BOOLEAN DEFAULT false,
    can_manage_staff BOOLEAN DEFAULT false,
    can_manage_courses BOOLEAN DEFAULT false,
    can_manage_attendance BOOLEAN DEFAULT false,
    can_manage_exams BOOLEAN DEFAULT false,
    can_manage_finance BOOLEAN DEFAULT false,
    can_manage_library BOOLEAN DEFAULT false,
    can_view_reports BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(school_id, user_id)
);

-- ============================================================================
-- 28. ACTIVITY LOG
-- ============================================================================
CREATE TABLE IF NOT EXISTS activity_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID REFERENCES schools(id) ON DELETE CASCADE,
    user_id UUID,
    action TEXT NOT NULL,
    table_name TEXT,
    record_id UUID,
    details JSONB,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_students_school ON students(school_id);
CREATE INDEX IF NOT EXISTS idx_students_program ON students(program_id);
CREATE INDEX IF NOT EXISTS idx_students_status ON students(status);
CREATE INDEX IF NOT EXISTS idx_staff_school ON staff(school_id);
CREATE INDEX IF NOT EXISTS idx_staff_department ON staff(department_id);
CREATE INDEX IF NOT EXISTS idx_courses_school ON courses(school_id);
CREATE INDEX IF NOT EXISTS idx_courses_program ON courses(program_id);
CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date);
CREATE INDEX IF NOT EXISTS idx_attendance_records ON attendance_records(attendance_id);
CREATE INDEX IF NOT EXISTS idx_exam_results ON exam_results(exam_id);
CREATE INDEX IF NOT EXISTS idx_payments_student ON payments(student_id);
CREATE INDEX IF NOT EXISTS idx_book_issues_student ON book_issues(student_id);

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_schools_updated_at BEFORE UPDATE ON schools
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_staff_updated_at BEFORE UPDATE ON staff
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_students_updated_at BEFORE UPDATE ON students
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_courses_updated_at BEFORE UPDATE ON courses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Function to generate student ID
CREATE OR REPLACE FUNCTION generate_student_id(school_code TEXT, year TEXT)
RETURNS TEXT AS $$
DECLARE
    next_num INT;
    new_id TEXT;
BEGIN
    SELECT COALESCE(MAX(CAST(SUBSTRING(student_id FROM 5 FOR LENGTH(student_id)) AS INT)), 0) + 1
    INTO next_num
    FROM students
    WHERE school_id IN (SELECT id FROM schools WHERE code = school_code);
    
    new_id := 'STU' || year || LPAD(next_num::TEXT, 4, '0');
    RETURN new_id;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate GPA
CREATE OR REPLACE FUNCTION calculate_gpa(student_uuid UUID)
RETURNS NUMERIC AS $$
DECLARE
    total_points NUMERIC := 0;
    total_credits INT := 0;
    gpa NUMERIC := 0;
BEGIN
    SELECT 
        COALESCE(SUM(er.grade_point * c.credits), 0),
        COALESCE(SUM(c.credits), 0)
    INTO total_points, total_credits
    FROM exam_results er
    JOIN courses c ON c.id = (
        SELECT course_id FROM exams WHERE id = er.exam_id
    )
    WHERE er.student_id = student_uuid 
    AND er.grade_point IS NOT NULL;
    
    IF total_credits > 0 THEN
        gpa := total_points / total_credits;
    END IF;
    
    RETURN ROUND(gpa, 2);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SEED DATA
-- ============================================================================

-- Insert default school (Demo School)
INSERT INTO schools (id, name, email, phone, address, tagline, country, status)
VALUES (
    '550e8400-e29b-41d4-a716-446655440001',
    'Greenfield College Ghana',
    'admin@greenfield.edu.gh',
    '+233 24 000 0000',
    'Accra, Greater Accra Region',
    'Excellence in Education',
    'Ghana',
    'active'
) ON CONFLICT DO NOTHING;

-- Insert academic year
INSERT INTO academic_years (id, school_id, name, start_date, end_date, is_current, status)
VALUES (
    '550e8400-e29b-41d4-a716-446655440002',
    '550e8400-e29b-41d4-a716-446655440001',
    '2025-2026',
    '2025-09-01',
    '2026-08-31',
    true,
    'active'
) ON CONFLICT DO NOTHING;

-- Insert terms
INSERT INTO terms (id, school_id, academic_year_id, name, term_order, start_date, end_date, is_current, status)
VALUES 
    ('550e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440002', 'First Term', 1, '2025-09-01', '2025-12-15', true, 'active'),
    ('550e8400-e29b-41d4-a716-446655440004', '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440002', 'Second Term', 2, '2026-01-10', '2026-04-15', false, 'active'),
    ('550e8400-e29b-41d4-a716-446655440005', '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440002', 'Third Term', 3, '2026-05-01', '2026-08-31', false, 'active')
ON CONFLICT DO NOTHING;

-- Insert departments
INSERT INTO departments (id, school_id, name, code, description, status)
VALUES 
    ('550e8400-e29b-41d4-a716-446655440006', '550e8400-e29b-41d4-a716-446655440001', 'Computer Science', 'CS', 'Department of Computer Science', 'active'),
    ('550e8400-e29b-41d4-a716-446655440007', '550e8400-e29b-41d4-a716-446655440001', 'Business Administration', 'BUS', 'Department of Business Studies', 'active'),
    ('550e8400-e29b-41d4-a716-446655440008', '550e8400-e29b-41d4-a716-446655440001', 'Mathematics', 'MTH', 'Department of Mathematics', 'active'),
    ('550e8400-e29b-41d4-a716-446655440009', '550e8400-e29b-41d4-a716-446655440001', 'Biological Sciences', 'BIO', 'Department of Biology', 'active')
ON CONFLICT DO NOTHING;

-- Insert programs
INSERT INTO programs (id, school_id, department_id, name, code, description, duration_years, status)
VALUES 
    ('550e8400-e29b-41d4-a716-446655440010', '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440006', 'Computer Science', 'CS', 'Bachelor of Science in Computer Science', 4, 'active'),
    ('550e8400-e29b-41d4-a716-446655440011', '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440007', 'Business Administration', 'BA', 'Bachelor of Business Administration', 4, 'active'),
    ('550e8400-e29b-41d4-a716-446655440012', '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440008', 'Mathematics', 'MTH', 'Bachelor of Science in Mathematics', 4, 'active'),
    ('550e8400-e29b-41d4-a716-446655440013', '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440009', 'Biological Sciences', 'BIO', 'Bachelor of Science in Biological Sciences', 4, 'active')
ON CONFLICT DO NOTHING;

-- Insert levels
INSERT INTO levels (id, school_id, name, code, order_index)
VALUES 
    ('550e8400-e29b-41d4-a716-446655440014', '550e8400-e29b-41d4-a716-446655440001', 'Level 100', '100', 1),
    ('550e8400-e29b-41d4-a716-446655440015', '550e8400-e29b-41d4-a716-446655440001', 'Level 200', '200', 2),
    ('550e8400-e29b-41d4-a716-446655440016', '550e8400-e29b-41d4-a716-446655440001', 'Level 300', '300', 3),
    ('550e8400-e29b-41d4-a716-446655440017', '550e8400-e29b-41d4-a716-446655440001', 'Level 400', '400', 4)
ON CONFLICT DO NOTHING;

-- Insert staff
INSERT INTO staff (id, school_id, staff_id, first_name, last_name, email, phone, gender, department_id, role, position, qualification, status)
VALUES 
    ('550e8400-e29b-41d4-a716-446655440018', '550e8400-e29b-41d4-a716-446655440001', 'STF-1001', 'Hannah', 'Reed', 'hannah.reed@greenfield.edu.gh', '+233 24 123 4567', 'Female', '550e8400-e29b-41d4-a716-446655440006', 'Academic Officer', 'Senior Lecturer', 'PhD in Computer Science', 'active'),
    ('550e8400-e29b-41d4-a716-446655440019', '550e8400-e29b-41d4-a716-446655440001', 'STF-1002', 'Kofi', 'Mensah', 'kofi.mensah@greenfield.edu.gh', '+233 24 234 5678', 'Male', '550e8400-e29b-41d4-a716-446655440007', 'Teacher', 'Lecturer', 'MBA', 'active'),
    ('550e8400-e29b-41d4-a716-446655440020', '550e8400-e29b-41d4-a716-446655440001', 'STF-1003', 'Ama', 'Osei', 'ama.osei@greenfield.edu.gh', '+233 24 345 6789', 'Female', '550e8400-e29b-41d4-a716-446655440008', 'Teacher', 'Lecturer', 'MSc Mathematics', 'active'),
    ('550e8400-e29b-41d4-a716-446655440021', '550e8400-e29b-41d4-a716-446655440001', 'STF-1004', 'John', 'Smith', 'admin@greenfield.edu.gh', '+233 24 456 7890', 'Male', '550e8400-e29b-41d4-a716-446655440006', 'Administrator', 'System Admin', 'BSc IT', 'active')
ON CONFLICT DO NOTHING;

-- Insert students
INSERT INTO students (id, school_id, student_id, first_name, last_name, email, phone, gender, program_id, level_id, status)
VALUES 
    ('550e8400-e29b-41d4-a716-446655440022', '550e8400-e29b-41d4-a716-446655440001', 'STU-1001', 'Daniel', 'Agyekum', 'daniel.agyekum@student.edu.gh', '+233 20 001 0001', 'Male', '550e8400-e29b-41d4-a716-446655440010', '550e8400-e29b-41d4-a716-446655440014', 'active'),
    ('550e8400-e29b-41d4-a716-446655440023', '550e8400-e29b-41d4-a716-446655440001', 'STU-1002', 'Lila', 'Mensah', 'lila.mensah@student.edu.gh', '+233 20 001 0002', 'Female', '550e8400-e29b-41d4-a716-446655440011', '550e8400-e29b-41d4-a716-446655440014', 'active'),
    ('550e8400-e29b-41d4-a716-446655440024', '550e8400-e29b-41d4-a716-446655440001', 'STU-1003', 'Kojo', 'Tetteh', 'kojo.tetteh@student.edu.gh', '+233 20 001 0003', 'Male', '550e8400-e29b-41d4-a716-446655440010', '550e8400-e29b-41d4-a716-446655440015', 'active')
ON CONFLICT DO NOTHING;

-- Insert courses
INSERT INTO courses (id, school_id, program_id, level_id, department_id, code, name, description, credits, teacher_id, is_active)
VALUES 
    ('550e8400-e29b-41d4-a716-446655440025', '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440010', '550e8400-e29b-41d4-a716-446655440014', '550e8400-e29b-41d4-a716-446655440006', 'CSC101', 'Introduction to Programming', 'Basic programming concepts using Python', 3, '550e8400-e29b-41d4-a716-446655440018', true),
    ('550e8400-e29b-41d4-a716-446655440026', '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440010', '550e8400-e29b-41d4-a716-446655440014', '550e8400-e29b-41d4-a716-446655440006', 'CSC102', 'Data Structures', 'Fundamental data structures and algorithms', 3, '550e8400-e29b-41d4-a716-446655440018', true),
    ('550e8400-e29b-41d4-a716-446655440027', '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440011', '550e8400-e29b-41d4-a716-446655440014', '550e8400-e29b-41d4-a716-446655440007', 'BUS101', 'Principles of Management', 'Introduction to business management', 3, '550e8400-e29b-41d4-a716-446655440019', true),
    ('550e8400-e29b-41d4-a716-446655440028', '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440010', '550e8400-e29b-41d4-a716-446655440014', '550e8400-e29b-41d4-a716-446655440008', 'MTH101', 'Calculus I', 'Differential calculus', 3, '550e8400-e29b-41d4-a716-446655440020', true)
ON CONFLICT DO NOTHING;

-- Insert grade scales
INSERT INTO grade_scales (id, school_id, name, grade, min_marks, max_marks, grade_point, description)
VALUES 
    ('550e8400-e29b-41d4-a716-446655440029', '550e8400-e29b-41d4-a716-446655440001', 'Standard', 'A', 80, 100, 4.0, 'Excellent'),
    ('550e8400-e29b-41d4-a716-446655440030', '550e8400-e29b-41d4-a716-446655440001', 'Standard', 'B', 70, 79, 3.5, 'Very Good'),
    ('550e8400-e29b-41d4-a716-446655440031', '550e8400-e29b-41d4-a716-446655440001', 'Standard', 'C', 60, 69, 3.0, 'Good'),
    ('550e8400-e29b-41d4-a716-446655440032', '550e8400-e29b-41d4-a716-446655440001', 'Standard', 'D', 50, 59, 2.5, 'Pass'),
    ('550e8400-e29b-41d4-a716-446655440033', '550e8400-e29b-41d4-a716-446655440001', 'Standard', 'F', 0, 49, 0.0, 'Fail')
ON CONFLICT DO NOTHING;

-- Insert announcements
INSERT INTO announcements (id, school_id, title, content, target_audience, priority, is_published, created_by)
VALUES 
    ('550e8400-e29b-41d4-a716-446655440034', '550e8400-e29b-41d4-a716-446655440001', 'Welcome to 2025-2026 Academic Year', 'We are excited to welcome all students to the new academic year. Classes begin on September 1, 2025.', 'all', 'high', true, '550e8400-e29b-41d4-a716-446655440021'),
    ('550e8400-e29b-41d4-a716-446655440035', '550e8400-e29b-41d4-a716-446655440001', 'Course Registration Open', 'Course registration for First Term is now open. Please register before the deadline.', 'students', 'normal', true, '550e8400-e29b-41d4-a716-446655440021'),
    ('550e8400-e29b-41d4-a716-446655440036', '550e8400-e29b-41d4-a716-446655440001', 'Mid-Term Examinations', 'Mid-term examinations will be held from November 15-20, 2025.', 'students', 'normal', true, '550e8400-e29b-41d4-a716-446655440018')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================

