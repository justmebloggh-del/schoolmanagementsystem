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
    if (!el) return;
    el.textContent = text;
    el.classList.remove("error", "success");
    el.classList.add(isError ? "error" : "success");
  }

  function isAdminStaff(staff) {
    return String(staff && staff.role ? staff.role : "").toLowerCase().indexOf("admin") !== -1;
  }

  async function ensureAuth() {
    // Session lives in localStorage — check it first, no API needed
    const staffId  = localStorage.getItem('sms_current_staff');
    const schoolId = localStorage.getItem('sms_current_school');
    if (!staffId || !schoolId) {
      window.location.href = "school-home.html";
      return null;
    }

    // Fetch staff details for role check + name display.
    // If the API is temporarily unavailable, fall back to a stub so the
    // dashboard still loads rather than bouncing the user.
    const apiStaff = await SMSStore.getCurrentStaff();
    const staff = apiStaff || { id: staffId, name: 'Admin', role: 'Admin', department: 'Administration', status: 'active' };

    if (!isAdminStaff(staff)) {
      window.alert("Admin access only.");
      window.location.href = "school-home.html";
      return null;
    }

    return { school: { id: schoolId }, staff };
  }

  function switchTab(tab) {
    document.querySelectorAll(".tab-btn").forEach(function (b) {
      b.classList.toggle("active", b.dataset.tab === tab);
    });
    document.querySelectorAll(".tab-panel").forEach(function (p) {
      p.classList.toggle("active", p.id === "tab-" + tab);
    });
  }

  // ── 1. OVERVIEW ─────────────────────────────────────────────────────────────

  function renderOverview(data, metrics) {
    const stats = byId("dashboardStats");
    if (stats) {
      stats.innerHTML = [
        ["Total Students",       metrics.totalStudents,       "students"],
        ["Total Staff",          metrics.totalStaff,          "staff"],
        ["Pending Applications", metrics.pendingApplications, "applications"],
        ["Exam Results",         metrics.recordedResults,     "results"],
        ["Attendance Rate",      metrics.attendanceRate + "%","attendance"]
      ].map(function (row) {
        return (
          '<div class="stat-card" style="cursor:pointer" data-jump="' + row[2] + '">' +
          "<span>" + row[0] + "</span><strong>" + row[1] + "</strong></div>"
        );
      }).join("");

      stats.querySelectorAll(".stat-card[data-jump]").forEach(function (card) {
        card.addEventListener("click", function () { switchTab(card.dataset.jump); });
      });
    }

    const appList = byId("recentApplications");
    if (appList) {
      const recent = data.applications.slice(0, 5);
      appList.innerHTML = recent.length
        ? recent.map(function (a) {
            return "<li><strong>" + escapeHtml(a.fullName) + "</strong> — <span class=\"badge " +
              escapeHtml(a.status) + "\">" + escapeHtml(a.status) + "</span> (" + escapeHtml(a.submittedOn) + ")</li>";
          }).join("")
        : '<li class="empty">No applications.</li>';
    }

    const resList = byId("recentResults");
    if (resList) {
      const recent = data.examResults.slice(0, 5);
      resList.innerHTML = recent.length
        ? recent.map(function (r) {
            return "<li><strong>" + escapeHtml(r.studentName) + "</strong> — " +
              escapeHtml(r.subject) + ": " + escapeHtml(String(r.score)) + "% (" + escapeHtml(r.grade) + ")</li>";
          }).join("")
        : '<li class="empty">No results yet.</li>';
    }
  }

  // ── 2. STUDENTS ──────────────────────────────────────────────────────────────

  function renderStudents(data, searchValue) {
    const tbody = byId("studentsTableBody");
    if (!tbody) return;

    const query = (searchValue || "").trim().toLowerCase();
    const rows = data.students.filter(function (s) {
      if (!query) return true;
      return [s.id, s.name, s.program, s.email].join(" ").toLowerCase().indexOf(query) !== -1;
    });

    tbody.innerHTML = rows.length
      ? rows.map(function (s) {
          const isActive = s.status === "active";
          return (
            "<tr>" +
            "<td>" + escapeHtml(s.id) + "</td>" +
            "<td>" + escapeHtml(s.name) + "</td>" +
            "<td>" + escapeHtml(s.email) + "</td>" +
            "<td>" + escapeHtml(s.program) + "</td>" +
            "<td>" + escapeHtml(s.level) + "</td>" +
            "<td><span class=\"badge " + escapeHtml(s.status) + "\">" + escapeHtml(s.status) + "</span></td>" +
            "<td class=\"action-cell\">" +
              "<button class=\"btn btn-xs btn-secondary stu-profile\" data-id=\"" + escapeHtml(s.id) + "\" title=\"View full profile\">Profile</button> " +
              "<button class=\"btn btn-xs " + (isActive ? "btn-warning" : "btn-success") + " stu-toggle\" data-id=\"" + escapeHtml(s.id) + "\">" +
                (isActive ? "Suspend" : "Activate") +
              "</button> " +
              "<button class=\"btn btn-xs btn-secondary stu-reset\" data-id=\"" + escapeHtml(s.id) + "\" title=\"Reset to Student@123\">Reset PW</button>" +
            "</td>" +
            "</tr>"
          );
        }).join("")
      : '<tr><td colspan="7" class="empty">No students found.</td></tr>';

    // Populate student dropdown for admin course registration
    const regStuSel = byId("adminRegStudentId");
    if (regStuSel) {
      regStuSel.innerHTML = '<option value="">Select student...</option>' +
        data.students.map(function (s) {
          return '<option value="' + escapeHtml(s.id) + '">' + escapeHtml(s.id + " — " + s.name) + "</option>";
        }).join("");
    }
  }

  // ── 3. ADMISSIONS / APPLICATIONS ─────────────────────────────────────────────

  function renderApplications(data) {
    const grid = byId("applicationsGrid");
    if (!grid) return;

    if (!data.applications.length) {
      grid.innerHTML = '<p class="empty">No applications received yet.</p>';
      return;
    }

    grid.innerHTML = data.applications.map(function (app) {
      const actions = app.status === "pending"
        ? '<div class="action-row">' +
            '<button class="btn btn-primary app-action" data-action="approve" data-app-id="' + escapeHtml(app.id) + '">Approve → Create Student</button> ' +
            '<button class="btn btn-danger app-action" data-action="reject" data-app-id="' + escapeHtml(app.id) + '">Reject</button>' +
          '</div>'
        : app.status === "approved"
          ? '<p style="color:var(--sea-700);font-weight:600">✓ Approved — student account created</p>'
          : '<p style="color:var(--red-600,#c0392b);font-weight:600">✗ Rejected</p>';

      return (
        '<article class="app-card">' +
        "<h3>" + escapeHtml(app.fullName) + "</h3>" +
        '<p><span class="badge ' + escapeHtml(app.status) + '">' + escapeHtml(app.status) + "</span></p>" +
        "<p><strong>1st Choice:</strong> " + escapeHtml(app.programFirstChoice) + "</p>" +
        (app.programSecondChoice ? "<p><strong>2nd Choice:</strong> " + escapeHtml(app.programSecondChoice) + "</p>" : "") +
        "<p><strong>DOB:</strong> " + escapeHtml(app.dob) + "</p>" +
        "<p><strong>Email:</strong> " + escapeHtml(app.email) + "</p>" +
        "<p><strong>Phone:</strong> " + escapeHtml(app.phone) + "</p>" +
        "<p><strong>Address:</strong> " + escapeHtml(app.address) + "</p>" +
        (app.notes ? "<p><strong>Notes:</strong> " + escapeHtml(app.notes.substring(0, 120)) + (app.notes.length > 120 ? "…" : "") + "</p>" : "") +
        "<p><strong>Submitted:</strong> " + escapeHtml(app.submittedOn) + "</p>" +
        actions +
        "</article>"
      );
    }).join("");
  }

  // ── 4. ATTENDANCE ─────────────────────────────────────────────────────────────

  function renderAttendanceStudents(data) {
    const list = byId("attendanceStudentList");
    if (list) {
      if (!data.students.length) {
        list.innerHTML = '<p class="empty">No students enrolled yet.</p>';
      } else
      list.innerHTML = data.students.map(function (s) {
        return (
          '<label class="check-item">' +
          '<input type="checkbox" name="presentStudentIds" value="' + escapeHtml(s.id) + '">' +
          "<span><strong>" + escapeHtml(s.name) + "</strong><small>" +
          escapeHtml(s.id) + " | " + escapeHtml(s.program) + "</small></span></label>"
        );
      }).join("");
    }

    const hist = byId("attendanceHistory");
    if (hist) {
      if (!data.attendance || !data.attendance.length) {
        hist.innerHTML = '<p class="empty">No attendance records yet.</p>';
        return;
      }
      hist.innerHTML =
        '<table><thead><tr><th>Date</th><th>Course</th><th>Present</th><th>Absent</th><th>Rate</th></tr></thead><tbody>' +
        data.attendance.slice(0, 15).map(function (entry) {
          const course = data.courses.find(function (c) { return c.id === entry.courseId; });
          const present = entry.presentStudentIds ? entry.presentStudentIds.length : 0;
          const absent  = entry.absentStudentIds  ? entry.absentStudentIds.length  : 0;
          const total   = present + absent;
          const pct     = total ? Math.round((present / total) * 100) : 0;
          return (
            "<tr><td>" + escapeHtml(entry.date) + "</td>" +
            "<td>" + escapeHtml(course ? course.code + " — " + course.title : entry.courseId) + "</td>" +
            "<td>" + present + "</td><td>" + absent + "</td>" +
            "<td><strong>" + pct + "%</strong></td></tr>"
          );
        }).join("") +
        "</tbody></table>";
    }
  }

  // ── 5. COURSES ───────────────────────────────────────────────────────────────

  function renderCourses(data) {
    const grid = byId("coursesGrid");
    const select = byId("attendanceCourse");

    if (grid) {
      if (!data.courses.length) {
        grid.innerHTML = '<p class="empty">No courses added yet.</p>';
      } else
      grid.innerHTML = data.courses.map(function (course) {
        // Count enrolled students
        const enrolled = data.registrations
          ? data.registrations.filter(function (r) {
              return r.courseIds && r.courseIds.indexOf(course.id) !== -1;
            }).length
          : 0;

        return (
          '<article class="course-card">' +
          "<h3>" + escapeHtml(course.code) + " — " + escapeHtml(course.title) + "</h3>" +
          "<p><strong>Program:</strong> " + escapeHtml(course.program) + " | Level " + escapeHtml(course.level) + "</p>" +
          "<p><strong>Credits:</strong> " + course.credits + " | <strong>Seats:</strong> " + course.seats + "</p>" +
          (enrolled ? "<p><strong>Enrolled:</strong> " + enrolled + " student(s)</p>" : "") +
          '<p><span class="badge ' + (course.active ? "active" : "inactive") + '">' +
            (course.active ? "Active" : "Inactive") + "</span></p>" +
          '<button class="btn btn-secondary course-toggle" data-course-id="' + escapeHtml(course.id) + '">' +
            (course.active ? "Deactivate" : "Activate") + "</button>" +
          "</article>"
        );
      }).join("");

      // Populate admin course registration checkboxes
      const regCourseList = byId("adminRegCourseList");
      if (regCourseList) {
        const active = data.courses.filter(function (c) { return c.active; });
        regCourseList.innerHTML = active.length
          ? active.map(function (c) {
              return (
                '<label class="check-item">' +
                '<input type="checkbox" name="adminCourseIds" value="' + escapeHtml(c.id) + '">' +
                "<span><strong>" + escapeHtml(c.code) + "</strong> — " + escapeHtml(c.title) +
                "<small>" + escapeHtml(c.program) + " | Level " + escapeHtml(c.level) + " | " + c.credits + " cr</small></span></label>"
              );
            }).join("")
          : '<p class="empty">No active courses.</p>';
      }
    }

    if (select) {
      select.innerHTML =
        '<option value="">Select active course</option>' +
        data.courses.filter(function (c) { return c.active; }).map(function (c) {
          return '<option value="' + escapeHtml(c.id) + '">' + escapeHtml(c.code) + " — " + escapeHtml(c.title) + "</option>";
        }).join("");
    }
  }

  // ── CREDENTIAL BOX ───────────────────────────────────────────────────────────

  function showCredBox(boxId, id, password, type) {
    var box = byId(boxId);
    if (!box) return;
    var label = type === 'staff' ? 'Staff' : 'Student';
    var idLabel = type === 'staff' ? 'Staff ID' : 'Student ID';
    box.style.display = 'block';
    box.innerHTML =
      '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:1rem;margin-top:0.75rem">' +
      '<p style="font-weight:600;color:#15803d;margin:0 0 0.5rem"><i class="fa-solid fa-circle-check"></i> ' + label + ' login created successfully</p>' +
      '<table style="border:none;font-size:0.875rem"><tbody>' +
      '<tr><td style="padding:3px 12px 3px 0;color:#374151">' + idLabel + ':</td><td><code style="background:#dcfce7;padding:2px 6px;border-radius:4px;font-weight:600">' + escapeHtml(id) + '</code></td></tr>' +
      '<tr><td style="padding:3px 12px 3px 0;color:#374151">Password:</td><td><code style="background:#dcfce7;padding:2px 6px;border-radius:4px;font-weight:600">' + escapeHtml(password) + '</code></td></tr>' +
      '</tbody></table>' +
      '<p style="font-size:0.78rem;color:#6b7280;margin:0.5rem 0 0">Share these with the ' + label.toLowerCase() + '. They can update their password after logging in.</p>' +
      '</div>';
  }

  // ── 6. REGISTRATIONS ─────────────────────────────────────────────────────────

  function renderRegistrations(data, searchValue) {
    var tbody = byId('registrationsTableBody');
    if (!tbody) return;

    var studentMap = {};
    data.students.forEach(function (s) { studentMap[s.id] = s; });
    var courseMap = {};
    data.courses.forEach(function (c) { courseMap[c.id] = c; });

    var regs = data.registrations || [];
    var query = (searchValue || '').trim().toLowerCase();
    if (query) {
      regs = regs.filter(function (r) {
        var s = studentMap[r.studentId];
        return [r.studentId, s ? s.name : '', r.term].join(' ').toLowerCase().indexOf(query) !== -1;
      });
    }

    if (!regs.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="empty">No registrations found.</td></tr>';
      return;
    }

    tbody.innerHTML = regs.map(function (r) {
      var s = studentMap[r.studentId];
      var courseCodes = (r.courseIds || []).map(function (cid) {
        var c = courseMap[cid];
        return c ? c.code : cid;
      });
      return '<tr>' +
        '<td><strong>' + escapeHtml(s ? s.name : r.studentId) + '</strong>' +
          (s ? '<br><small style="color:#9ca3af">' + escapeHtml(r.studentId) + ' | ' + escapeHtml(s.program) + ' L' + escapeHtml(s.level) + '</small>' : '') +
        '</td>' +
        '<td>' + escapeHtml(r.term) + '</td>' +
        '<td style="font-size:0.82rem">' + escapeHtml(courseCodes.join(', ') || '—') + '</td>' +
        '<td style="white-space:nowrap">' + escapeHtml(r.registeredOn) + '</td>' +
        '</tr>';
    }).join('');
  }

  // ── 7. STAFF ─────────────────────────────────────────────────────────────────

  function renderStaff(data) {
    const tbody = byId("staffTableBody");
    if (tbody) {
      tbody.innerHTML = data.staff.length
        ? data.staff.map(function (s) {
            const isActive = s.status === "active";
            return (
              "<tr>" +
              "<td>" + escapeHtml(s.id) + "</td>" +
              "<td>" + escapeHtml(s.name) + "</td>" +
              "<td>" + escapeHtml(s.email) + "</td>" +
              "<td>" + escapeHtml(s.role) + "</td>" +
              "<td>" + escapeHtml(s.department) + "</td>" +
              "<td><span class=\"badge " + escapeHtml(s.status) + "\">" + escapeHtml(s.status) + "</span></td>" +
              "<td class=\"action-cell\">" +
                "<button class=\"btn btn-xs " + (isActive ? "btn-warning" : "btn-success") + " staff-toggle\" data-id=\"" + escapeHtml(s.id) + "\">" +
                  (isActive ? "Suspend" : "Activate") +
                "</button> " +
                "<button class=\"btn btn-xs btn-secondary staff-reset\" data-id=\"" + escapeHtml(s.id) + "\" title=\"Reset to Staff@123\">Reset PW</button>" +
              "</td>" +
              "</tr>"
            );
          }).join("")
        : '<tr><td colspan="7" class="empty">No staff records found.</td></tr>';
    }

    const resultSelect = byId("resultStudentId");
    if (resultSelect) {
      resultSelect.innerHTML =
        '<option value="">Select student</option>' +
        data.students.map(function (s) {
          return '<option value="' + escapeHtml(s.id) + '">' + escapeHtml(s.id + " — " + s.name) + "</option>";
        }).join("");
    }
  }

  // ── 7. EXAM RESULTS ──────────────────────────────────────────────────────────

  function renderExamResults(data) {
    const tbody = byId("examResultsBody");
    if (!tbody) return;

    tbody.innerHTML = data.examResults.length
      ? data.examResults.map(function (r) {
          return (
            "<tr>" +
            "<td>" + escapeHtml(r.recordedOn) + "</td>" +
            "<td>" + escapeHtml(r.studentName) + "</td>" +
            "<td>" + escapeHtml(r.term) + "</td>" +
            "<td>" + escapeHtml(r.subject) + "</td>" +
            "<td>" + escapeHtml(String(r.score)) + "</td>" +
            "<td><strong>" + escapeHtml(r.grade) + "</strong></td>" +
            "<td>" + escapeHtml(r.recordedByName || r.recordedBy || "—") + "</td>" +
            "<td class=\"action-cell\">" +
              "<button class=\"btn btn-xs btn-danger result-delete\" data-id=\"" + escapeHtml(r.id) + "\">Delete</button>" +
            "</td>" +
            "</tr>"
          );
        }).join("")
      : '<tr><td colspan="8" class="empty">No exam results recorded yet.</td></tr>';
  }

  // ── 8. JOB APPLICATIONS ──────────────────────────────────────────────────────

  async function renderJobApplications() {
    const grid = byId("jobApplicationsGrid");
    if (!grid) return;

    try {
      const headers = { "Content-Type": "application/json" };
      const schoolId = localStorage.getItem("sms_current_school");
      if (schoolId) headers["X-School-ID"] = schoolId;

      const response = await fetch("/api/job-applications/list", { method: "GET", headers });
      const result = await response.json();

      if (!result.ok || !result.jobApplications || !result.jobApplications.length) {
        grid.innerHTML = '<p class="empty">No job applications received yet.</p>';
        return;
      }

      grid.innerHTML = result.jobApplications.map(function (app) {
        const isPending = app.status === "pending";
        const actions = isPending
          ? '<div class="action-row">' +
              '<button class="btn btn-primary job-action" data-action="shortlist" data-job-id="' + escapeHtml(app.id) + '">Shortlist</button> ' +
              '<button class="btn btn-danger job-action" data-action="reject" data-job-id="' + escapeHtml(app.id) + '">Reject</button>' +
            '</div>'
          : app.status === "shortlisted"
            ? '<p style="color:var(--sea-700);font-weight:600">★ Shortlisted</p>'
            : '<p style="color:var(--red-600,#c0392b);font-weight:600">✗ Rejected</p>';

        return (
          '<article class="app-card">' +
          "<h3>" + escapeHtml(app.fullName) + "</h3>" +
          '<p><span class="badge ' + escapeHtml(app.status) + '">' + escapeHtml(app.status) + "</span></p>" +
          "<p><strong>Position:</strong> " + escapeHtml(app.position) + "</p>" +
          "<p><strong>Department:</strong> " + escapeHtml(app.department) + "</p>" +
          "<p><strong>Qualification:</strong> " + escapeHtml(app.qualification) + "</p>" +
          "<p><strong>Experience:</strong> " + app.experience + " yrs</p>" +
          "<p><strong>Email:</strong> " + escapeHtml(app.email) + "</p>" +
          "<p><strong>Phone:</strong> " + escapeHtml(app.phone) + "</p>" +
          (app.cvFileName ? "<p><strong>CV:</strong> " + escapeHtml(app.cvFileName) + "</p>" : "") +
          (app.notes ? "<p><strong>Notes:</strong> " + escapeHtml(app.notes.substring(0, 120)) + (app.notes.length > 120 ? "…" : "") + "</p>" : "") +
          "<p><strong>Submitted:</strong> " + escapeHtml(app.submittedOn) + "</p>" +
          actions +
          "</article>"
        );
      }).join("");
    } catch (e) {
      grid.innerHTML = '<p class="empty">Could not load job applications.</p>';
    }
  }

  // ── 9. REPORTS ───────────────────────────────────────────────────────────────

  function renderReport(data, type) {
    const output = byId("reportOutput");
    if (!output) return;

    if (type === "students") {
      const byProgram = {};
      data.students.forEach(function (s) {
        byProgram[s.program] = (byProgram[s.program] || 0) + 1;
      });
      const total = data.students.length;
      output.innerHTML =
        "<h3>Student Summary — " + total + " total</h3>" +
        Object.keys(byProgram).map(function (p) {
          const pct = Math.round((byProgram[p] / total) * 100);
          return "<p><strong>" + escapeHtml(p) + ":</strong> " + byProgram[p] + " students (" + pct + "%)</p>";
        }).join("");
      return;
    }

    if (type === "attendance") {
      if (!data.attendance.length) {
        output.innerHTML = '<p class="empty">No attendance records available.</p>';
        return;
      }
      output.innerHTML =
        "<h3>Attendance Summary (last 15 sessions)</h3>" +
        data.attendance.slice(0, 15).map(function (entry) {
          const course = data.courses.find(function (c) { return c.id === entry.courseId; });
          const present = entry.presentStudentIds ? entry.presentStudentIds.length : 0;
          const absent  = entry.absentStudentIds  ? entry.absentStudentIds.length  : 0;
          const total   = present + absent;
          const pct     = total ? Math.round((present / total) * 100) : 0;
          return "<p><strong>" + escapeHtml(entry.date) + "</strong> — " +
            escapeHtml(course ? course.code : entry.courseId) +
            ": " + pct + "% present (" + present + "/" + total + ")</p>";
        }).join("");
      return;
    }

    if (type === "results") {
      if (!data.examResults.length) {
        output.innerHTML = '<p class="empty">No exam results available.</p>';
        return;
      }
      const avg = Math.round(
        data.examResults.reduce(function (s, r) { return s + Number(r.score || 0); }, 0) / data.examResults.length
      );
      const gradeMap = {};
      data.examResults.forEach(function (r) {
        gradeMap[r.grade] = (gradeMap[r.grade] || 0) + 1;
      });
      output.innerHTML =
        "<h3>Exam Results Summary</h3>" +
        "<p><strong>Total records:</strong> " + data.examResults.length + "</p>" +
        "<p><strong>Average score:</strong> " + avg + "%</p>" +
        "<p><strong>Grade breakdown:</strong> " +
        Object.keys(gradeMap).sort().map(function (g) { return g + ": " + gradeMap[g]; }).join(", ") + "</p>";
      return;
    }

    if (type === "applications") {
      const summary = { pending: 0, approved: 0, rejected: 0 };
      data.applications.forEach(function (a) { summary[a.status] = (summary[a.status] || 0) + 1; });
      output.innerHTML =
        "<h3>Admissions Summary</h3>" +
        "<p><strong>Pending:</strong> " + summary.pending + "</p>" +
        "<p><strong>Approved:</strong> " + summary.approved + "</p>" +
        "<p><strong>Rejected:</strong> " + summary.rejected + "</p>";
      return;
    }

    if (type === "performance") {
      if (!data.examResults.length || !data.students.length) {
        output.innerHTML = '<p class="empty">No data available for performance report.</p>';
        return;
      }
      const studentMap = {};
      data.students.forEach(function (s) { studentMap[s.id] = s.name; });
      const byStudent = {};
      data.examResults.forEach(function (r) {
        if (!byStudent[r.studentId]) byStudent[r.studentId] = { name: studentMap[r.studentId] || r.studentId, scores: [] };
        byStudent[r.studentId].scores.push(r.score);
      });
      const rows = Object.values(byStudent).map(function (s) {
        const avg = Math.round(s.scores.reduce(function (a, b) { return a + b; }, 0) / s.scores.length);
        return { name: s.name, count: s.scores.length, avg };
      }).sort(function (a, b) { return b.avg - a.avg; });

      output.innerHTML =
        "<h3>Student Performance Report</h3>" +
        "<table><thead><tr><th>Student</th><th>Subjects</th><th>Avg Score</th></tr></thead><tbody>" +
        rows.map(function (r) {
          return "<tr><td>" + escapeHtml(r.name) + "</td><td>" + r.count + "</td><td><strong>" + r.avg + "%</strong></td></tr>";
        }).join("") +
        "</tbody></table>";
    }
  }

  // ── STUDENT PROFILE MODAL ────────────────────────────────────────────────────

  async function showStudentProfile(studentId) {
    const modal = byId("studentProfileModal");
    const body  = byId("profileModalBody");
    if (!modal || !body) return;

    body.innerHTML = '<p class="empty">Loading profile…</p>';
    modal.style.display = "flex";

    const result = await SMSStore.getStudentProfile(studentId);
    if (!result.ok) {
      body.innerHTML = '<p class="empty">Could not load profile.</p>';
      return;
    }

    const s = result.student;
    const attPct = result.attendanceSummary.total
      ? Math.round((result.attendanceSummary.present / result.attendanceSummary.total) * 100)
      : 0;

    body.innerHTML =
      "<div class=\"profile-header\">" +
        "<h3>" + escapeHtml(s.name) + "</h3>" +
        "<p><strong>ID:</strong> " + escapeHtml(s.id) +
        " | <strong>Program:</strong> " + escapeHtml(s.program) +
        " | <strong>Level:</strong> " + escapeHtml(s.level) +
        " | <strong>Status:</strong> <span class=\"badge " + escapeHtml(s.status) + "\">" + escapeHtml(s.status) + "</span></p>" +
        (s.email ? "<p><strong>Email:</strong> " + escapeHtml(s.email) + "</p>" : "") +
      "</div>" +

      "<h4>Enrolled Courses (" + result.courses.length + ")</h4>" +
      (result.courses.length
        ? "<table><thead><tr><th>Code</th><th>Title</th><th>Credits</th><th>Term</th></tr></thead><tbody>" +
          result.courses.map(function (c) {
            return "<tr><td>" + escapeHtml(c.code) + "</td><td>" + escapeHtml(c.title) + "</td><td>" + c.credits + "</td><td>" + escapeHtml(c.term) + "</td></tr>";
          }).join("") + "</tbody></table>"
        : '<p class="empty">No courses registered yet.</p>') +

      "<h4>Attendance — " + attPct + "% (" + result.attendanceSummary.present + "/" + result.attendanceSummary.total + " sessions)</h4>" +
      (result.attendance.length
        ? "<table><thead><tr><th>Date</th><th>Course</th><th>Status</th></tr></thead><tbody>" +
          result.attendance.map(function (a) {
            return "<tr><td>" + escapeHtml(a.date) + "</td><td>" + escapeHtml(a.code) + "</td>" +
              "<td><span class=\"badge " + escapeHtml(a.status) + "\">" + escapeHtml(a.status) + "</span></td></tr>";
          }).join("") + "</tbody></table>"
        : '<p class="empty">No attendance records yet.</p>') +

      "<h4>Exam Results — Avg: " + result.averageScore + "%</h4>" +
      (result.results.length
        ? "<table><thead><tr><th>Date</th><th>Term</th><th>Subject</th><th>Score</th><th>Grade</th></tr></thead><tbody>" +
          result.results.map(function (r) {
            return "<tr><td>" + escapeHtml(r.recordedOn) + "</td><td>" + escapeHtml(r.term) + "</td><td>" + escapeHtml(r.subject) +
              "</td><td>" + r.score + "</td><td><strong>" + escapeHtml(r.grade) + "</strong></td></tr>";
          }).join("") + "</tbody></table>"
        : '<p class="empty">No results recorded yet.</p>');
  }

  // ── DASHBOARD REFRESH ────────────────────────────────────────────────────────

  function buildMetrics(data) {
    var att = data.attendance || [];
    var rate = 0;
    if (att.length) {
      var latest  = att[0];
      var present = (latest.presentStudentIds || []).length;
      var absent  = (latest.absentStudentIds  || []).length;
      var total   = present + absent;
      rate = total ? Math.round((present / total) * 100) : 0;
    }
    return {
      totalStudents:       (data.students     || []).length,
      totalStaff:          (data.staff        || []).length,
      pendingApplications: (data.applications || []).filter(function (a) { return a.status === 'pending'; }).length,
      recordedResults:     (data.examResults  || []).length,
      attendanceRate:      rate
    };
  }

  async function refreshDashboard(searchValue) {
    const data    = await SMSStore.getData();   // single API call
    const metrics = buildMetrics(data);
    renderOverview(data, metrics);
    renderStudents(data, searchValue || "");
    renderApplications(data);
    renderCourses(data);
    renderAttendanceStudents(data);
    renderStaff(data);
    renderRegistrations(data, "");
    renderExamResults(data);
    return data;
  }

  // ── EVENT BINDINGS ───────────────────────────────────────────────────────────

  function bindEvents(context) {
    const staff = context.staff;

    // Tab switching
    document.querySelectorAll(".tab-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        switchTab(btn.dataset.tab);
        if (btn.dataset.tab === "job-applications") renderJobApplications();
      });
    });

    // Student search
    const search = byId("studentSearch");
    if (search) {
      search.addEventListener("input", async function () {
        const data = await SMSStore.getData();
        renderStudents(data, search.value);
      });
    }

    // Students table: profile / toggle / reset
    const studentsTable = byId("studentsTableBody");
    if (studentsTable) {
      studentsTable.addEventListener("click", async function (e) {
        const profileBtn = e.target.closest(".stu-profile");
        if (profileBtn) { showStudentProfile(profileBtn.dataset.id); return; }

        const toggleBtn = e.target.closest(".stu-toggle");
        if (toggleBtn) {
          const result = await SMSStore.toggleStudent(toggleBtn.dataset.id);
          if (!result.ok) { window.alert(result.message); return; }
          await refreshDashboard(search ? search.value : "");
          return;
        }

        const resetBtn = e.target.closest(".stu-reset");
        if (resetBtn) {
          if (!window.confirm("Reset this student's password to Student@123?")) return;
          const result = await SMSStore.resetStudentPassword(resetBtn.dataset.id);
          window.alert(result.message);
          return;
        }
      });
    }

    // Profile modal close
    const modalClose = byId("profileModalClose");
    if (modalClose) {
      modalClose.addEventListener("click", function () {
        const modal = byId("studentProfileModal");
        if (modal) modal.style.display = "none";
      });
    }
    const modal = byId("studentProfileModal");
    if (modal) {
      modal.addEventListener("click", function (e) {
        if (e.target === modal) modal.style.display = "none";
      });
    }

    // Admissions approve / reject
    const appGrid = byId("applicationsGrid");
    if (appGrid) {
      appGrid.addEventListener("click", async function (e) {
        const btn = e.target.closest(".app-action");
        if (!btn) return;
        const appId  = btn.dataset.appId;
        const action = btn.dataset.action;
        const result = action === "approve"
          ? await SMSStore.approveApplication(appId, staff.id)
          : await SMSStore.rejectApplication(appId);
        if (!result.ok) { window.alert(result.message); return; }
        if (action === "approve" && result.studentId) {
          window.alert("Student account created!\nID: " + result.studentId + "\nPassword: " + (result.defaultPassword || "Student@123"));
        }
        await refreshDashboard(search ? search.value : "");
      });
    }

    // Courses: add + toggle
    const courseForm = byId("courseForm");
    if (courseForm) {
      courseForm.addEventListener("submit", async function (e) {
        e.preventDefault();
        const fd = new FormData(courseForm);
        const result = await SMSStore.addCourse({
          code:    String(fd.get("code")    || "").trim(),
          title:   String(fd.get("title")   || "").trim(),
          program: String(fd.get("program") || "").trim(),
          level:   String(fd.get("level")   || "").trim(),
          credits: Number(fd.get("credits") || 3),
          seats:   Number(fd.get("seats")   || 30)
        }, staff.name);
        if (!result.ok) { setMessage("courseMessage", result.message, true); return; }
        courseForm.reset();
        setMessage("courseMessage", result.message, false);
        await refreshDashboard(search ? search.value : "");
      });
    }

    const coursesGrid = byId("coursesGrid");
    if (coursesGrid) {
      coursesGrid.addEventListener("click", async function (e) {
        const btn = e.target.closest(".course-toggle");
        if (!btn) return;
        const result = await SMSStore.toggleCourseActive(btn.dataset.courseId);
        if (!result.ok) { window.alert(result.message); return; }
        await refreshDashboard(search ? search.value : "");
      });
    }

    // Attendance: record
    const attendanceForm = byId("attendanceForm");
    if (attendanceForm) {
      attendanceForm.addEventListener("submit", async function (e) {
        e.preventDefault();
        const fd = new FormData(attendanceForm);
        const presentIds = Array.from(attendanceForm.querySelectorAll('input[name="presentStudentIds"]:checked'))
          .map(function (cb) { return cb.value; });
        const result = await SMSStore.saveAttendance({
          date:     String(fd.get("date")     || ""),
          courseId: String(fd.get("courseId") || ""),
          presentStudentIds: presentIds
        }, staff.id);
        if (!result.ok) { setMessage("attendanceMessage", result.message, true); return; }
        setMessage("attendanceMessage", result.message, false);
        await refreshDashboard(search ? search.value : "");
      });
    }

    // Staff: add + toggle status
    const staffForm = byId("staffForm");
    if (staffForm) {
      staffForm.addEventListener("submit", async function (e) {
        e.preventDefault();
        const fd = new FormData(staffForm);
        const result = await SMSStore.addStaff({
          name:       String(fd.get("name")       || "").trim(),
          email:      String(fd.get("email")      || "").trim(),
          role:       String(fd.get("role")       || "").trim(),
          department: String(fd.get("department") || "").trim(),
          password:   String(fd.get("password")   || "").trim()
        });
        if (!result.ok) { setMessage("staffMessage", result.message, true); return; }
        staffForm.reset();
        setMessage("staffMessage", "", false);
        showCredBox("staffCredBox", result.staffId, result.defaultPassword, "staff");
        await refreshDashboard(search ? search.value : "");
      });
    }

    const staffTable = byId("staffTableBody");
    if (staffTable) {
      staffTable.addEventListener("click", async function (e) {
        const toggleBtn = e.target.closest(".staff-toggle");
        if (toggleBtn) {
          const result = await SMSStore.toggleStaff(toggleBtn.dataset.id);
          if (!result.ok) { window.alert(result.message); return; }
          await refreshDashboard(search ? search.value : "");
          return;
        }
        const resetBtn = e.target.closest(".staff-reset");
        if (resetBtn) {
          if (!window.confirm("Reset this staff member's password to Staff@123?")) return;
          const result = await SMSStore.resetStaffPassword(resetBtn.dataset.id);
          window.alert(result.message);
          return;
        }
      });
    }

    // Registration search
    const regSearch = byId("regSearch");
    if (regSearch) {
      regSearch.addEventListener("input", async function () {
        const data = await SMSStore.getData();
        renderRegistrations(data, regSearch.value);
      });
    }

    // Student creation
    const studentForm = byId("studentForm");
    if (studentForm) {
      studentForm.addEventListener("submit", async function (e) {
        e.preventDefault();
        const fd = new FormData(studentForm);
        const result = await SMSStore.addStudent({
          name:     String(fd.get("name")     || "").trim(),
          email:    String(fd.get("email")    || "").trim(),
          phone:    String(fd.get("phone")    || "").trim(),
          program:  String(fd.get("program")  || "").trim(),
          level:    String(fd.get("level")    || "").trim(),
          password: String(fd.get("password") || "").trim()
        });
        if (!result.ok) { setMessage("studentMessage", result.message, true); return; }
        studentForm.reset();
        setMessage("studentMessage", "", false);
        showCredBox("studentCredBox", result.studentId, result.defaultPassword, "student");
        await refreshDashboard(search ? search.value : "");
      });
    }

    // Admin course registration
    const adminRegForm = byId("adminRegForm");
    if (adminRegForm) {
      adminRegForm.addEventListener("submit", async function (e) {
        e.preventDefault();
        const fd = new FormData(adminRegForm);
        const courseIds = Array.from(adminRegForm.querySelectorAll('input[name="adminCourseIds"]:checked'))
          .map(function (cb) { return cb.value; });
        if (!courseIds.length) { setMessage("adminRegMessage", "Select at least one course.", true); return; }
        const result = await SMSStore.adminRegisterCourses({
          studentId: String(fd.get("studentId") || "").trim(),
          term:      String(fd.get("term")      || "").trim(),
          courseIds: courseIds
        });
        if (!result.ok) { setMessage("adminRegMessage", result.message, true); return; }
        adminRegForm.reset();
        setMessage("adminRegMessage", result.message, false);
        await refreshDashboard(search ? search.value : "");
      });
    }

    // Exam results: add + delete
    const examForm = byId("examResultForm");
    if (examForm) {
      examForm.addEventListener("submit", async function (e) {
        e.preventDefault();
        const fd = new FormData(examForm);
        const result = await SMSStore.addExamResult({
          studentId: String(fd.get("studentId") || "").trim(),
          term:      String(fd.get("term")      || "").trim(),
          subject:   String(fd.get("subject")   || "").trim(),
          score:     Number(fd.get("score")     || 0),
          grade:     String(fd.get("grade")     || "").trim().toUpperCase()
        }, staff.id);
        if (!result.ok) { setMessage("examResultMessage", result.message, true); return; }
        examForm.reset();
        setMessage("examResultMessage", result.message, false);
        await refreshDashboard(search ? search.value : "");
      });
    }

    const examBody = byId("examResultsBody");
    if (examBody) {
      examBody.addEventListener("click", async function (e) {
        const btn = e.target.closest(".result-delete");
        if (!btn) return;
        if (!window.confirm("Delete this exam result?")) return;
        const result = await SMSStore.deleteExamResult(btn.dataset.id);
        if (!result.ok) { window.alert(result.message); return; }
        await refreshDashboard(search ? search.value : "");
      });
    }

    // Job applications: shortlist / reject
    const jobGrid = byId("jobApplicationsGrid");
    if (jobGrid) {
      jobGrid.addEventListener("click", async function (e) {
        const btn = e.target.closest(".job-action");
        if (!btn) return;
        const jobId  = btn.dataset.jobId;
        const action = btn.dataset.action;
        const result = action === "shortlist"
          ? await SMSStore.shortlistJobApplication(jobId)
          : await SMSStore.rejectJobApplication(jobId);
        if (!result.ok) { window.alert(result.message); return; }
        await renderJobApplications();
      });
    }

    // Reports
    document.querySelectorAll("[data-report]").forEach(function (btn) {
      btn.addEventListener("click", async function () {
        const data = await SMSStore.getData();
        renderReport(data, btn.dataset.report);
      });
    });

    // Logout
    const logoutBtn = byId("logoutBtn");
    if (logoutBtn) {
      logoutBtn.addEventListener("click", function () {
        SMSStore.logoutStaff();
        window.location.href = "school-home.html";
      });
    }
  }

  async function init() {
    if (!["dashboard", "admin-dashboard"].includes(document.body.dataset.page || "")) return;

    const context = await ensureAuth();
    if (!context) return;

    // Show logged-in user immediately
    const userLabel = byId("dashboardUser");
    if (userLabel) userLabel.textContent = context.staff.name + " — " + context.staff.role;

    // Switch to the hash tab right away so the right section is visible before data loads
    const hashTab = (window.location.hash || "").replace("#", "");
    if (hashTab && document.getElementById("tab-" + hashTab)) {
      switchTab(hashTab);
    }

    // Set today's date on the attendance form
    const attendanceDate = document.querySelector('#attendanceForm input[name="date"]');
    if (attendanceDate) attendanceDate.value = new Date().toISOString().slice(0, 10);

    // Bind all event handlers NOW so tabs and forms are interactive immediately,
    // before the data API call completes.
    bindEvents(context);

    // Load and render all data (runs after UI is already interactive)
    await refreshDashboard("");

    // If the careers tab was opened via hash, load its data now that the API call is done
    if (hashTab === "job-applications") renderJobApplications();
  }

  document.addEventListener("DOMContentLoaded", function () { init(); });
})();
