# School Management System - Rebuild with Supabase

## Project Overview
Comprehensive school management platform for Ghana academic institutions. This system manages the complete student lifecycle from admission to graduation, including staff management, course registration, attendance tracking, exam results, and more.

---

## Current System Analysis

### Existing Features
- Multi-school support (multi-tenant architecture)
- School account creation and authentication
- Student admissions/applications
- Staff management
- Course management
- Course registration
- Attendance tracking
- Exam results recording
- Announcements
- Basic reporting

### Current Stack
- Frontend: Vanilla HTML/CSS/JavaScript
- Backend: Python Flask-like server with SQLite
- Storage: LocalStorage for session

---

## New Features to Add (Research-Based)

### 1. Academic Structure Management
- **Academic Years**: Define academic years (e.g., 2025-2026)
- **Terms/Semesters**: Configure terms within academic years
- **Programs/Departments**: Organize courses by faculty/department
- **Levels/Year Groups**: Student year levels (100, 200, 300, 400)

### 2. Enhanced Student Management
- **Student Profile**: Detailed student information ( guardian info, emergency contacts)
- **Student Status**: Active, Graduated, Suspended, Withdrawn, Deferred
- **Student ID Generation**: Auto-generate formatted student IDs
- **Bulk Student Import**: Import students via CSV

### 3. Comprehensive Staff Management
- **Staff Categories**: Teachers, Administrators, Support Staff
- **Staff Profile**: Qualifications, specializations, employment history
- **Teaching Assignments**: Assign teachers to courses/classes
- **Staff Attendance**: Track staff presence

### 4. Class/Group Management
- **Class Groups**: Create student groups (e.g., CS Year 1 Group A)
- **Class Schedules**: Weekly timetable for classes
- **Room Management**: Manage classrooms/labs

### 5. Attendance Enhancement
- **Daily Attendance**: Mark daily attendance by class
- **Attendance Reports**: Summary and detailed reports
- **Attendance Notifications**: Alert for low attendance

### 6. Examination & Assessment
- **Exam Types**: Midterm, Final, Quiz, Assignment
- **Grade Scales**: Configure grading systems (A-F, Percentage, GPA)
- **Grade Book**: Track grades throughout term
- **Transcript Generation**: Official academic transcripts
- **Class Ranking**: Student ranking by performance

### 7. Financial Management (Basic)
- **Fee Categories**: Tuition, Registration, Library, Sports
- **Fee Structure**: Define fees by program/level
- **Payment Tracking**: Record payments
- **Payment Receipts**: Generate receipts

### 8. Library Management
- **Book Catalog**: Library books/inventory
- **Book Issues**: Track borrowed books
- **Book Returns**: Return tracking

### 9. Communication
- **Notice Board**: School-wide announcements
- **Messages**: Internal messaging
- **Email Notifications**: Automated emails

### 10. Reports & Analytics
- **Student Reports**: Performance, attendance
- **Staff Reports**: Teaching loads, performance
- **Institution Reports**: Enrollment stats, pass rates
- **Export Options**: PDF, Excel exports

### 11. User Portal Features
- **Student Portal**: View grades, attendance, schedule
- **Parent Portal**: View child progress (future)
- **Teacher Portal**: Grade entry, attendance

### 12. Settings & Configuration
- **School Profile**: Institution details, logo
- **System Settings**: Academic calendar, grading scales
- **User Roles**: Define permissions

---

## Supabase Database Schema

### Core Tables

