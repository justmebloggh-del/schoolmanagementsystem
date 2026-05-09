const { createClient } = require('@supabase/supabase-js');

const db = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

const today = () => new Date().toISOString().split('T')[0];

async function nextId(table, prefix) {
  const { data } = await db
    .from(table)
    .select('id')
    .like('id', prefix + '%')
    .order('id', { ascending: false })
    .limit(1);
  if (!data || !data.length) return prefix + '1001';
  const num = parseInt((data[0].id || '').replace(prefix, '')) || 1000;
  return prefix + (num + 1);
}

function schoolId(req) {
  return (req.headers['x-school-id'] || '').trim();
}

async function requireSchool(req, res) {
  const id = schoolId(req);
  if (!id) { res.status(400).json({ ok: false, message: 'Select your school account first.' }); return null; }
  const { data } = await db.from('sms_schools').select('*').eq('id', id).single();
  if (!data) { res.status(404).json({ ok: false, message: 'School not found.' }); return null; }
  return data;
}

// ── ROUTE HANDLERS ──────────────────────────────────────────────────────────

async function handleHealth(req, res) {
  res.json({ ok: true, message: 'School Management API is running.' });
}

async function handleGetSchools(req, res) {
  const { data } = await db.from('sms_schools').select('id, name, email, phone, address').order('name');
  res.json({ ok: true, schools: data || [] });
}

async function handleGetSchool(req, res, id) {
  const { data } = await db.from('sms_schools').select('*').eq('id', id).single();
  if (!data) return res.status(404).json({ ok: false, message: 'School not found.' });
  res.json({ ok: true, school: { id: data.id, name: data.name, email: data.email, phone: data.phone || '', address: data.address || '' } });
}

async function handleSchoolRegister(req, res) {
  const b = req.body;
  const schoolName  = (b.schoolName  || '').trim();
  const schoolEmail = (b.schoolEmail || '').trim().toLowerCase();
  const schoolPhone = (b.schoolPhone || '').trim();
  const schoolAddr  = (b.schoolAddress || '').trim();
  const schoolPass  = (b.password    || '').trim();
  const adminName   = (b.adminName   || 'School Admin').trim();
  const adminEmail  = (b.adminEmail  || schoolEmail).trim().toLowerCase();
  const adminPass   = (b.adminPassword || 'Staff@123').trim();

  if (!schoolName || !schoolEmail || !schoolPass)
    return res.status(400).json({ ok: false, message: 'School name, email and password are required.' });

  const { data: exists } = await db.from('sms_schools').select('id').eq('email', schoolEmail).single();
  if (exists) return res.status(400).json({ ok: false, message: 'A school with that email already exists.' });

  const schoolId2 = await nextId('sms_schools', 'SCH-');
  const staffId   = await nextId('sms_staff',   'STF-');
  const now       = today();

  await db.from('sms_schools').insert({ id: schoolId2, name: schoolName, email: schoolEmail, phone: schoolPhone, address: schoolAddr, password: schoolPass, created_at: now });
  await db.from('sms_staff').insert({ id: staffId, school_id: schoolId2, name: adminName, email: adminEmail, role: 'Admin', department: 'Administration', status: 'active', password: adminPass, created_at: now });

  // Default courses
  const defaultCourses = [
    { code: 'CS101', title: 'Introduction to Computing', program: 'Computer Science', level: '100', credits: 3, seats: 40, lecturer: adminName },
    { code: 'MTH101', title: 'Mathematics I', program: 'General', level: '100', credits: 3, seats: 50, lecturer: adminName },
    { code: 'ENG101', title: 'Communication Skills', program: 'General', level: '100', credits: 2, seats: 50, lecturer: adminName },
  ];
  for (const c of defaultCourses) {
    const cid = await nextId('sms_courses', 'COURSE-');
    await db.from('sms_courses').insert({ id: cid, school_id: schoolId2, ...c, active: true });
  }

  res.json({ ok: true, message: 'School registered.', school: { id: schoolId2, name: schoolName, email: schoolEmail }, staffId, defaultPassword: adminPass, defaultStaff: { id: staffId, email: adminEmail, password: adminPass } });
}

async function handleSchoolLogin(req, res) {
  const { email, password } = req.body;
  if (!email || !password) return res.status(400).json({ ok: false, message: 'Email and password required.' });
  const { data } = await db.from('sms_schools').select('*').eq('email', email.toLowerCase().trim()).single();
  if (!data || data.password !== password)
    return res.status(401).json({ ok: false, message: 'Invalid email or password.' });
  res.json({ ok: true, school: { id: data.id, name: data.name, email: data.email } });
}

