
-- ============================================================================
-- Row Level Security (RLS) Policies
-- School Management System - Supabase
-- ============================================================================

ALTER TABLE schools ENABLE ROW LEVEL SECURITY;
ALTER TABLE academic_years ENABLE ROW LEVEL SECURITY;
ALTER TABLE terms ENABLE ROW LEVEL SECURITY;
ALTER TABLE departments ENABLE ROW LEVEL SECURITY;
ALTER TABLE programs ENABLE ROW LEVEL SECURITY;
ALTER TABLE levels ENABLE ROW LEVEL SECURITY;
ALTER TABLE staff ENABLE ROW LEVEL SECURITY;
ALTER TABLE students ENABLE ROW LEVEL SECURITY;
ALTER TABLE courses ENABLE ROW LEVEL SECURITY;
ALTER TABLE class_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE class_group_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE course_registrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE teaching_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE exams ENABLE ROW LEVEL SECURITY;
ALTER TABLE exam_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE grade_scales ENABLE ROW LEVEL SECURITY;
ALTER TABLE fee_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE books ENABLE ROW LEVEL SECURITY;
ALTER TABLE book_issues ENABLE ROW LEVEL SECURITY;
ALTER TABLE announcements ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_log ENABLE ROW LEVEL SECURITY;

-- Schools: Public can view for login
CREATE POLICY "Public can view schools" ON schools FOR SELECT USING (true);
CREATE POLICY "School admin can update school" ON schools FOR UPDATE USING (
    EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id = auth.uid() AND ur.role = 'admin' AND ur.school_id = schools.id)
);

-- Academic Years
CREATE POLICY "Staff can view academic years" ON academic_years FOR SELECT USING (
    school_id IN (SELECT school_id FROM staff WHERE user_id = auth.uid() UNION ALL SELECT school_id FROM students WHERE user_id = auth.uid())
);
CREATE POLICY "Admin can manage academic years" ON academic_years FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id = auth.uid() AND ur.role = 'admin' AND ur.school_id = academic_years.school_id)
);

-- Terms
CREATE POLICY "Staff can view terms" ON terms FOR SELECT USING (
    school_id IN (SELECT school_id FROM staff WHERE user_id = auth.uid() UNION ALL SELECT school_id FROM students WHERE user_id = auth.uid())
);
CREATE POLICY "Admin can manage terms" ON terms FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id = auth.uid() AND ur.role = 'admin' AND ur.school_id = terms.school_id)
);

-- Departments
CREATE POLICY "Users can view departments" ON departments FOR SELECT USING (
    school_id IN (SELECT school_id FROM staff WHERE user_id = auth.uid() UNION ALL SELECT school_id FROM students WHERE user_id = auth.uid())
);
CREATE POLICY "Admin can manage departments" ON departments FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id = auth.uid() AND ur.role = 'admin' AND ur.school_id = departments.school_id)
);

-- Programs
CREATE POLICY "Users can view programs" ON programs FOR SELECT USING (
    school_id IN (SELECT school_id FROM staff WHERE user_id = auth.uid() UNION ALL SELECT school_id FROM students WHERE user_id = auth.uid())
);
CREATE POLICY "Admin can manage programs" ON programs FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id = auth.uid() AND ur.role = 'admin' AND ur.school_id = programs.school_id)
);

-- Levels
CREATE POLICY "Users can view levels" ON levels FOR SELECT USING (
    school_id IN (SELECT school_id FROM staff WHERE user_id = auth.uid() UNION ALL SELECT school_id FROM students WHERE user_id = auth.uid())
);
CREATE POLICY "Admin can manage levels" ON levels FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id = auth.uid() AND ur.role = 'admin' AND ur.school_id = levels.school_id)
);

-- Staff
CREATE POLICY "Staff can view staff" ON staff FOR SELECT USING (school_id IN (SELECT school_id FROM staff WHERE user_id = auth.uid()));
CREATE POLICY "Admin can manage staff" ON staff FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id = auth.uid() AND ur.role = 'admin' AND ur.school_id = staff.school_id)
);
CREATE POLICY "Staff can update own profile" ON staff FOR UPDATE USING (user_id = auth.uid());