```sql
-- 1. Schools (multi-tenant)
sms_schools (
  id uuid PRIMARY KEY,
  name text NOT NULL,
  email text UNIQUE,
  phone text,
  address text,
  logo_url text,
  established_date date,
  created_at timestamptz,
  updated_at timestamptz
)

-- 2. Academic Years
sms_academic_years (
  id uuid PRIMARY KEY,
  school_id uuid REFERENCES schools(id),
  name text NOT NULL, -- "2025-2026"
  start_date date,
  end_date date,
  is_current boolean DEFAULT false,
  created_at timestamptz
)

-- 3. Terms/Semesters
sms_terms (
  id uuid PRIMARY KEY,
  school_id uuid REFERENCES schools(id),
  academic_year_id uuid REFERENCES academic_years(id),
  name text NOT NULL, -- "First Term"
  term_order int,
  start_date date,
  end_date date,
  is_current boolean DEFAULT false,
  created_at timestamptz
)

-- 4. Departments/Faculties
sms_departments (
  id uuid PRIMARY KEY,
  school_id uuid REFERENCES schools(id),
  name text NOT NULL,
  code text,
  head_id uuid, -- staff_id
  created_at timestamptz
)

-- 5. Programs
sms_programs (
  id uuid PRIMARY KEY,
  school_id uuid REFERENCES schools(id),
  department_id uuid REFERENCES departments(id),
  name text NOT NULL,
  code text,
  duration_years int,
  created_at timestamptz
)

-- 6. Staff/Employees
sms_staff (
  id uuid PRIMARY KEY,
  school_id uuid REFERENCES schools(id),
  user_id uuid REFERENCES auth.users, -- Supabase Auth
  staff_id text, -- "STF-1001"
  first_name text,
  last_name text,
  email text UNIQUE,
  phone text,
  gender text,
  date_of_birth date,
  department_id uuid REFERENCES departments(id),
  role text, -- "Teacher", "Admin", "Accountant"
  position text,
  qualification text,
  specialization text,
  employment_date date,
  salary numeric,
  status text DEFAULT 'active',
  photo_url text,
  created_at timestamptz,
  updated_at timestamptz
)

-- 7. Students
sms_students (
  id uuid PRIMARY KEY,
  school_id uuid REFERENCES schools(id),
  user_id uuid REFERENCES auth.users,
  student_id text, -- "STU-1001"
  first_name text,
  last_name text,
  email text,
  phone text,
  gender text,
  date_of_birth date,
  program_id uuid REFERENCES programs(id),
  level text, -- "100", "200"
  entry_year text,
  status text DEFAULT 'active', -- active, graduated, suspended, withdrawn
  guardian_name text,
  guardian_phone text,
  guardian_email text,
  address text,
  photo_url text,
  created_at timestamptz,
  updated_at timestamptz
)

-- 8. Courses/Subjects
sms_courses (
  id uuid PRIMARY KEY,
  school_id uuid REFERENCES schools(id),
  program_id uuid REFERENCES programs(id),
  code text NOT NULL,
  name text NOT NULL,
  description text,
  credits int DEFAULT 3,
  level text,
  department_id uuid REFERENCES departments(id),
  teacher_id uuid REFERENCES staff(id),
  seats int DEFAULT 30,
  is_active boolean DEFAULT true,
  created_at timestamptz
)

-- 9. Student Course Registrations
sms_registrations (
  id uuid PRIMARY KEY,
  school_id uuid REFERENCES schools(id),
  student_id uuid REFERENCES students(id),
  term_id uuid REFERENCES terms(id),
  course_id uuid REFERENCES courses(id),
  status text DEFAULT 'registered',
  registered_date date,
  created_at timestamptz,
  UNIQUE(student_id, term_id, course_id)
)

-- 10. Attendance
sms_attendance (
  id uuid PRIMARY KEY,
  school_id uuid REFERENCES schools(id),
  term_id uuid REFERENCES terms(id),
  course_id uuid REFERENCES courses(id),
  student_id uuid REFERENCES students(id),
  date date NOT NULL,
  status text NOT NULL, -- present, absent, late, excused
  remarks text,
  marked_by uuid REFERENCES staff(id),
  created_at timestamptz,
  UNIQUE(student_id, course_id, date)
)

-- 11. Examinations
sms_exams (
  id uuid PRIMARY KEY,
  school_id uuid REFERENCES schools(id),
  term_id uuid REFERENCES terms(id),
  course_id uuid REFERENCES courses(id),
  exam_type text, -- "Midterm", "Final", "Quiz"
  exam_date date,
  total_marks numeric,
  created_by uuid REFERENCES staff(id),
  created_at timestamptz
)

-- 12. Exam Results/Grades
sms_exam_results (
  id uuid PRIMARY KEY,
  school_id uuid REFERENCES schools(id),
  exam_id uuid REFERENCES exams(id),
  student_id uuid REFERENCES students(id),
  marks_obtained numeric,
  grade text,
  remarks text,
  recorded_by uuid REFERENCES staff(id),
  recorded_at timestamptz,
  UNIQUE(exam_id, student_id)
)

-- 13. Grade Scales
sms_grade_scales (
  id uuid PRIMARY KEY,
  school_id uuid REFERENCES schools(id),
  name text NOT NULL, -- "Standard A-F"
  grade text NOT NULL,
  min_marks numeric,
  max_marks numeric,
  grade_point numeric,
  description text
)

-- 14. Announcements
sms_announcements (
  id uuid PRIMARY KEY,
  school_id uuid REFERENCES schools(id),
  title text NOT NULL,
  content text,
  target_audience text, -- all, students, staff
  priority text DEFAULT 'normal',
  start_date date,
  end_date date,
  created_by uuid REFERENCES staff(id),
  created_at timestamptz
)

-- 15. Fees
sms_fee_categories (
  id uuid PRIMARY KEY,
  school_id uuid REFERENCES schools(id),
  name text NOT NULL, -- "Tuition", "Library", "Sports"
  description text,
  amount numeric NOT NULL,
  academic_year_id uuid REFERENCES academic_years(id),
  created_at timestamptz
)

-- 16. Fee Payments
sms_payments (
  id uuid PRIMARY KEY,
  school_id uuid REFERENCES schools(id),
  student_id uuid REFERENCES students(id),
  fee_category_id uuid REFERENCES fee_categories(id),
  amount_paid numeric,
  payment_date date,
  payment_method text,
  receipt_number text,
  recorded_by uuid REFERENCES staff(id),
  created_at timestamptz
)

-- 17. Library Books
sms_books (
  id uuid PRIMARY KEY,
  school_id uuid REFERENCES schools(id),
  isbn text,
  title text NOT NULL,
  author text,
  publisher text,
  category text,
  total_copies int DEFAULT 1,
  available_copies int,
  created_at timestamptz
)

-- 18. Book Issues
sms_book_issues (
  id uuid PRIMARY KEY,
  school_id uuid REFERENCES schools(id),
  book_id uuid REFERENCES books(id),
  student_id uuid REFERENCES students(id),
  issue_date date,
  due_date date,
  return_date date,
  status text DEFAULT 'issued', -- issued, returned, lost
  created_at timestamptz
)

-- 19. Messages
sms_messages (
  id uuid PRIMARY KEY,
  school_id uuid REFERENCES schools(id),
  sender_id uuid REFERENCES staff(id) OR students(id),
  recipient_id uuid,
  subject text,
  body text,
  is_read boolean DEFAULT false,
  created_at timestamptz
)

-- 20. Class Groups
sms_class_groups (
  id uuid PRIMARY KEY,
  school_id uuid REFERENCES schools(id),
  name text NOT NULL,
  program_id uuid REFERENCES programs(id),
  level text,
  academic_year_id uuid REFERENCES academic_years(id),
  created_at timestamptz
)
```