async function handleGetData(req, res) {
  const school = await requireSchool(req, res);
  if (!school) return;
  const sid = school.id;

  const [
    { data: staff },
    { data: students },
    { data: applications },
    { data: courses },
    { data: regRows },
    { data: regCourseRows },
    { data: attendance },
    { data: attRecords },
    { data: examResults },
    { data: announcements },
  ] = await Promise.all([
    db.from('sms_staff').select('*').eq('school_id', sid).order('created_at', { ascending: false }),
    db.from('sms_students').select('*').eq('school_id', sid).order('id'),
    db.from('sms_applications').select('*').eq('school_id', sid).order('submitted_on', { ascending: false }),
    db.from('sms_courses').select('*').eq('school_id', sid).order('code'),
    db.from('sms_registrations').select('*').eq('school_id', sid).order('registered_on', { ascending: false }),
    db.from('sms_registration_courses').select('*'),
    db.from('sms_attendance').select('*').eq('school_id', sid).order('date', { ascending: false }),
    db.from('sms_attendance_records').select('*'),
    db.from('sms_exam_results').select('*').eq('school_id', sid).order('recorded_on', { ascending: false }),
    db.from('sms_announcements').select('*').eq('school_id', sid).order('created_at', { ascending: false }),
  ]);

  const studentMap = {};
  (students || []).forEach(s => { studentMap[s.id] = s.name; });
  const staffMap = {};
  (staff || []).forEach(s => { staffMap[s.id] = s.name; });

  const regMap = {};
  (regCourseRows || []).forEach(rc => {
    if (!regMap[rc.registration_id]) regMap[rc.registration_id] = [];
    regMap[rc.registration_id].push(rc.course_id);
  });

  const attMap = {};
  (attRecords || []).forEach(ar => {
    if (!attMap[ar.attendance_id]) attMap[ar.attendance_id] = { present: [], absent: [] };
    if (ar.present) attMap[ar.attendance_id].present.push(ar.student_id);
    else attMap[ar.attendance_id].absent.push(ar.student_id);
  });

  res.json({
    ok: true,
    data: {
      meta: { schoolName: school.name, schoolId: school.id },
      staff: (staff || []).map(s => ({ id: s.id, name: s.name, email: s.email, role: s.role, department: s.department, status: s.status })),
      students: (students || []).map(s => ({ id: s.id, name: s.name, email: s.email || '', phone: s.phone || '', program: s.program, level: s.level, status: s.status })),
      applications: (applications || []).map(a => ({ id: a.id, fullName: a.full_name, dob: a.dob, email: a.email, phone: a.phone, address: a.address, programFirstChoice: a.program_first_choice, programSecondChoice: a.program_second_choice || '', notes: a.notes || '', status: a.status, submittedOn: a.submitted_on })),
      courses: (courses || []).map(c => ({ id: c.id, code: c.code, title: c.title, program: c.program, level: c.level, credits: c.credits, seats: c.seats, lecturer: c.lecturer, active: c.active, description: c.description || '' })),
      registrations: (regRows || []).map(r => ({ id: r.id, studentId: r.student_id, term: r.term, registeredOn: r.registered_on, courseIds: regMap[r.id] || [] })),
      attendance: (attendance || []).map(a => ({ id: a.id, date: a.date, courseId: a.course_id, presentStudentIds: (attMap[a.id] || {}).present || [], absentStudentIds: (attMap[a.id] || {}).absent || [] })),
      examResults: (examResults || []).map(r => ({ id: r.id, studentId: r.student_id, studentName: studentMap[r.student_id] || r.student_id, term: r.term, subject: r.subject, score: r.score, grade: r.grade, recordedOn: r.recorded_on, recordedBy: r.recorded_by || '', recordedByName: staffMap[r.recorded_by] || r.recorded_by || '' })),
      announcements: (announcements || []).map(a => ({ id: a.id, title: a.title, content: a.content || '', createdAt: a.created_at })),
      departments: [], programs: [], levels: [],
    }
  });
}