-- Students
CREATE POLICY "Staff can view students" ON students FOR SELECT USING (school_id IN (SELECT school_id FROM staff WHERE user_id = auth.uid()));
CREATE POLICY "Students can view own profile" ON students FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "Admin can manage students" ON students FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id = auth.uid() AND ur.role IN ('admin', 'teacher') AND ur.school_id = students.school_id)
);
CREATE POLICY "Students can update own profile" ON students FOR UPDATE USING (user_id = auth.uid());

-- Courses
CREATE POLICY "Users can view courses" ON courses FOR SELECT USING (
    school_id IN (SELECT school_id FROM staff WHERE user_id = auth.uid() UNION ALL SELECT school_id FROM students WHERE user_id = auth.uid())
);
CREATE POLICY "Admin can manage courses" ON courses FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id = auth.uid() AND ur.role IN ('admin', 'teacher') AND ur.school_id = courses.school_id)
);

-- Class Groups
CREATE POLICY "Users can view class groups" ON class_groups FOR SELECT USING (
    school_id IN (SELECT school_id FROM staff WHERE user_id = auth.uid() UNION ALL SELECT school_id FROM students WHERE user_id = auth.uid())
);
CREATE POLICY "Admin can manage class groups" ON class_groups FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id = auth.uid() AND ur.role = 'admin' AND ur.school_id = class_groups.school_id)
);

-- Course Registrations
CREATE POLICY "Users can view registrations" ON course_registrations FOR SELECT USING (
    school_id IN (SELECT school_id FROM staff WHERE user_id = auth.uid() UNION ALL SELECT school_id FROM students WHERE user_id = auth.uid())
    OR student_id IN (SELECT id FROM students WHERE user_id = auth.uid())
);
CREATE POLICY "Admin can manage registrations" ON course_registrations FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id = auth.uid() AND ur.role IN ('admin', 'teacher') AND ur.school_id = course_registrations.school_id)
);
CREATE POLICY "Students can register courses" ON course_registrations FOR INSERT WITH CHECK (
    student_id IN (SELECT id FROM students WHERE user_id = auth.uid())
);

-- Attendance
CREATE POLICY "Users can view attendance" ON attendance FOR SELECT USING (
    school_id IN (SELECT school_id FROM staff WHERE user_id = auth.uid() UNION ALL SELECT school_id FROM students WHERE user_id = auth.uid())
);
CREATE POLICY "Admin can manage attendance" ON attendance FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id = auth.uid() AND ur.role IN ('admin', 'teacher') AND ur.school_id = attendance.school_id)
);

-- Attendance Records
CREATE POLICY "Users can view attendance records" ON attendance_records FOR SELECT USING (
    student_id IN (SELECT id FROM students WHERE user_id = auth.uid())
);
CREATE POLICY "Admin can manage attendance records" ON attendance_records FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id = auth.uid() AND ur.role IN ('admin', 'teacher'))
);

-- Exams
CREATE POLICY "Users can view exams" ON exams FOR SELECT USING (
    school_id IN (SELECT school_id FROM staff WHERE user_id = auth.uid() UNION ALL SELECT school_id FROM students WHERE user_id = auth.uid())
);
CREATE POLICY "Admin can manage exams" ON exams FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id = auth.uid() AND ur.role IN ('admin', 'teacher') AND ur.school_id = exams.school_id)
);

-- Exam Results
CREATE POLICY "Users can view exam results" ON exam_results FOR SELECT USING (
    school_id IN (SELECT school_id FROM staff WHERE user_id = auth.uid() UNION ALL SELECT school_id FROM students WHERE user_id = auth.uid())
    OR student_id IN (SELECT id FROM students WHERE user_id = auth.uid())
);
CREATE POLICY "Admin can manage exam results" ON exam_results FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id = auth.uid() AND ur.role IN ('admin', 'teacher') AND ur.school_id = exam_results.school_id)
);