---

## Implementation Phases

### Phase 1: Foundation
- Set up Supabase project
- Create database schema
- Configure authentication
- Update Python server for Supabase

### Phase 2: Core Features
- Multi-school authentication
- Student management
- Staff management  
- Course management

### Phase 3: Academic Features
- Attendance system
- Examination system
- Grade book
- Reports

### Phase 4: Additional Modules
- Fee management
- Library management
- Communications

### Phase 5: Enhancements
- Student/Teacher portals
- Analytics
- Export features

---

## Files to Update/Create

### Backend (Python)
- `server.py` - Main API server using Supabase

### Frontend (HTML)
- `index.html` - Landing page
- `admin-dashboard.html` - Main admin dashboard
- `teacher-dashboard.html` - Staff dashboard
- `student-dashboard.html` - Student portal (NEW)
- `school-auth.html` - School account management
- `admissions.html` - Application form
- `course-registration.html` - Student course registration
- `student-login.html` - Student authentication
- `teacher-login.html` - Staff authentication
- `courses.html` - Course management (NEW)
- `attendance.html` - Attendance management (NEW)
- `exams.html` - Examination management (NEW)
- `reports.html` - Reports generation (NEW)
- `finance.html` - Fee management (NEW)
- `library.html` - Library management (NEW)
- `settings.html` - System settings (NEW)

### JavaScript
- `js/storage.js` - Supabase client
- `js/main.js` - Common functionality
- `js/app.js` - Dashboard functionality
- `js/auth.js` - Authentication (NEW)
- `js/api.js` - API calls (NEW)

### CSS
- `css/style.css` - Existing styles (enhance as needed)

---

## Supabase Configuration

### Environment Variables
```
SUPABASE_URL=your-project-url
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

### Row Level Security (RLS)
- Enable RLS on all tables
- Create policies for:
  - School isolation (users can only see their school's data)
  - Role-based access (admin, teacher, student permissions)

### Authentication
- Use Supabase Auth for:
  - Email/Password authentication
  - Magic links
  - OAuth (Google, etc.)

---

## Acceptance Criteria

1. ✓ Multi-school support with isolated data
2. ✓ Complete student lifecycle management
3. ✓ Staff management with role-based access
4. ✓ Course and registration management
5. ✓ Attendance tracking
6. ✓ Examination and grade management
7. ✓ Financial tracking (fees)
8. ✓ Library management
9. ✓ Announcements and messaging
10. ✓ Reports and analytics
11. ✓ Responsive design
12. ✓ Supabase integration for auth and database