async function handleStudentLogin(req, res) {
  const school = await requireSchool(req, res);
  if (!school) return;
  const { identifier, password } = req.body;
  if (!identifier || !password) return res.status(400).json({ ok: false, message: 'Identifier and password required.' });

  const q = db.from('sms_students').select('*').eq('school_id', school.id);
  const idClean = identifier.trim().toLowerCase();
  const { data: byId } = await db.from('sms_students').select('*').eq('school_id', school.id).eq('id', identifier.trim().toUpperCase()).single();
  const { data: byEmail } = await db.from('sms_students').select('*').eq('school_id', school.id).eq('email', idClean).single();
  const student = byId || byEmail;

  if (!student || student.password !== password)
    return res.status(401).json({ ok: false, message: 'Invalid credentials.' });
  if (student.status !== 'active')
    return res.status(403).json({ ok: false, message: 'Account suspended. Contact admin.' });

  res.json({ ok: true, student: { id: student.id, name: student.name, email: student.email || '', program: student.program, level: student.level, status: student.status } });
}

async function handleStaffLogin(req, res) {
  const school = await requireSchool(req, res);
  if (!school) return;
  const { identifier, password } = req.body;
  if (!identifier || !password) return res.status(400).json({ ok: false, message: 'Identifier and password required.' });

  const idClean = identifier.trim().toLowerCase();
  const { data: byId }    = await db.from('sms_staff').select('*').eq('school_id', school.id).eq('id', identifier.trim().toUpperCase()).single();
  const { data: byEmail } = await db.from('sms_staff').select('*').eq('school_id', school.id).eq('email', idClean).single();
  const staff = byId || byEmail;

  if (!staff || staff.password !== password)
    return res.status(401).json({ ok: false, message: 'Invalid credentials.' });
  if (staff.status !== 'active')
    return res.status(403).json({ ok: false, message: 'Account suspended.' });

  res.json({ ok: true, staff: { id: staff.id, name: staff.name, email: staff.email, role: staff.role, department: staff.department, status: staff.status } });
}

async function handleGetStudent(req, res, studentId) {
  const school = await requireSchool(req, res);
  if (!school) return;
  const { data } = await db.from('sms_students').select('*').eq('id', studentId).eq('school_id', school.id).single();
  if (!data) return res.status(404).json({ ok: false, message: 'Student not found.' });
  res.json({ ok: true, student: { id: data.id, name: data.name, email: data.email || '', phone: data.phone || '', program: data.program, level: data.level, status: data.status } });
}

async function handleGetStudentProfile(req, res, studentId) {
  const school = await requireSchool(req, res);
  if (!school) return;
  const { data: student } = await db.from('sms_students').select('*').eq('id', studentId).eq('school_id', school.id).single();
  if (!student) return res.status(404).json({ ok: false, message: 'Student not found.' });

  const [{ data: regRows }, { data: attRecs }, { data: results }] = await Promise.all([
    db.from('sms_registrations').select('id, term').eq('student_id', studentId),
    db.from('sms_attendance_records').select('attendance_id, present').eq('student_id', studentId),
    db.from('sms_exam_results').select('*').eq('student_id', studentId).eq('school_id', school.id).order('recorded_on', { ascending: false }),
  ]);

  const regIds = (regRows || []).map(r => r.id);
  let courses = [];
  if (regIds.length) {
    const { data: rcRows } = await db.from('sms_registration_courses').select('registration_id, course_id').in('registration_id', regIds);
    const courseIds = [...new Set((rcRows || []).map(r => r.course_id))];
    if (courseIds.length) {
      const { data: cRows } = await db.from('sms_courses').select('*').in('id', courseIds);
      const termMap = {};
      (regRows || []).forEach(r => { termMap[r.id] = r.term; });
      const rcMap = {};
      (rcRows || []).forEach(rc => { rcMap[rc.course_id] = termMap[rc.registration_id]; });
      courses = (cRows || []).map(c => ({ code: c.code, title: c.title, program: c.program, level: c.level, credits: c.credits, term: rcMap[c.id] || '' }));
    }
  }

  const attIds = (attRecs || []).map(r => r.attendance_id);
  let attendance = [];
  if (attIds.length) {
    const { data: sessions } = await db.from('sms_attendance').select('id, date, course_id').in('id', attIds);
    const courseIds2 = [...new Set((sessions || []).map(s => s.course_id))];
    let codeMap = {};
    if (courseIds2.length) {
      const { data: cRows2 } = await db.from('sms_courses').select('id, code, title').in('id', courseIds2);
      (cRows2 || []).forEach(c => { codeMap[c.id] = c; });
    }
    const presMap = {};
    (attRecs || []).forEach(r => { presMap[r.attendance_id] = r.present; });
    attendance = (sessions || []).map(s => ({ date: s.date, code: (codeMap[s.course_id] || {}).code || s.course_id, title: (codeMap[s.course_id] || {}).title || '', status: presMap[s.id] ? 'present' : 'absent' }));
  }

  const present = (attRecs || []).filter(r => r.present).length;
  const total   = (attRecs || []).length;
  const avg     = results && results.length ? Math.round(results.reduce((s, r) => s + r.score, 0) / results.length * 10) / 10 : 0;

  res.json({
    ok: true,
    student: { id: student.id, name: student.name, email: student.email || '', program: student.program, level: student.level, status: student.status },
    courses,
    attendance,
    attendanceSummary: { present, total },
    results: (results || []).map(r => ({ id: r.id, recordedOn: r.recorded_on, term: r.term, subject: r.subject, score: r.score, grade: r.grade })),
    averageScore: avg,
  });
}

