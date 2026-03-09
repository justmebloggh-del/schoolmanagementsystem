(function () {
  const CURRENT_STUDENT_KEY = "sms_current_student";
  const CURRENT_STAFF_KEY = "sms_current_staff";
  const CURRENT_SCHOOL_KEY = "sms_current_school";

  function getSchoolId() {
    return localStorage.getItem(CURRENT_SCHOOL_KEY) || "";
  }

  function setSchoolId(schoolId) {
    if (!schoolId) {
      return;
    }
    localStorage.setItem(CURRENT_SCHOOL_KEY, schoolId);
  }

  function buildHeaders(extraHeaders) {
    const headers = {
      "Content-Type": "application/json",
      ...(extraHeaders || {})
    };

    const schoolId = getSchoolId();
    if (schoolId) {
      headers["X-School-ID"] = schoolId;
    }

    return headers;
  }

  async function request(path, options) {
    try {
      const response = await fetch(path, {
        method: "GET",
        ...options,
        headers: buildHeaders(options ? options.headers : {})
      });

      const payload = await response.json();
      if (!response.ok) {
        return {
          ok: false,
          message: payload.message || "Request failed."
        };
      }
      return payload;
    } catch (error) {
      return {
        ok: false,
        message: "Cannot connect to the API server. Start it with: python3 server.py"
      };
    }
  }

  async function getData() {
    const result = await request("/api/data");
    if (!result.ok) {
      return {
        meta: { schoolName: "", schoolId: "" },
        staff: [],
        teachers: [],
        students: [],
        applications: [],
        courses: [],
        registrations: [],
        attendance: [],
        examResults: [],
        announcements: []
      };
    }
    return result.data;
  }

  async function createSchoolAccount(payload) {
    const result = await request("/api/schools/register", {
      method: "POST",
      body: JSON.stringify(payload)
    });

    if (!result.ok) {
      return result;
    }

    setSchoolId(result.school.id);
    return result;
  }

  async function loginSchool(email, password) {
    const result = await request("/api/schools/login", {
      method: "POST",
      body: JSON.stringify({ email: email, password: password })
    });

    if (!result.ok) {
      return result;
    }

    setSchoolId(result.school.id);
    return result;
  }

  function logoutSchool() {
    localStorage.removeItem(CURRENT_SCHOOL_KEY);
    localStorage.removeItem(CURRENT_STAFF_KEY);
    localStorage.removeItem(CURRENT_STUDENT_KEY);
  }

  async function getCurrentSchool() {
    const schoolId = getSchoolId();
    if (!schoolId) {
      return null;
    }

    const result = await request("/api/schools/" + encodeURIComponent(schoolId));
    if (!result.ok) {
      localStorage.removeItem(CURRENT_SCHOOL_KEY);
      return null;
    }
    return result.school;
  }

  async function submitApplication(payload) {
    return request("/api/admissions", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  async function loginStudent(identifier, password) {
    const result = await request("/api/auth/student-login", {
      method: "POST",
      body: JSON.stringify({ identifier: identifier, password: password })
    });

    if (!result.ok) {
      return result;
    }

    localStorage.setItem(CURRENT_STUDENT_KEY, result.student.id);
    return result;
  }

  async function loginStaff(identifier, password) {
    const result = await request("/api/auth/staff-login", {
      method: "POST",
      body: JSON.stringify({ identifier: identifier, password: password })
    });

    if (!result.ok) {
      return result;
    }

    localStorage.setItem(CURRENT_STAFF_KEY, result.staff.id);
    return result;
  }

  async function loginTeacher(identifier, password) {
    return loginStaff(identifier, password);
  }

  function logoutStudent() {
    localStorage.removeItem(CURRENT_STUDENT_KEY);
  }

  function logoutStaff() {
    localStorage.removeItem(CURRENT_STAFF_KEY);
  }

  function logoutTeacher() {
    logoutStaff();
  }

  async function getCurrentStudent() {
    const id = localStorage.getItem(CURRENT_STUDENT_KEY);
    if (!id) {
      return null;
    }

    const result = await request("/api/students/" + encodeURIComponent(id));
    if (!result.ok) {
      return null;
    }
    return result.student;
  }

  async function getCurrentStaff() {
    const id = localStorage.getItem(CURRENT_STAFF_KEY);
    if (!id) {
      return null;
    }

    const result = await request("/api/staff/" + encodeURIComponent(id));
    if (!result.ok) {
      return null;
    }
    return result.staff;
  }

  async function getCurrentTeacher() {
    return getCurrentStaff();
  }

  async function registerCourses(input) {
    return request("/api/registrations", {
      method: "POST",
      body: JSON.stringify(input)
    });
  }

  async function approveApplication(appId, staffId) {
    return request("/api/applications/" + encodeURIComponent(appId) + "/approve", {
      method: "POST",
      body: JSON.stringify({ staffId: staffId, teacherId: staffId })
    });
  }

  async function rejectApplication(appId) {
    return request("/api/applications/" + encodeURIComponent(appId) + "/reject", {
      method: "POST",
      body: JSON.stringify({})
    });
  }

  async function addCourse(payload, staffName) {
    return request("/api/courses", {
      method: "POST",
      body: JSON.stringify({ ...payload, staffName: staffName, teacherName: staffName })
    });
  }

  async function toggleCourseActive(courseId) {
    return request("/api/courses/" + encodeURIComponent(courseId) + "/toggle", {
      method: "POST",
      body: JSON.stringify({})
    });
  }

  async function saveAttendance(payload, staffId) {
    return request("/api/attendance", {
      method: "POST",
      body: JSON.stringify({ ...payload, staffId: staffId, teacherId: staffId })
    });
  }

  async function addStaff(payload) {
    return request("/api/staff", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  async function addExamResult(payload, staffId) {
    return request("/api/exam-results", {
      method: "POST",
      body: JSON.stringify({ ...payload, staffId: staffId })
    });
  }

  async function getOverviewMetrics() {
    const data = await getData();
    const totalStudents = data.students.length;
    const totalStaff = data.staff.length;
    const pendingApplications = data.applications.filter(function (item) {
      return item.status === "pending";
    }).length;
    const recordedResults = data.examResults.length;

    let latestAttendancePct = 0;
    if (data.attendance.length > 0) {
      const latest = data.attendance[0];
      const total = latest.presentStudentIds.length + latest.absentStudentIds.length;
      latestAttendancePct = total === 0 ? 0 : Math.round((latest.presentStudentIds.length / total) * 100);
    }

    return {
      totalStudents: totalStudents,
      totalStaff: totalStaff,
      pendingApplications: pendingApplications,
      recordedResults: recordedResults,
      attendanceRate: latestAttendancePct
    };
  }

  window.SMSStore = {
    getData: getData,
    createSchoolAccount: createSchoolAccount,
    loginSchool: loginSchool,
    logoutSchool: logoutSchool,
    getCurrentSchool: getCurrentSchool,
    submitApplication: submitApplication,
    loginStudent: loginStudent,
    loginStaff: loginStaff,
    loginTeacher: loginTeacher,
    logoutStudent: logoutStudent,
    logoutStaff: logoutStaff,
    logoutTeacher: logoutTeacher,
    getCurrentStudent: getCurrentStudent,
    getCurrentStaff: getCurrentStaff,
    getCurrentTeacher: getCurrentTeacher,
    registerCourses: registerCourses,
    approveApplication: approveApplication,
    rejectApplication: rejectApplication,
    addCourse: addCourse,
    toggleCourseActive: toggleCourseActive,
    saveAttendance: saveAttendance,
    addStaff: addStaff,
    addExamResult: addExamResult,
    getOverviewMetrics: getOverviewMetrics
  };
})();
