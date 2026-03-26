
/**
 * School Management System - Storage Module
 * Handles data operations with Supabase
 */

(function() {
  'use strict';

  // Local storage keys
  const CURRENT_STUDENT_KEY = 'sms_current_student';
  const CURRENT_STAFF_KEY = 'sms_current_staff';
  const CURRENT_SCHOOL_KEY = 'sms_current_school';
  const CURRENT_USER_KEY = 'sms_current_user';

  // Get school ID from local storage
  function getSchoolId() {
    return localStorage.getItem(CURRENT_SCHOOL_KEY) || '';
  }

  // Set school ID
  function setSchoolId(schoolId) {
    if (!schoolId) return;
    localStorage.setItem(CURRENT_SCHOOL_KEY, schoolId);
  }

  // Check if Supabase is configured
  function isSupabaseConfigured() {
    const config = window.SUPABASE_CONFIG;
    return config && config.url && config.url !== 'YOUR_SUPABASE_PROJECT_URL';
  }

  // Build headers for API requests
  function buildHeaders(extraHeaders) {
    const headers = {
      'Content-Type': 'application/json',
      ...(extraHeaders || {})
    };

    const schoolId = getSchoolId();
    if (schoolId) {
      headers['X-School-ID'] = schoolId;
    }

    return headers;
  }

  // Generic request handler
  async function request(path, options = {}) {
    try {
      const response = await fetch(path, {
        method: options.method || 'GET',
        ...options,
        headers: buildHeaders(options.headers)
      });

      const payload = await response.json();
      if (!response.ok) {
        return { ok: false, message: payload.message || 'Request failed.' };
      }
      return payload;
    } catch (error) {
      console.error('API Error:', error);
      return { ok: false, message: 'Cannot connect to the API server. Ensure Python server is running: python3 server.py' };
    }
  }

  // Supabase client functions (when configured)
  async function supabaseRequest(table, operation, filters = {}, data = null) {
    if (!isSupabaseConfigured()) {
      return { ok: false, message: 'Supabase not configured. Please set up your Supabase credentials.' };
    }

    try {
      let query = window.supabaseClient.from(table);

      switch(operation) {
        case 'select':
          if (filters.select) query = query.select(filters.select);
          else query = query.select('*');
          
          if (filters.eq) {
            for (const [key, value] of Object.entries(filters.eq)) {
              query = query.eq(key, value);
            }
          }
          if (filters.order) {
            query = query.order(filters.order.column, { ascending: filters.order.ascending });
          }
          if (filters.limit) {
            query = query.limit(filters.limit);
          }
          break;
          
        case 'insert':
          const insertResult = await query.insert(data);
          if (insertResult.error) throw insertResult.error;
          return { ok: true, data: insertResult.data };
          
        case 'update':
          const updateResult = await query.update(data).eq(filters.eq.idColumn, filters.eq.id);
          if (updateResult.error) throw updateResult.error;
          return { ok: true, data: updateResult.data };
          
        case 'delete':
          const deleteResult = await query.eq(filters.eq.idColumn, filters.eq.id).delete();
          if (deleteResult.error) throw deleteResult.error;
          return { ok: true };
      }

      const result = await query;
      if (result.error) throw result.error;
      return { ok: true, data: result.data };
    } catch (error) {
      console.error('Supabase Error:', error);
      return { ok: false, message: error.message };
    }
  }

  // ============ DATA OPERATIONS ============

  // Get all data for current school
  async function getData() {
    // First try local API (Python server)
    const result = await request('/api/data');
    if (result.ok) return result.data;
    
    // Fallback: Return empty data structure
    return {
      meta: { schoolName: '', schoolId: '' },
      staff: [],
      students: [],
      applications: [],
      courses: [],
      registrations: [],
      attendance: [],
      examResults: [],
      announcements: [],
      departments: [],
      programs: [],
      levels: []
    };
  }

  // Get overview metrics
  async function getOverviewMetrics() {
    const data = await getData();
    const totalStudents = data.students?.length || 0;
    const totalStaff = data.staff?.length || 0;
    const pendingApplications = data.applications?.filter(a => a.status === 'pending').length || 0;
    const recordedResults = data.examResults?.length || 0;

    let latestAttendancePct = 0;
    if (data.attendance?.length > 0) {
      const latest = data.attendance[0];
      const total = (latest.presentStudentIds?.length || 0) + (latest.absentStudentIds?.length || 0);
      latestAttendancePct = total === 0 ? 0 : Math.round((latest.presentStudentIds?.length / total) * 100);
    }

    return {
      totalStudents,
      totalStaff,
      pendingApplications,
      recordedResults,
      attendanceRate: latestAttendancePct
    };
  }

  // ============ SCHOOL OPERATIONS ============

  async function createSchoolAccount(payload) {
    const result = await request('/api/schools/register', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    if (!result.ok) return result;
    setSchoolId(result.school.id);
    return result;
  }

  async function loginSchool(email, password) {
    const result = await request('/api/schools/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });

    if (!result.ok) return result;
    setSchoolId(result.school.id);
    return result;
  }

  function logoutSchool() {
    localStorage.removeItem(CURRENT_SCHOOL_KEY);
    localStorage.removeItem(CURRENT_STAFF_KEY);
    localStorage.removeItem(CURRENT_STUDENT_KEY);
    localStorage.removeItem(CURRENT_USER_KEY);
  }

  async function getCurrentSchool() {
    const schoolId = getSchoolId();
    if (!schoolId) return null;

    const result = await request('/api/schools/' + encodeURIComponent(schoolId));
    if (!result.ok) {
      localStorage.removeItem(CURRENT_SCHOOL_KEY);
      return null;
    }
    return result.school;
  }

  // ============ STUDENT OPERATIONS ============

  async function submitApplication(payload) {
    return request('/api/admissions', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async function loginStudent(identifier, password) {
    const result = await request('/api/auth/student-login', {
      method: 'POST',
      body: JSON.stringify({ identifier, password })
    });

    if (!result.ok) return result;
    localStorage.setItem(CURRENT_STUDENT_KEY, result.student.id);
    return result;
  }

  function logoutStudent() {
    localStorage.removeItem(CURRENT_STUDENT_KEY);
  }

  async function getCurrentStudent() {
    const id = localStorage.getItem(CURRENT_STUDENT_KEY);
    if (!id) return null;

    const result = await request('/api/students/' + encodeURIComponent(id));
    if (!result.ok) return null;
    return result.student;
  }

  // ============ STAFF OPERATIONS ============

  async function loginStaff(identifier, password) {
    const result = await request('/api/auth/staff-login', {
      method: 'POST',
      body: JSON.stringify({ identifier, password })
    });

    if (!result.ok) return result;
    localStorage.setItem(CURRENT_STAFF_KEY, result.staff.id);
    return result;
  }

  async function loginTeacher(identifier, password) {
    return loginStaff(identifier, password);
  }

  function logoutStaff() {
    localStorage.removeItem(CURRENT_STAFF_KEY);
  }

  function logoutTeacher() {
    logoutStaff();
  }

  async function getCurrentStaff() {
    const id = localStorage.getItem(CURRENT_STAFF_KEY);
    if (!id) return null;

    const result = await request('/api/staff/' + encodeURIComponent(id));
    if (!result.ok) return null;
    return result.staff;
  }

  async function getCurrentTeacher() {
    return getCurrentStaff();
  }

  // ============ COURSE OPERATIONS ============

  async function registerCourses(input) {
    return request('/api/registrations', {
      method: 'POST',
      body: JSON.stringify(input)
    });
  }

  async function addCourse(payload, staffName) {
    return request('/api/courses', {
      method: 'POST',
      body: JSON.stringify({ ...payload, staffName, teacherName: staffName })
    });
  }

  async function toggleCourseActive(courseId) {
    return request('/api/courses/' + encodeURIComponent(courseId) + '/toggle', {
      method: 'POST',
      body: JSON.stringify({})
    });
  }

  // ============ ATTENDANCE OPERATIONS ============

  async function saveAttendance(payload, staffId) {
    return request('/api/attendance', {
      method: 'POST',
      body: JSON.stringify({ ...payload, staffId, teacherId: staffId })
    });
  }

  // ============ APPLICATION OPERATIONS ============

  async function approveApplication(appId, staffId) {
    return request('/api/applications/' + encodeURIComponent(appId) + '/approve', {
      method: 'POST',
      body: JSON.stringify({ staffId, teacherId: staffId })
    });
  }

  async function rejectApplication(appId) {
    return request('/api/applications/' + encodeURIComponent(appId) + '/reject', {
      method: 'POST',
      body: JSON.stringify({})
    });
  }

  // ============ STAFF MANAGEMENT ============

  async function addStaff(payload) {
    return request('/api/staff', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  // ============ EXAM RESULTS ============

  async function addExamResult(payload, staffId) {
    return request('/api/exam-results', {
      method: 'POST',
      body: JSON.stringify({ ...payload, staffId })
    });
  }

  // ============ SUPABASE DIRECT OPERATIONS ============

  // Direct Supabase operations (when configured)
  async function getSupabaseData(table, schoolId, options = {}) {
    if (!isSupabaseConfigured()) {
      return { ok: false, message: 'Supabase not configured' };
    }
    
    try {
      let query = window.supabaseClient.from(table).select('*');
      
      if (schoolId) {
        query = query.eq('school_id', schoolId);
      }
      
      if (options.orderBy) {
        query = query.order(options.orderBy, { ascending: options.ascending || false });
      }
      
      if (options.limit) {
        query = query.limit(options.limit);
      }
      
      const { data, error } = await query;
      if (error) throw error;
      return { ok: true, data };
    } catch (error) {
      return { ok: false, message: error.message };
    }
  }

  async function insertSupabaseData(table, data) {
    if (!isSupabaseConfigured()) {
      return { ok: false, message: 'Supabase not configured' };
    }
    
    try {
      const { data: result, error } = await window.supabaseClient.from(table).insert(data);
      if (error) throw error;
      return { ok: true, data: result };
    } catch (error) {
      return { ok: false, message: error.message };
    }
  }

  async function updateSupabaseData(table, id, data) {
    if (!isSupabaseConfigured()) {
      return { ok: false, message: 'Supabase not configured' };
    }
    
    try {
      const { data: result, error } = await window.supabaseClient.from(table).update(data).eq('id', id);
      if (error) throw error;
      return { ok: true, data: result };
    } catch (error) {
      return { ok: false, message: error.message };
    }
  }

  async function deleteSupabaseData(table, id) {
    if (!isSupabaseConfigured()) {
      return { ok: false, message: 'Supabase not configured' };
    }
    
    try {
      const { error } = await window.supabaseClient.from(table).delete().eq('id', id);
      if (error) throw error;
      return { ok: true };
    } catch (error) {
      return { ok: false, message: error.message };
    }
  }

  // ============ AUTH OPERATIONS (Supabase) ============

  async function signUp(email, password, metadata = {}) {
    if (!isSupabaseConfigured()) {
      return { ok: false, message: 'Supabase not configured' };
    }
    
    try {
      const { data, error } = await window.supabaseClient.auth.signUp({
        email,
        password,
        options: { data: metadata }
      });
      if (error) throw error;
      return { ok: true, data };
    } catch (error) {
      return { ok: false, message: error.message };
    }
  }

  async function signIn(email, password) {
    if (!isSupabaseConfigured()) {
      // Fall back to local auth
      return loginStaff(email, password);
    }
    
    try {
      const { data, error } = await window.supabaseClient.auth.signInWithPassword({
        email,
        password
      });
      if (error) throw error;
      localStorage.setItem(CURRENT_USER_KEY, data.user.id);
      return { ok: true, data };
    } catch (error) {
      return { ok: false, message: error.message };
    }
  }

  async function signOut() {
    if (!isSupabaseConfigured()) {
      logoutSchool();
      return { ok: true };
    }
    
    try {
      const { error } = await window.supabaseClient.auth.signOut();
      if (error) throw error;
      logoutSchool();
      return { ok: true };
    } catch (error) {
      return { ok: false, message: error.message };
    }
  }

  async function getCurrentUser() {
    if (!isSupabaseConfigured()) {
      return null;
    }
    
    try {
      const { data: { user } } = await window.supabaseClient.auth.getUser();
      return user;
    } catch (error) {
      return null;
    }
  }

  // ============ EXPORT API ============

  window.SMSStore = {
    // Configuration
    isSupabaseConfigured,
    
    // Data operations
    getData,
    getOverviewMetrics,
    
    // School operations
    createSchoolAccount,
    loginSchool,
    logoutSchool,
    getCurrentSchool,
    
    // Student operations
    submitApplication,
    loginStudent,
    logoutStudent,
    getCurrentStudent,
    
    // Staff operations
    loginStaff,
    loginTeacher,
    logoutStaff,
    logoutTeacher,
    getCurrentStaff,
    getCurrentTeacher,
    
    // Course operations
    registerCourses,
    addCourse,
    toggleCourseActive,
    
    // Attendance
    saveAttendance,
    
    // Applications
    approveApplication,
    rejectApplication,
    
    // Staff management
    addStaff,
    
    // Exam results
    addExamResult,
    
    // Supabase direct operations
    getSupabaseData,
    insertSupabaseData,
    updateSupabaseData,
    deleteSupabaseData,
    
    // Auth
    signUp,
    signIn,
    signOut,
    getCurrentUser
  };

})();