async function handleAddStudent(req, res) {
  const school = await requireSchool(req, res);
  if (!school) return;
  const b = req.body;
  const name    = (b.name    || '').trim();
  const program = (b.program || '').trim();
  const level   = (b.level   || '').trim();
  const email   = (b.email   || '').trim().toLowerCase();
  const phone   = (b.phone   || '').trim();
  const password = (b.password || '').trim() || 'Student@123';

  if (!name || !program || !level)
    return res.status(400).json({ ok: false, message: 'Name, program and level are required.' });

  if (email) {
    const { data: exists } = await db.from('sms_students').select('id').eq('school_id', school.id).eq('email', email).single();
    if (exists) return res.status(400).json({ ok: false, message: 'A student with that email already exists.' });
  }

  const studentId = await nextId('sms_students', 'STU-');
  await db.from('sms_students').insert({ id: studentId, school_id: school.id, name, email, phone, program, level, status: 'active', password, joined_on: today() });
  res.json({ ok: true, message: 'Student account created.', studentId, defaultPassword: password });
}

async function handleToggleStudent(req, res, studentId) {
  const school = await requireSchool(req, res);
  if (!school) return;
  const { data } = await db.from('sms_students').select('status').eq('id', studentId).eq('school_id', school.id).single();
  if (!data) return res.status(404).json({ ok: false, message: 'Student not found.' });
  const newStatus = data.status === 'active' ? 'suspended' : 'active';
  await db.from('sms_students').update({ status: newStatus }).eq('id', studentId);
  res.json({ ok: true, status: newStatus, message: `Student ${newStatus}.` });
}

async function handleResetStudentPassword(req, res, studentId) {
  const school = await requireSchool(req, res);
  if (!school) return;
  const { data } = await db.from('sms_students').select('id').eq('id', studentId).eq('school_id', school.id).single();
  if (!data) return res.status(404).json({ ok: false, message: 'Student not found.' });
  await db.from('sms_students').update({ password: 'Student@123' }).eq('id', studentId);
  res.json({ ok: true, message: 'Password reset to Student@123.' });
}

async function handleGetStaff(req, res, staffId) {
  const school = await requireSchool(req, res);
  if (!school) return;
  const { data } = await db.from('sms_staff').select('*').eq('id', staffId).eq('school_id', school.id).single();
  if (!data) return res.status(404).json({ ok: false, message: 'Staff not found.' });
  const s = { id: data.id, name: data.name, email: data.email, role: data.role, department: data.department, status: data.status };
  res.json({ ok: true, staff: s, teacher: s });
}

async function handleAddStaff(req, res) {
  const school = await requireSchool(req, res);
  if (!school) return;
  const b = req.body;
  const name       = (b.name       || '').trim();
  const email      = (b.email      || '').trim().toLowerCase();
  const role       = (b.role       || '').trim();
  const department = (b.department || '').trim();
  const password   = (b.password   || '').trim() || 'Staff@123';

  if (!name || !email || !role || !department)
    return res.status(400).json({ ok: false, message: 'Name, email, role and department are required.' });

  const { data: exists } = await db.from('sms_staff').select('id').eq('school_id', school.id).eq('email', email).single();
  if (exists) return res.status(400).json({ ok: false, message: 'A staff member with that email already exists.' });

  const staffId = await nextId('sms_staff', 'STF-');
  await db.from('sms_staff').insert({ id: staffId, school_id: school.id, name, email, role, department, status: 'active', password, created_at: today() });
  res.json({ ok: true, message: 'Staff account created.', staffId, defaultPassword: password });
}

