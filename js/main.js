(function () {
  function byId(id) {
    return document.getElementById(id);
  }

  function showMessage(el, text, isError) {
    if (!el) {
      return;
    }
    el.textContent = text;
    el.classList.remove("error", "success");
    el.classList.add(isError ? "error" : "success");
  }

  function renderSelectedCourses(form, courses) {
    const list = byId("selectedCoursesList");
    const meta = byId("selectedCoursesMeta");
    if (!list || !meta) {
      return;
    }

    const selectedIds = Array.from(form.querySelectorAll('input[name="courseIds"]:checked')).map(function (item) {
      return item.value;
    });

    const selectedCourses = courses.filter(function (course) {
      return selectedIds.indexOf(course.id) !== -1;
    });

    const totalCredits = selectedCourses.reduce(function (sum, course) {
      return sum + Number(course.credits || 0);
    }, 0);

    meta.textContent =
      selectedCourses.length +
      " course" +
      (selectedCourses.length === 1 ? "" : "s") +
      " selected | " +
      totalCredits +
      " total credits";

    list.innerHTML = selectedCourses.length
      ? selectedCourses
          .map(function (course) {
            return (
              "<li><strong>" +
              course.code +
              "</strong> - " +
              course.title +
              " (" +
              course.credits +
              " credits)</li>"
            );
          })
          .join("")
      : '<li class="empty">No courses selected yet.</li>';
  }

  function setActiveNav(page) {
    const mapping = {
      home: "home",
      "school-auth": "school-auth",
      admissions: "admissions",
      registration: "registration",
      "student-login": "student-login",
      "teacher-login": "teacher-login",
      "admin-dashboard": "dashboard",
      dashboard: "dashboard"
    };

    const target = mapping[page];
    if (!target) {
      return;
    }

    document.querySelectorAll("[data-nav]").forEach(function (item) {
      item.classList.toggle("active", item.dataset.nav === target);
    });
  }

  function initNavigation() {
    const toggle = document.querySelector(".nav-toggle");
    const nav = document.querySelector(".site-nav");
    if (!toggle || !nav) {
      return;
    }

    toggle.addEventListener("click", function () {
      const open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(open));
    });
  }

  function initYear() {
    const year = new Date().getFullYear();
    document.querySelectorAll("#year").forEach(function (node) {
      node.textContent = String(year);
    });
  }

  function fillSchoolContext(school) {
    document.querySelectorAll("[data-school-name]").forEach(function (node) {
      node.textContent = school ? school.name : "No school selected";
    });
  }

  async function requireSchoolForPage(page) {
    const school = await SMSStore.getCurrentSchool();
    fillSchoolContext(school);
    return school;
  }

  async function initHomePage() {
    if (document.body.dataset.page !== "home") {
      return;
    }

    const school = await SMSStore.getCurrentSchool();

    if (school) {
      const schoolState = byId("homeSchoolState");
      if (schoolState) {
        schoolState.textContent = "Current school workspace: " + school.name;
      }

      const data = await SMSStore.getData();
      const metrics = await SMSStore.getOverviewMetrics();

      const list = byId("homeMetrics");
      if (list) {
        const rows = [
          ["Students", metrics.totalStudents],
          ["Staff", metrics.totalStaff],
          ["Pending Applications", metrics.pendingApplications],
          ["Exam Results", metrics.recordedResults]
        ];
        list.innerHTML = rows
          .map(function (entry) {
            return "<li><span>" + entry[0] + "</span><strong>" + entry[1] + "</strong></li>";
          })
          .join("");
      }

      const announcementList = byId("announcementList");
      if (announcementList) {
        announcementList.innerHTML = data.announcements
          .slice(0, 5)
          .map(function (item) {
            return "<li><strong>" + item.createdAt + "</strong> - " + item.title + "</li>";
          })
          .join("");
      }

      const latest = byId("latestAnnouncement");
      if (latest && data.announcements[0]) {
        latest.textContent = data.announcements[0].title;
      }
    } else {
      const schoolState = byId("homeSchoolState");
      if (schoolState) {
        schoolState.textContent = "Choose or create your school account to start managing records.";
      }

      const list = byId("homeMetrics");
      if (list) {
        list.innerHTML = [
          ["Students", 0],
          ["Staff", 0],
          ["Pending Applications", 0],
          ["Exam Results", 0]
        ]
          .map(function (entry) {
            return "<li><span>" + entry[0] + "</span><strong>" + entry[1] + "</strong></li>";
          })
          .join("");
      }

      const announcementList = byId("announcementList");
      if (announcementList) {
        announcementList.innerHTML = '<li class="empty">Sign in to a school to load announcements.</li>';
      }

      const latest = byId("latestAnnouncement");
      if (latest) {
        latest.textContent = "No school selected";
      }
    }

    const todayDate = byId("todayDate");
    if (todayDate) {
      todayDate.textContent = new Date().toLocaleDateString(undefined, {
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric"
      });
    }
  }

  function initSchoolAuth() {
    if (document.body.dataset.page !== "school-auth") {
      return;
    }

    const createForm = byId("createSchoolForm");
    const createMessage = byId("createSchoolMessage");
    const loginForm = byId("schoolLoginForm");
    const loginMessage = byId("schoolLoginMessage");

    if (createForm) {
      createForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        const formData = new FormData(createForm);

        const payload = {
          schoolName: String(formData.get("schoolName") || "").trim(),
          schoolEmail: String(formData.get("schoolEmail") || "").trim(),
          schoolPhone: String(formData.get("schoolPhone") || "").trim(),
          schoolAddress: String(formData.get("schoolAddress") || "").trim(),
          password: String(formData.get("password") || "").trim(),
          adminName: String(formData.get("adminName") || "").trim(),
          adminEmail: String(formData.get("adminEmail") || "").trim(),
          adminPassword: String(formData.get("adminPassword") || "").trim()
        };

        const result = await SMSStore.createSchoolAccount(payload);
        if (!result.ok) {
          showMessage(createMessage, result.message, true);
          return;
        }

        const note =
          "School account created. Staff login: " +
          result.defaultStaff.email +
          " / " +
          result.defaultStaff.password;
        showMessage(createMessage, note, false);

        setTimeout(function () {
          window.location.href = "teacher-login.html";
        }, 700);
      });
    }

    if (loginForm) {
      loginForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        const formData = new FormData(loginForm);

        const result = await SMSStore.loginSchool(
          String(formData.get("email") || "").trim(),
          String(formData.get("password") || "")
        );

        if (!result.ok) {
          showMessage(loginMessage, result.message, true);
          return;
        }

        showMessage(loginMessage, "School selected. Continue with staff login.", false);
        setTimeout(function () {
          window.location.href = "teacher-login.html";
        }, 600);
      });
    }

    const logoutButton = byId("schoolLogoutBtn");
    if (logoutButton) {
      logoutButton.addEventListener("click", function () {
        SMSStore.logoutSchool();
        showMessage(loginMessage || createMessage, "School workspace cleared.", false);
      });
    }
  }

  function initAdmissionsForm() {
    const form = byId("admissionsForm");
    if (!form) {
      return;
    }

    const message = byId("admissionMessage");

    form.addEventListener("submit", async function (event) {
      event.preventDefault();

      const formData = new FormData(form);
      const payload = {
        fullName: String(formData.get("fullName") || "").trim(),
        dob: String(formData.get("dob") || ""),
        email: String(formData.get("email") || "").trim(),
        phone: String(formData.get("phone") || "").trim(),
        address: String(formData.get("address") || "").trim(),
        programFirstChoice: String(formData.get("programFirstChoice") || ""),
        programSecondChoice: String(formData.get("programSecondChoice") || ""),
        notes: String(formData.get("notes") || "")
      };

      if (!formData.get("terms")) {
        showMessage(message, "You must confirm accuracy before submitting.", true);
        return;
      }

      const result = await SMSStore.submitApplication(payload);
      if (!result.ok) {
        showMessage(message, result.message, true);
        return;
      }

      form.reset();
      showMessage(message, "Application submitted successfully. Reference: " + result.applicationId, false);
    });
  }

  function initStudentLogin() {
    const form = byId("studentLoginForm");
    if (!form) {
      return;
    }

    const message = byId("studentLoginMessage");
    form.addEventListener("submit", async function (event) {
      event.preventDefault();
      const formData = new FormData(form);

      const result = await SMSStore.loginStudent(
        String(formData.get("identifier") || ""),
        String(formData.get("password") || "")
      );

      if (!result.ok) {
        showMessage(message, result.message, true);
        return;
      }

      showMessage(message, "Login successful. Redirecting to registration...", false);
      setTimeout(function () {
        window.location.href = "course-registration.html";
      }, 600);
    });
  }

  function initTeacherLogin() {
    const form = byId("teacherLoginForm");
    if (!form) {
      return;
    }

    const message = byId("teacherLoginMessage");
    form.addEventListener("submit", async function (event) {
      event.preventDefault();
      const formData = new FormData(form);

      const result = await SMSStore.loginStaff(
        String(formData.get("identifier") || ""),
        String(formData.get("password") || "")
      );

      if (!result.ok) {
        showMessage(message, result.message, true);
        return;
      }

      showMessage(message, "Staff login successful. Opening dashboard...", false);
      setTimeout(function () {
        window.location.href = "admin-dashboard.html";
      }, 600);
    });
  }

  async function renderCourseChecklist() {
    const container = byId("courseChecklist");
    if (!container) {
      return;
    }

    const data = await SMSStore.getData();
    const activeCourses = data.courses.filter(function (course) {
      return course.active;
    });

    container.innerHTML = activeCourses.length
      ? activeCourses
          .map(function (course) {
            return (
              '<label class="check-item">' +
              '<input type="checkbox" name="courseIds" value="' +
              course.id +
              '">' +
              "<span><strong>" +
              course.code +
              "</strong> - " +
              course.title +
              "<small>" +
              course.program +
              " | Level " +
              course.level +
              " | " +
              course.credits +
              " credits</small></span></label>"
            );
          })
          .join("")
      : '<p class="empty">No active courses yet.</p>';

    return activeCourses;
  }

  async function initCourseRegistration() {
    const form = byId("courseRegistrationForm");
    if (!form) {
      return;
    }

    const activeCourses = await renderCourseChecklist();
    const message = byId("registrationMessage");

    const student = await SMSStore.getCurrentStudent();
    if (student) {
      form.elements.studentIdentifier.value = student.id;
    }

    form.addEventListener("change", function (event) {
      if (event.target && event.target.name === "courseIds") {
        renderSelectedCourses(form, activeCourses || []);
      }
    });

    renderSelectedCourses(form, activeCourses || []);

    form.addEventListener("submit", async function (event) {
      event.preventDefault();
      const formData = new FormData(form);
      const selected = Array.from(form.querySelectorAll('input[name="courseIds"]:checked')).map(function (item) {
        return item.value;
      });

      const result = await SMSStore.registerCourses({
        studentIdentifier: String(formData.get("studentIdentifier") || "").trim(),
        password: String(formData.get("password") || "").trim(),
        term: String(formData.get("term") || ""),
        courseIds: selected
      });

      if (!result.ok) {
        showMessage(message, result.message, true);
        return;
      }

      showMessage(message, result.message, false);
      form.elements.password.value = "";
      form.querySelectorAll('input[name="courseIds"]').forEach(function (checkbox) {
        checkbox.checked = false;
      });
      renderSelectedCourses(form, activeCourses || []);
    });
  }

  async function init() {
    const page = document.body.dataset.page || "";

    initNavigation();
    initYear();
    setActiveNav(page);

    await requireSchoolForPage(page);

    await initHomePage();
    initSchoolAuth();
    initAdmissionsForm();
    initStudentLogin();
    initTeacherLogin();
    await initCourseRegistration();
  }

  document.addEventListener("DOMContentLoaded", function () {
    init();
  });
})();
