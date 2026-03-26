(function () {
  function byId(id) {
    return document.getElementById(id);
  }

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function setMessage(id, text, isError) {
    const el = byId(id);
    if (!el) {
      return;
    }
    el.textContent = text;
    el.classList.remove("error", "success");
    el.classList.add(isError ? "error" : "success");
  }

  function isAdminStaff(staff) {
    return String(staff && staff.role ? staff.role : "")
      .toLowerCase()
      .indexOf("admin") !== -1;
  }

  async function ensureAuth() {
    const staff = await SMSStore.getCurrentStaff();
    if (!staff) {
      window.location.href = "teacher-login.html";
      return null;
    }
    if (!isAdminStaff(staff)) {
      window.alert("Admin access only.");
      window.location.href = "teacher-login.html";
      return null;
    }

    const school = await SMSStore.getCurrentSchool();
    return { school: school, staff: staff };
  }

  function switchTab(tab) {
    document.querySelectorAll(".tab-btn").forEach(function (button) {
      button.classList.toggle("active", button.dataset.tab === tab);
    });
    document.querySelectorAll(".tab-panel").forEach(function (panel) {
      panel.classList.toggle("active", panel.id === "tab-" + tab);
    });
  }

  function renderOverview(data, metrics) {
    const stats = byId("dashboardStats");
    if (stats) {
      stats.innerHTML = [
        ["Total Students", metrics.totalStudents],
        ["Total Staff", metrics.totalStaff],
        ["Pending Applications", metrics.pendingApplications],
        ["Recorded Results", metrics.recordedResults],
        ["Latest Attendance", metrics.attendanceRate + "%"]
      ]
        .map(function (row) {
          return "<div class=\"stat-card\"><span>" + row[0] + "</span><strong>" + row[1] + "</strong></div>";
        })
        .join("");
    }

    const appList = byId("recentApplications");
    if (appList) {
      const recentApps = data.applications.slice(0, 5);
      appList.innerHTML = recentApps.length
        ? recentApps
            .map(function (app) {
              return (
                "<li><strong>" +
                escapeHtml(app.fullName) +
                "</strong> - <span class=\"badge " +
                escapeHtml(app.status) +
                "\">" +
                escapeHtml(app.status) +
                "</span> (" +
                app.submittedOn +
                ")</li>"
              );
            })
            .join("")
        : '<li class="empty">No applications.</li>';
    }

    const resultList = byId("recentResults");
    if (resultList) {
      const recent = data.examResults.slice(0, 5);
      resultList.innerHTML = recent.length
        ? recent
            .map(function (item) {
              return (
                "<li><strong>" +
                escapeHtml(item.studentName) +
                "</strong> - " +
                escapeHtml(item.subject) +
                ": " +
                escapeHtml(String(item.score)) +
                "% (" +
                escapeHtml(item.grade) +
                ")</li>"
              );
            })
            .join("")
        : '<li class="empty">No exam results yet.</li>';
    }
  }

  function renderStudents(data, searchValue) {
    const tbody = byId("studentsTableBody");
    if (!tbody) {
      return;
    }

    const query = (searchValue || "").trim().toLowerCase();
    const rows = data.students.filter(function (student) {
      if (!query) {
        return true;
      }
      const haystack = [student.id, student.name, student.program, student.email]
        .join(" ")
        .toLowerCase();
      return haystack.indexOf(query) !== -1;
    });

    tbody.innerHTML = rows.length
      ? rows
          .map(function (student) {
            return (
              "<tr><td>" +
              escapeHtml(student.id) +
              "</td><td>" +
              escapeHtml(student.name) +
              "</td><td>" +
              escapeHtml(student.email) +
              "</td><td>" +
              escapeHtml(student.program) +
              "</td><td>" +
              escapeHtml(student.level) +
              "</td><td><span class=\"badge " +
              escapeHtml(student.status) +
              "\">" +
              escapeHtml(student.status) +
              "</span></td></tr>"
            );
          })
          .join("")
      : '<tr><td colspan="6" class="empty">No students found.</td></tr>';
  }

  function renderApplications(data) {
    const grid = byId("applicationsGrid");
    if (!grid) {
      return;
    }

    const applications = data.applications;

    if (!applications.length) {
      grid.innerHTML = '<p class="empty">No applications available.</p>';
      return;
    }

    grid.innerHTML = applications
      .map(function (app) {
        const actionButtons =
          app.status === "pending"
            ? '<div class="action-row">' +
              '<button class="btn btn-primary app-action" data-action="approve" data-app-id="' +
              app.id +
              '">Approve</button>' +
              '<button class="btn btn-danger app-action" data-action="reject" data-app-id="' +
              app.id +
              '">Reject</button></div>'
            : "";

        return (
          '<article class="app-card">' +
          "<h3>" +
          escapeHtml(app.fullName) +
          "</h3>" +
          '<p><span class="badge ' +
          escapeHtml(app.status) +
          '">' +
          escapeHtml(app.status) +
          "</span></p>" +
          "<p><strong>Program:</strong> " +
          escapeHtml(app.programFirstChoice) +
          "</p>" +
          "<p><strong>Email:</strong> " +
          escapeHtml(app.email) +
          "</p>" +
          "<p><strong>Phone:</strong> " +
          escapeHtml(app.phone) +
          "</p>" +
          "<p><strong>Submitted:</strong> " +
          escapeHtml(app.submittedOn) +
          "</p>" +
          actionButtons +
          "</article>"
        );
      })
      .join("");
  }

  function renderCourses(data) {
    const grid = byId("coursesGrid");
    const select = byId("attendanceCourse");

    if (grid) {
      grid.innerHTML = data.courses
        .map(function (course) {
          return (
            '<article class="course-card">' +
            "<h3>" +
            escapeHtml(course.code) +
            " - " +
            escapeHtml(course.title) +
            "</h3>" +
            "<p><strong>Program:</strong> " +
            escapeHtml(course.program) +
            " | Level " +
            escapeHtml(course.level) +
            "</p>" +
            "<p><strong>Credits:</strong> " +
            course.credits +
            " | <strong>Seats:</strong> " +
            course.seats +
            "</p>" +
            "<p><span class=\"badge " +
            (course.active ? "active" : "inactive") +
            "\">" +
            (course.active ? "active" : "inactive") +
            "</span></p>" +
            '<button class="btn btn-secondary course-toggle" data-course-id="' +
            course.id +
            '">' +
            (course.active ? "Deactivate" : "Activate") +
            "</button>" +
            "</article>"
          );
        })
        .join("");
    }

    if (select) {
      const options = data.courses
        .filter(function (course) {
          return course.active;
        })
        .map(function (course) {
          return "<option value=\"" + course.id + "\">" + course.code + " - " + course.title + "</option>";
        });

      select.innerHTML = '<option value="">Select active course</option>' + options.join("");
    }
  }

  function renderAttendanceStudents(data) {
    const list = byId("attendanceStudentList");
    if (!list) {
      return;
    }

    list.innerHTML = data.students
      .map(function (student) {
        return (
          '<label class="check-item">' +
          '<input type="checkbox" name="presentStudentIds" value="' +
          student.id +
          '">' +
          "<span><strong>" +
          escapeHtml(student.name) +
          "</strong><small>" +
          escapeHtml(student.id) +
          " | " +
          escapeHtml(student.program) +
          "</small></span></label>"
        );
      })
      .join("");
  }

  function renderStaff(data) {
    const tbody = byId("staffTableBody");
    if (!tbody) {
      return;
    }

    tbody.innerHTML = data.staff.length
      ? data.staff
          .map(function (staff) {
            return (
              "<tr><td>" +
              escapeHtml(staff.id) +
              "</td><td>" +
              escapeHtml(staff.name) +
              "</td><td>" +
              escapeHtml(staff.email) +
              "</td><td>" +
              escapeHtml(staff.role) +
              "</td><td>" +
              escapeHtml(staff.department) +
              "</td><td><span class=\"badge " +
              escapeHtml(staff.status) +
              "\">" +
              escapeHtml(staff.status) +
              "</span></td></tr>"
            );
          })
          .join("")
      : '<tr><td colspan="6" class="empty">No staff records found.</td></tr>';

    const resultSelect = byId("resultStudentId");
    if (resultSelect) {
      const studentOptions = data.students
        .map(function (student) {
          return '<option value="' + escapeHtml(student.id) + '">' + escapeHtml(student.id + " - " + student.name) + "</option>";
        })
        .join("");
      resultSelect.innerHTML = '<option value="">Select student</option>' + studentOptions;
    }
  }

  function renderExamResults(data) {
    const tbody = byId("examResultsBody");
    if (!tbody) {
      return;
    }

    tbody.innerHTML = data.examResults.length
      ? data.examResults
          .map(function (item) {
            return (
              "<tr><td>" +
              escapeHtml(item.recordedOn) +
              "</td><td>" +
              escapeHtml(item.studentName) +
              "</td><td>" +
              escapeHtml(item.term) +
              "</td><td>" +
              escapeHtml(item.subject) +
              "</td><td>" +
              escapeHtml(String(item.score)) +
              "</td><td><strong>" +
              escapeHtml(item.grade) +
              "</strong></td><td>" +
              escapeHtml(item.recordedByName || item.recordedBy || "-") +
              "</td></tr>"
            );
          })
          .join("")
      : '<tr><td colspan="7" class="empty">No exam results recorded yet.</td></tr>';
  }

  function renderReport(data, type) {
    const output = byId("reportOutput");
    if (!output) {
      return;
    }

    if (type === "students") {
      const byProgram = {};
      data.students.forEach(function (student) {
        byProgram[student.program] = (byProgram[student.program] || 0) + 1;
      });
      output.innerHTML = Object.keys(byProgram)
        .map(function (program) {
          return "<p><strong>" + escapeHtml(program) + "</strong>: " + byProgram[program] + " students</p>";
        })
        .join("");
      return;
    }

    if (type === "attendance") {
      if (!data.attendance.length) {
        output.innerHTML = '<p class="empty">No attendance records available.</p>';
        return;
      }
      const rows = data.attendance.slice(0, 8).map(function (entry) {
        const course = data.courses.find(function (item) {
          return item.id === entry.courseId;
        });
        const total = entry.presentStudentIds.length + entry.absentStudentIds.length;
        const pct = total ? Math.round((entry.presentStudentIds.length / total) * 100) : 0;
        return (
          "<p><strong>" +
          escapeHtml(entry.date) +
          "</strong> - " +
          escapeHtml(course ? course.code : entry.courseId) +
          ": " +
          pct +
          "% present</p>"
        );
      });
      output.innerHTML = rows.join("");
      return;
    }

    if (type === "results") {
      if (!data.examResults.length) {
        output.innerHTML = '<p class="empty">No exam results available.</p>';
        return;
      }
      const avg = Math.round(
        data.examResults.reduce(function (sum, item) {
          return sum + Number(item.score || 0);
        }, 0) / data.examResults.length
      );
      output.innerHTML =
        "<p><strong>Total records:</strong> " +
        data.examResults.length +
        "</p><p><strong>Average score:</strong> " +
        avg +
        "%</p>";
      return;
    }

    if (type === "applications") {
      const summary = { pending: 0, approved: 0, rejected: 0 };
      data.applications.forEach(function (app) {
        summary[app.status] = (summary[app.status] || 0) + 1;
      });

      output.innerHTML =
        "<p><strong>Pending:</strong> " +
        summary.pending +
        "</p><p><strong>Approved:</strong> " +
        summary.approved +
        "</p><p><strong>Rejected:</strong> " +
        summary.rejected +
        "</p>";
    }
  }

  async function renderJobApplications() {
    const grid = byId("jobApplicationsGrid");
    if (!grid) {
      return;
    }

    try {
      const headers = { 'Content-Type': 'application/json' };
      const schoolId = localStorage.getItem('sms_current_school');
      if (schoolId) {
        headers['X-School-ID'] = schoolId;
      }

      const response = await fetch('/api/job-applications/list', {
        method: 'GET',
        headers: headers
      });
      const result = await response.json();

      if (!result.ok || !result.jobApplications || result.jobApplications.length === 0) {
        grid.innerHTML = '<p class="empty">No job applications received yet.</p>';
        return;
      }

      grid.innerHTML = result.jobApplications
        .map(function (app) {
          return (
            '<article class="app-card">' +
            "<h3>" + escapeHtml(app.fullName) + "</h3>" +
            '<p><span class="badge ' + escapeHtml(app.status) + '">' + escapeHtml(app.status) + '</span></p>' +
            "<p><strong>Position:</strong> " + escapeHtml(app.position) + "</p>" +
            "<p><strong>Department:</strong> " + escapeHtml(app.department) + "</p>" +
            "<p><strong>Email:</strong> " + escapeHtml(app.email) + "</p>" +
            "<p><strong>Phone:</strong> " + escapeHtml(app.phone) + "</p>" +
            "<p><strong>Qualification:</strong> " + escapeHtml(app.qualification) + "</p>" +
            "<p><strong>Experience:</strong> " + app.experience + " years</p>" +
            "<p><strong>Submitted:</strong> " + escapeHtml(app.submittedOn) + "</p>" +
            (app.cvFileName ? "<p><strong>CV:</strong> " + escapeHtml(app.cvFileName) + "</p>" : "") +
            (app.notes ? "<p><strong>Notes:</strong> " + escapeHtml(app.notes.substring(0, 100)) + (app.notes.length > 100 ? '...' : '') + "</p>" : "") +
            "</article>"
          );
        })
        .join("");
    } catch (e) {
      console.error('Error loading job applications:', e);
      grid.innerHTML = '<p class="empty">Could not load job applications.</p>';
    }
  }

  async function refreshDashboard(searchValue) {
    const [data, metrics] = await Promise.all([SMSStore.getData(), SMSStore.getOverviewMetrics()]);
    renderOverview(data, metrics);
    renderStudents(data, searchValue || "");
    renderApplications(data);
    renderCourses(data);
    renderAttendanceStudents(data);
    renderStaff(data);
    renderExamResults(data);
    return data;
  }

  function bindEvents(context) {
    const staff = context.staff;

    document.querySelectorAll(".tab-btn").forEach(function (button) {
      button.addEventListener("click", function () {
        switchTab(button.dataset.tab);
        
        // Load job applications when that tab is clicked
        if (button.dataset.tab === "job-applications") {
          renderJobApplications();
        }
      });
    });

    const search = byId("studentSearch");
    if (search) {
      search.addEventListener("input", async function () {
        const data = await SMSStore.getData();
        renderStudents(data, search.value);
      });
    }

    const appGrid = byId("applicationsGrid");
    if (appGrid) {
      appGrid.addEventListener("click", async function (event) {
        const button = event.target.closest(".app-action");
        if (!button) {
          return;
        }

        const appId = button.dataset.appId;
        const action = button.dataset.action;
        let result;

        if (action === "approve") {
          result = await SMSStore.approveApplication(appId, staff.id);
        } else {
          result = await SMSStore.rejectApplication(appId);
        }

        if (!result.ok) {
          window.alert(result.message);
          return;
        }

        await refreshDashboard(byId("studentSearch") ? byId("studentSearch").value : "");
      });
    }

    const courseForm = byId("courseForm");
    if (courseForm) {
      courseForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        const formData = new FormData(courseForm);
        const result = await SMSStore.addCourse(
          {
            code: String(formData.get("code") || "").trim(),
            title: String(formData.get("title") || "").trim(),
            program: String(formData.get("program") || "").trim(),
            level: String(formData.get("level") || "").trim(),
            credits: Number(formData.get("credits") || 3),
            seats: Number(formData.get("seats") || 30)
          },
          staff.name
        );

        if (!result.ok) {
          setMessage("courseMessage", result.message, true);
          return;
        }

        courseForm.reset();
        setMessage("courseMessage", result.message, false);
        await refreshDashboard(byId("studentSearch") ? byId("studentSearch").value : "");
      });
    }

    const coursesGrid = byId("coursesGrid");
    if (coursesGrid) {
      coursesGrid.addEventListener("click", async function (event) {
        const button = event.target.closest(".course-toggle");
        if (!button) {
          return;
        }

        const courseId = button.dataset.courseId;
        const result = await SMSStore.toggleCourseActive(courseId);
        if (!result.ok) {
          window.alert(result.message);
          return;
        }

        await refreshDashboard(byId("studentSearch") ? byId("studentSearch").value : "");
      });
    }

    const attendanceForm = byId("attendanceForm");
    if (attendanceForm) {
      attendanceForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const formData = new FormData(attendanceForm);
        const presentIds = Array.from(
          attendanceForm.querySelectorAll('input[name="presentStudentIds"]:checked')
        ).map(function (checkbox) {
          return checkbox.value;
        });

        const result = await SMSStore.saveAttendance(
          {
            date: String(formData.get("date") || ""),
            courseId: String(formData.get("courseId") || ""),
            presentStudentIds: presentIds
          },
          staff.id
        );

        if (!result.ok) {
          setMessage("attendanceMessage", result.message, true);
          return;
        }

        setMessage("attendanceMessage", result.message, false);
        await refreshDashboard(byId("studentSearch") ? byId("studentSearch").value : "");
      });
    }

    const staffForm = byId("staffForm");
    if (staffForm) {
      staffForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const formData = new FormData(staffForm);
        const result = await SMSStore.addStaff({
          name: String(formData.get("name") || "").trim(),
          email: String(formData.get("email") || "").trim(),
          role: String(formData.get("role") || "").trim(),
          department: String(formData.get("department") || "").trim(),
          password: String(formData.get("password") || "").trim()
        });

        if (!result.ok) {
          setMessage("staffMessage", result.message, true);
          return;
        }

        staffForm.reset();
        setMessage(
          "staffMessage",
          "Staff account created: " + result.staffId + " | password: " + result.defaultPassword,
          false
        );
        await refreshDashboard(byId("studentSearch") ? byId("studentSearch").value : "");
      });
    }

    const examForm = byId("examResultForm");
    if (examForm) {
      examForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const formData = new FormData(examForm);
        const result = await SMSStore.addExamResult(
          {
            studentId: String(formData.get("studentId") || "").trim(),
            term: String(formData.get("term") || "").trim(),
            subject: String(formData.get("subject") || "").trim(),
            score: Number(formData.get("score") || 0),
            grade: String(formData.get("grade") || "").trim().toUpperCase()
          },
          staff.id
        );

        if (!result.ok) {
          setMessage("examResultMessage", result.message, true);
          return;
        }

        examForm.reset();
        setMessage("examResultMessage", result.message, false);
        await refreshDashboard(byId("studentSearch") ? byId("studentSearch").value : "");
      });
    }

    document.querySelectorAll("[data-report]").forEach(function (button) {
      button.addEventListener("click", async function () {
        const data = await SMSStore.getData();
        renderReport(data, button.dataset.report);
      });
    });

    const logoutBtn = byId("logoutBtn");
    if (logoutBtn) {
      logoutBtn.addEventListener("click", function () {
        SMSStore.logoutStaff();
        window.location.href = "teacher-login.html";
      });
    }

  }

  async function init() {
    if (!["dashboard", "admin-dashboard"].includes(document.body.dataset.page || "")) {
      return;
    }

    const context = await ensureAuth();
    if (!context) {
      return;
    }

    const userLabel = byId("dashboardUser");
    if (userLabel) {
      userLabel.textContent = context.staff.name + " - " + context.staff.role;
    }

    await refreshDashboard("");

    const attendanceDate = document.querySelector('#attendanceForm input[name="date"]');
    if (attendanceDate) {
      attendanceDate.value = new Date().toISOString().slice(0, 10);
    }

    bindEvents(context);
  }

  document.addEventListener("DOMContentLoaded", function () {
    init();
  });
})();