async function handleResetStaffPassword(req, res, staffId) {
  const school = await requireSchool(req, res);
  if (!school) return;
  const { data } = await db.from('sms_staff').select('id').eq('id', staffId).eq('school_id', school.id).single();
  if (!data) return res.status(404).json({ ok: false, message: 'Staff not found.' });
  await db.from('sms_staff').update({ password: 'Staff@123' }).eq('id', staffId);
  res.json({ ok: true, message: 'Staff password reset to Staff@123.' });
}

async function handleToggleStaff(req, res, staffId) {
  const school = await requireSchool(req, res);
  if (!school) return;
  const { data } = await db.from('sms_staff').select('status').eq('id', staffId).eq('school_id', school.id).single();
  if (!data) return res.status(404).json({ ok: false, message: 'Staff not found.' });
  const newStatus = data.status === 'active' ? 'suspended' : 'active';
  await db.from('sms_staff').update({ status: newStatus }).eq('id', staffId);
  res.json({ ok: true, status: newStatus, message: `Staff ${newStatus}.` });
}

async function handleAddCourse(req, res) {
  const school = await requireSchool(req, res);
  if (!school) return;
  const b = req.body;
  const code     = (b.code     || '').trim().toUpperCase();
  const title    = (b.title    || '').trim();
  const program  = (b.program  || '').trim();
  const level    = (b.level    || '').trim();
  const credits  = parseInt(b.credits  || 3);
  const seats    = parseInt(b.seats    || 30);
  const lecturer = (b.staffName || b.teacherName || '').trim();

  if (!code || !title || !program || !level)
    return res.status(400).json({ ok: false, message: 'Code, title, program and level are required.' });

  const { data: exists } = await db.from('sms_courses').select('id').eq('school_id', school.id).eq('code', code).single();
  if (exists) return res.status(400).json({ ok: false, message: `Course ${code} already exists.` });

  const courseId = await nextId('sms_courses', 'COURSE-');
  await db.from('sms_courses').insert({ id: courseId, school_id: school.id, code, title, program, level, credits, seats, lecturer, active: true });
  res.json({ ok: true, message: `Course ${code} added.`, courseId });
}

async function handleToggleCourse(req, res, courseId) {
  const school = await requireSchool(req, res);
  if (!school) return;
  const { data } = await db.from('sms_courses').select('active').eq('id', courseId).eq('school_id', school.id).single();
  if (!data) return res.status(404).json({ ok: false, message: 'Course not found.' });
  await db.from('sms_courses').update({ active: !data.active }).eq('id', courseId);
  res.json({ ok: true, message: data.active ? 'Course deactivated.' : 'Course activated.' });
}

async function handleAdmissions(req, res) {
  const b = req.body;
  const bodySchoolId = (b.schoolId || '').trim();
  let school;
  if (bodySchoolId) {
    const { data } = await db.from('sms_schools').select('*').eq('id', bodySchoolId).single();
    if (!data) return res.status(404).json({ ok: false, message: 'School not found.' });
    school = data;
  } else {
    school = await requireSchool(req, res);
    if (!school) return;
  }

  const required = ['fullName', 'dob', 'email', 'phone', 'address', 'programFirstChoice'];
  if (required.some(f => !(b[f] || '').trim()))
    return res.status(400).json({ ok: false, message: 'Please fill all required fields.' });

  const appId = await nextId('sms_applications', 'APP-');
  await db.from('sms_applications').insert({
    id: appId, school_id: school.id,
    full_name: b.fullName.trim(), dob: b.dob, email: b.email.trim().toLowerCase(),
    phone: b.phone.trim(), address: b.address.trim(),
    program_first_choice: b.programFirstChoice.trim(),
    program_second_choice: (b.programSecondChoice || '').trim(),
    notes: (b.notes || '').trim(), status: 'pending', submitted_on: today(),
  });
  res.json({ ok: true, message: 'Application submitted.', applicationId: appId });
}

async function handleApproveApplication(req, res, appId) {
  const school = await requireSchool(req, res);
  if (!school) return;
  const { data: app } = await db.from('sms_applications').select('*').eq('id', appId).eq('school_id', school.id).single();
  if (!app) return res.status(404).json({ ok: false, message: 'Application not found.' });
  if (app.status !== 'pending') return res.status(400).json({ ok: false, message: `Application already ${app.status}.` });

  const studentId = await nextId('sms_students', 'STU-');
  const password  = 'Student@123';
  await db.from('sms_students').insert({
    id: studentId, school_id: school.id, name: app.full_name, email: app.email,
    phone: '', program: app.program_first_choice, level: '100',
    status: 'active', password, joined_on: today(),
  });
  await db.from('sms_applications').update({ status: 'approved' }).eq('id', appId);
  res.json({ ok: true, message: 'Application approved. Student account created.', studentId, defaultPassword: password });
}