-- Grade Scales
CREATE POLICY "Users can view grade scales" ON grade_scales FOR SELECT USING (
    school_id IN (SELECT school_id FROM staff WHERE user_id = auth.uid() UNION ALL SELECT school_id FROM students WHERE user_id = auth.uid())
);
CREATE POLICY "Admin can manage grade scales" ON grade_scales FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id = auth.uid() AND ur.role = 'admin' AND ur.school_id = grade_scales.school_id)
);

-- Fee Categories
CREATE POLICY "Users can view fee categories" ON fee_categories FOR SELECT USING (
    school_id IN (SELECT school_id FROM staff WHERE user_id = auth.uid() UNION ALL SELECT school_id FROM students WHERE user_id = auth.uid())
);
CREATE POLICY "Admin can manage fee categories" ON fee_categories FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id = auth.uid() AND ur.role IN ('admin', 'accountant') AND ur.school_id = fee_categories.school_id)
);

-- Payments
CREATE POLICY "Users can view payments" ON payments FOR SELECT USING (
    school_id IN (SELECT school_id FROM staff WHERE user_id = auth.uid())
    OR student_id IN (SELECT id FROM students WHERE user_id = auth.uid())
);
CREATE POLICY "Admin can manage payments" ON payments FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id = auth.uid() AND ur.role IN ('admin', 'accountant') AND ur.school_id = payments.school_id)
);

-- Books
CREATE POLICY "Users can view books" ON books FOR SELECT USING (
    school_id IN (SELECT school_id FROM staff WHERE user_id = auth.uid() UNION ALL SELECT school_id FROM students WHERE user_id = auth.uid())
);
CREATE POLICY "Admin can manage books" ON books FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id = auth.uid() AND ur.role IN ('admin', 'librarian') AND ur.school_id = books.school_id)
);

-- Book Issues
CREATE POLICY "Users can view book issues" ON book_issues FOR SELECT USING (
    school_id IN (SELECT school_id FROM staff WHERE user_id = auth.uid())
    OR student_id IN (SELECT id FROM students WHERE user_id = auth.uid())
);
CREATE POLICY "Admin can manage book issues" ON book_issues FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id = auth.uid() AND ur.role IN ('admin', 'librarian') AND ur.school_id = book_issues.school_id)
);

-- Announcements
CREATE POLICY "Users can view announcements" ON announcements FOR SELECT USING (
    school_id IN (SELECT school_id FROM staff WHERE user_id = auth.uid() UNION ALL SELECT school_id FROM students WHERE user_id = auth.uid())
    AND is_published = true
);
CREATE POLICY "Admin can manage announcements" ON announcements FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id = auth.uid() AND ur.role = 'admin' AND ur.school_id = announcements.school_id)
);

-- Messages
CREATE POLICY "Users can view own messages" ON messages FOR SELECT USING (sender_id = auth.uid() OR recipient_id = auth.uid());
CREATE POLICY "Users can send messages" ON messages FOR INSERT WITH CHECK (sender_id = auth.uid());

-- Events
CREATE POLICY "Users can view events" ON events FOR SELECT USING (
    school_id IN (SELECT school_id FROM staff WHERE user_id = auth.uid() UNION ALL SELECT school_id FROM students WHERE user_id = auth.uid())
);
CREATE POLICY "Admin can manage events" ON events FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id = auth.uid() AND ur.role = 'admin' AND ur.school_id = events.school_id)
);

-- User Roles
CREATE POLICY "Users can view own roles" ON user_roles FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "Admin can manage roles" ON user_roles FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id = auth.uid() AND ur.role = 'admin' AND ur.school_id = user_roles.school_id)
);

-- Activity Log
CREATE POLICY "Anyone can insert activity logs" ON activity_log FOR INSERT WITH CHECK (true);
CREATE POLICY "Admin can view activity logs" ON activity_log FOR SELECT USING (
    school_id IN (SELECT school_id FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
);