async function handleRejectApplication(req, res, appId) {
  const school = await requireSchool(req, res);
  if (!school) return;
  const { data } = await db.from('sms_applications').select('id').eq('id', appId).eq('school_id', school.id).single();
  if (!data) return res.status(404).json({ ok: false, message: 'Application not found.' });
  await db.from('sms_applications').update({ status: 'rejected' }).eq('id', appId);
  res.json({ ok: true, message: 'Application rejected.' });
}

async function handleAttendance(req, res) {
  const school = await requireSchool(req, res);
  if (!school) return;
  const { date, courseId, presentStudentIds = [] } = req.body;
  const staffId = req.body.staffId || req.body.teacherId || '';
  if (!date || !courseId) return res.status(400).json({ ok: false, message: 'Date and course are required.' });

  const { data: students } = await db.from('sms_students').select('id').eq('school_id', school.id).eq('status', 'active');
  const attendanceId = await nextId('sms_attendance', 'ATT-');
  await db.from('sms_attendance').insert({ id: attendanceId, school_id: school.id, date, course_id: courseId, taken_by: staffId });

  const records = (students || []).map(s => ({ attendance_id: attendanceId, student_id: s.id, present: presentStudentIds.includes(s.id) }));
  if (records.length) await db.from('sms_attendance_records').insert(records);

  res.json({ ok: true, message: `Attendance saved for ${date}.` });
}

async function handleRegistrations(req, res) {
  const school = await requireSchool(req, res);
  if (!school) return;
  const { studentIdentifier, password, term, courseIds = [] } = req.body;
  if (!studentIdentifier || !password || !term || !courseIds.length)
    return res.status(400).json({ ok: false, message: 'Student ID/email, password, term and courses are required.' });

  const idClean = studentIdentifier.trim().toLowerCase();
  const { data: byId }    = await db.from('sms_students').select('*').eq('school_id', school.id).eq('id', studentIdentifier.trim().toUpperCase()).single();
  const { data: byEmail } = await db.from('sms_students').select('*').eq('school_id', school.id).eq('email', idClean).single();
  const student = byId || byEmail;

  if (!student || student.password !== password)
    return res.status(401).json({ ok: false, message: 'Invalid student credentials.' });

  const regId = await nextId('sms_registrations', 'REG-');
  await db.from('sms_registrations').insert({ id: regId, school_id: school.id, student_id: student.id, term, registered_on: today() });
  const rows = courseIds.map(cid => ({ registration_id: regId, course_id: cid }));
  await db.from('sms_registration_courses').insert(rows);

  res.json({ ok: true, message: `Registered for ${courseIds.length} course(s) in ${term}.`, registrationId: regId });
}

async function handleAdminRegistrations(req, res) {
  const school = await requireSchool(req, res);
  if (!school) return;
  const { studentId, term, courseIds = [] } = req.body;
  if (!studentId || !term || !courseIds.length)
    return res.status(400).json({ ok: false, message: 'Student, term and courses are required.' });

  const { data: student } = await db.from('sms_students').select('id, name').eq('id', studentId).eq('school_id', school.id).single();
  if (!student) return res.status(404).json({ ok: false, message: 'Student not found.' });

  const regId = await nextId('sms_registrations', 'REG-');
  await db.from('sms_registrations').insert({ id: regId, school_id: school.id, student_id: studentId, term, registered_on: today() });
  const validCourses = [];
  for (const cid of courseIds) {
    const { data: c } = await db.from('sms_courses').select('id').eq('id', cid).eq('school_id', school.id).single();
    if (c) validCourses.push(cid);
  }
  if (validCourses.length) await db.from('sms_registration_courses').insert(validCourses.map(cid => ({ registration_id: regId, course_id: cid })));

  res.json({ ok: true, message: `${student.name} registered for ${validCourses.length} course(s) in ${term}.`, registrationId: regId });
}

async function handleAddExamResult(req, res) {
  const school = await requireSchool(req, res);
  if (!school) return;
  const b = req.body;
  const studentId = (b.studentId || '').trim();
  const term      = (b.term      || '').trim();
  const subject   = (b.subject   || '').trim();
  const score     = parseFloat(b.score || 0);
  const grade     = (b.grade     || (score >= 70 ? 'A' : score >= 60 ? 'B' : score >= 50 ? 'C' : score >= 40 ? 'D' : 'F')).toUpperCase();
  const staffId   = (b.staffId   || '').trim();

  if (!studentId || !term || !subject)
    return res.status(400).json({ ok: false, message: 'Student, term and subject are required.' });

  const resultId = await nextId('sms_exam_results', 'RES-');
  await db.from('sms_exam_results').insert({ id: resultId, school_id: school.id, student_id: studentId, term, subject, score, grade, recorded_by: staffId, recorded_on: today() });
  res.json({ ok: true, message: 'Result recorded.', resultId });
}

async function handleDeleteExamResult(req, res, resultId) {
  const school = await requireSchool(req, res);
  if (!school) return;
  const { data } = await db.from('sms_exam_results').select('id').eq('id', resultId).eq('school_id', school.id).single();
  if (!data) return res.status(404).json({ ok: false, message: 'Result not found.' });
  await db.from('sms_exam_results').delete().eq('id', resultId);
  res.json({ ok: true, message: 'Result deleted.' });
}

async function handleJobApplication(req, res) {
  const b = req.body;
  const schoolId2 = (b.schoolId || '').trim();
  if (!schoolId2) return res.status(400).json({ ok: false, message: 'School is required.' });
  const { data: school } = await db.from('sms_schools').select('id, name').eq('id', schoolId2).single();
  if (!school) return res.status(404).json({ ok: false, message: 'School not found.' });

  const jobId = await nextId('sms_job_applications', 'JOB-');
  await db.from('sms_job_applications').insert({
    id: jobId, school_id: school.id, school_name: school.name,
    position: (b.position || '').trim(), full_name: (b.fullName || '').trim(),
    dob: b.dob || '', email: (b.email || '').trim().toLowerCase(),
    phone: (b.phone || '').trim(), address: (b.address || '').trim(),
    qualification: (b.qualification || '').trim(),
    experience: parseInt(b.experience || 0),
    department: (b.department || '').trim(),
    cv_file_name: (b.cvFileName || '').trim(),
    notes: (b.notes || '').trim(), status: 'pending', submitted_on: today(),
  });
  res.json({ ok: true, message: 'Job application submitted.', jobApplicationId: jobId });
}

async function handleListJobApplications(req, res) {
  const school = await requireSchool(req, res);
  if (!school) return;
  const { data } = await db.from('sms_job_applications').select('*').eq('school_id', school.id).order('submitted_on', { ascending: false });
  res.json({
    ok: true,
    jobApplications: (data || []).map(a => ({ id: a.id, position: a.position, fullName: a.full_name, email: a.email, phone: a.phone || '', qualification: a.qualification || '', experience: a.experience, department: a.department || '', cvFileName: a.cv_file_name || '', notes: a.notes || '', status: a.status, submittedOn: a.submitted_on }))
  });
}

async function handleUpdateJobApplication(req, res, jobId, newStatus) {
  const school = await requireSchool(req, res);
  if (!school) return;
  const { data } = await db.from('sms_job_applications').select('id').eq('id', jobId).eq('school_id', school.id).single();
  if (!data) return res.status(404).json({ ok: false, message: 'Application not found.' });
  await db.from('sms_job_applications').update({ status: newStatus }).eq('id', jobId);
  res.json({ ok: true, status: newStatus, message: `Application ${newStatus}.` });
}

async function handleRecoverAdmin(req, res) {
  const school = await requireSchool(req, res);
  if (!school) return;

  const { schoolPassword } = req.body;
  if (!schoolPassword) return res.status(400).json({ ok: false, message: 'School password required.' });
  if (school.password !== schoolPassword)
    return res.status(401).json({ ok: false, message: 'Incorrect school password.' });

  const { data: rows } = await db
    .from('sms_staff')
    .select('*')
    .eq('school_id', school.id)
    .ilike('role', '%admin%')
    .order('created_at', { ascending: true })
    .limit(1);

  if (!rows || !rows.length)
    return res.status(404).json({ ok: false, message: 'No admin staff found for this school. Please contact support.' });

  const admin = rows[0];
  const newPass = 'Staff@123';
  await db.from('sms_staff').update({ password: newPass }).eq('id', admin.id);

  res.json({ ok: true, message: 'Admin password reset.', adminEmail: admin.email, adminId: admin.id, newPassword: newPass });
}

// ── MAIN ROUTER ──────────────────────────────────────────────────────────────

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-School-ID');
  if (req.method === 'OPTIONS') return res.status(200).end();

  const rawPath = (req.url || '').split('?')[0];
  const path = rawPath.replace(/^\/api/, '') || '/';
  const slug = path.split('/').filter(Boolean);
  const m    = req.method;

  try {
    if (m === 'GET'  && path === '/health')                        return handleHealth(req, res);
    if (m === 'GET'  && path === '/schools')                       return handleGetSchools(req, res);
    if (m === 'POST' && path === '/schools/register')              return handleSchoolRegister(req, res);
    if (m === 'POST' && path === '/schools/login')                 return handleSchoolLogin(req, res);
    if (m === 'POST' && path === '/schools/recover-admin')         return handleRecoverAdmin(req, res);
    if (m === 'GET'  && path.startsWith('/schools/'))              return handleGetSchool(req, res, slug[1]);
    if (m === 'GET'  && path === '/data')                          return handleGetData(req, res);
    if (m === 'POST' && path === '/admissions')                    return handleAdmissions(req, res);
    if (m === 'POST' && (path === '/auth/student-login'))          return handleStudentLogin(req, res);
    if (m === 'POST' && (path === '/auth/staff-login' || path === '/auth/teacher-login')) return handleStaffLogin(req, res);
    if (m === 'POST' && path === '/students')                      return handleAddStudent(req, res);
    if (m === 'GET'  && slug[0] === 'students' && slug[2] === 'profile') return handleGetStudentProfile(req, res, slug[1]);
    if (m === 'GET'  && slug[0] === 'students' && slug.length === 2)     return handleGetStudent(req, res, slug[1]);
    if (m === 'POST' && slug[0] === 'students' && slug[2] === 'toggle')         return handleToggleStudent(req, res, slug[1]);
    if (m === 'POST' && slug[0] === 'students' && slug[2] === 'reset-password') return handleResetStudentPassword(req, res, slug[1]);
    if (m === 'POST' && path === '/staff')                         return handleAddStaff(req, res);
    if (m === 'GET'  && (slug[0] === 'staff' || slug[0] === 'teachers') && slug.length === 2) return handleGetStaff(req, res, slug[1]);
    if (m === 'POST' && slug[0] === 'staff' && slug[2] === 'toggle')          return handleToggleStaff(req, res, slug[1]);
    if (m === 'POST' && slug[0] === 'staff' && slug[2] === 'reset-password') return handleResetStaffPassword(req, res, slug[1]);
    if (m === 'POST' && path === '/courses')                       return handleAddCourse(req, res);
    if (m === 'POST' && slug[0] === 'courses' && slug[2] === 'toggle') return handleToggleCourse(req, res, slug[1]);
    if (m === 'POST' && path === '/attendance')                    return handleAttendance(req, res);
    if (m === 'POST' && path === '/registrations')                 return handleRegistrations(req, res);
    if (m === 'POST' && path === '/registrations/admin')           return handleAdminRegistrations(req, res);
    if (m === 'POST' && slug[0] === 'applications' && slug[2] === 'approve') return handleApproveApplication(req, res, slug[1]);
    if (m === 'POST' && slug[0] === 'applications' && slug[2] === 'reject')  return handleRejectApplication(req, res, slug[1]);
    if (m === 'POST' && path === '/exam-results')                  return handleAddExamResult(req, res);
    if (m === 'POST' && slug[0] === 'exam-results' && slug[2] === 'delete') return handleDeleteExamResult(req, res, slug[1]);
    if (m === 'POST' && path === '/job-applications')              return handleJobApplication(req, res);
    if (m === 'GET'  && path === '/job-applications/list')         return handleListJobApplications(req, res);
    if (m === 'POST' && slug[0] === 'job-applications' && slug[2] === 'shortlist') return handleUpdateJobApplication(req, res, slug[1], 'shortlisted');
    if (m === 'POST' && slug[0] === 'job-applications' && slug[2] === 'reject')    return handleUpdateJobApplication(req, res, slug[1], 'rejected');

    res.status(404).json({ ok: false, message: 'Unknown endpoint.' });
  } catch (err) {
    console.error('[API error]', err);
    res.status(500).json({ ok: false, message: 'Server error. Check Supabase connection.' });
  }
};
