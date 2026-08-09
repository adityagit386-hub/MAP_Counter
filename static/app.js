const state = {
  token: localStorage.getItem("certimapToken") || "",
  user: null,
  data: null,
  activeTab: "overview",
  previewUrls: [],
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));
const canReview = () => state.user && ["faculty", "admin"].includes(state.user.role);

function authHeaders() {
  return state.token ? { Authorization: `Bearer ${state.token}` } : {};
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}), ...authHeaders() };
  const response = await fetch(path, { ...options, headers });
  const type = response.headers.get("content-type") || "";
  const payload = type.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) throw new Error(payload.error || payload.message || payload || "Request failed");
  return payload;
}

function visibleTabsForRole(role) {
  if (role === "student") return ["overview", "upload", "gallery", "reports", "profile", "settings"];
  if (role === "admin") return ["overview", "approvals", "students", "rules", "reports", "profile", "settings"];
  return ["overview", "approvals", "students", "reports", "profile", "settings"];
}

function setPanel(tab) {
  const allowed = visibleTabsForRole(state.user?.role || "student");
  const next = allowed.includes(tab) ? tab : allowed[0];
  state.activeTab = next;
  $$(".tabs button").forEach((button) => {
    const visible = allowed.includes(button.dataset.tab);
    button.style.display = visible ? "" : "none";
    button.classList.toggle("active", button.dataset.tab === next);
  });
  $$(".tab-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `${next}Panel`);
  });
  $("#pageTitle").textContent = next[0].toUpperCase() + next.slice(1);
}

async function authenticate(path, form) {
  try {
    const payload = await api(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Object.fromEntries(form)),
    });
    state.token = payload.token;
    localStorage.setItem("certimapToken", state.token);
    await bootstrap();
  } catch (error) {
    alert(error.message);
  }
}

async function bootstrap() {
  if (!state.token) return;
  try {
    state.data = await api("/api/bootstrap");
    state.user = state.data.user;
    applyTheme(state.user.theme || localStorage.getItem("certimapTheme") || "system");
    $("#authScreen").classList.add("hidden");
    $("#shell").classList.remove("hidden");
    $("#roleLabel").textContent = `${state.user.role} dashboard`;
    $("#csvLink").href = `/api/report.csv?token=${encodeURIComponent(state.token)}`;
    renderAll();
    setPanel(state.activeTab);
  } catch (error) {
    localStorage.removeItem("certimapToken");
    state.token = "";
  }
}

function renderAll() {
  populateUploadProfile();
  populateProfileForm();
  populateSettingsForm();
  renderTopbarProfile();
  renderMetrics();
  renderWaitingBanner();
  renderCharts();
  renderRows();
  renderGallery();
  renderApprovals();
  renderStudents();
  renderRules();
  renderOverviewSide();
  renderNotifications();
}

function renderMetrics() {
  const stats = state.data.stats;
  const items = state.user.role === "student"
    ? [
        ["Calculated MAP points", stats.calculatedPoints],
        ["Approved points", stats.approvedPoints],
        ["Waiting for approve", stats.pending],
        ["Certificates", stats.totalCertificates],
      ]
    : [
        ["Pending approvals", stats.pending],
        ["Certificates", stats.totalCertificates],
        ["Students", state.data.students.length],
        ["Calculated points", stats.calculatedPoints],
      ];
  $("#metrics").innerHTML = items.map(([label, value]) => `
    <article class="metric"><span>${label}</span><strong>${value}</strong></article>
  `).join("");
}

function renderWaitingBanner() {
  const pending = state.data.certificates.filter((row) => row.status === "pending");
  const banner = $("#waitingBanner");
  if (state.user.role !== "student" || pending.length === 0) {
    banner.classList.add("hidden");
    banner.innerHTML = "";
    return;
  }
  banner.classList.remove("hidden");
  banner.innerHTML = `
    <strong>Points calculated automatically</strong>
    <span>${pending.length} certificate${pending.length === 1 ? "" : "s"} waiting for faculty approval. Points are visible now and become final after approval.</span>
  `;
}

function renderOverviewSide() {
  const title = $("#overviewSideTitle");
  const content = $("#overviewSideContent");
  if (state.user.role === "student") {
    const profile = state.data.studentProfile || {};
    title.textContent = "Student Profile";
    content.innerHTML = `
      <div class="profile-mini">
        ${avatarMarkup(profile.name || state.user.name, state.user.profile_photo)}
        <div><strong>${escapeHtml(profile.name || state.user.name)}</strong><span>${escapeHtml(profile.roll_number || "")}</span></div>
      </div>
      <p>${escapeHtml(profile.department || "Department not set")}</p>
      <p class="muted">${escapeHtml(profile.semester || "")} ${escapeHtml(profile.academic_year || "")}</p>
      <button type="button" onclick="document.querySelector('[data-tab=profile]').click()">Edit profile</button>
    `;
  } else {
    title.textContent = "Admin Tools";
    content.innerHTML = `
      <p>Review pending certificates, assign manual MAP points, or recalculate automatically from MAP rules.</p>
      <div class="actions">
        <button type="button" onclick="document.querySelector('[data-tab=approvals]').click()">Open approvals</button>
        <button class="subtle" type="button" onclick="document.querySelector('[data-tab=students]').click()">View students</button>
      </div>
    `;
  }
}

function renderCharts() {
  drawBars("#categoryChart", state.data.charts.byCategory, "No category points yet");
  drawBars("#departmentChart", state.data.charts.byDepartment, "No department data yet");
  drawBars("#monthChart", state.data.charts.byMonth, "No monthly uploads yet");
}

function drawBars(selector, values, emptyText) {
  const entries = Object.entries(values || {});
  const max = Math.max(...entries.map(([, value]) => Number(value)), 1);
  $(selector).innerHTML = entries.length
    ? entries.map(([label, value]) => `
      <div class="bar-row">
        <span>${escapeHtml(label)}</span>
        <div class="bar-track"><div class="bar-fill" style="width:${(Number(value) / max) * 100}%"></div></div>
        <strong>${value}</strong>
      </div>
    `).join("")
    : `<p class="muted">${emptyText}</p>`;
}

function renderRows() {
  const query = ($("#searchInput").value || "").toLowerCase();
  const rows = state.data.certificates.filter((row) => JSON.stringify(row).toLowerCase().includes(query)).slice(0, 12);
  $("#recentRows").innerHTML = rows.length
    ? rows.map((row) => `
      <tr>
        <td>${escapeHtml(row.student_name)}<br><span class="muted">${escapeHtml(row.roll_number)}</span></td>
        <td>${cleanCertificateTitle(row)}</td>
        <td>${escapeHtml(row.category)}<br><span class="muted">${Math.round(row.confidence * 100)}% confidence</span></td>
        <td>${escapeHtml(row.event_level)}</td>
        <td><strong>${row.map_points}</strong></td>
        <td><span class="status ${row.status}">${escapeHtml(displayStatus(row))}</span></td>
        <td><div class="row-actions">${actionButtons(row)}</div></td>
      </tr>
    `).join("")
    : `<tr><td colspan="7">No certificates found.</td></tr>`;
}

function renderGallery() {
  const filter = $("#galleryFilter").value;
  const categories = [...new Set(state.data.certificates.map((row) => row.category))].sort();
  $("#galleryFilter").innerHTML = `<option value="">All categories</option>` + categories.map((category) => `
    <option value="${escapeAttr(category)}" ${category === filter ? "selected" : ""}>${escapeHtml(category)}</option>
  `).join("");
  const grouped = {};
  state.data.certificates.filter((row) => !filter || row.category === filter).forEach((row) => {
    grouped[row.category] ||= [];
    grouped[row.category].push(row);
  });
  const groups = Object.entries(grouped);
  $("#galleryGroups").innerHTML = groups.length
    ? groups.map(([category, rows]) => `
      <section class="gallery-section">
        <div class="gallery-heading"><h3>${escapeHtml(category)}</h3><span>${rows.length} certificate${rows.length === 1 ? "" : "s"}</span></div>
        <div class="gallery-grid">${rows.map(galleryCard).join("")}</div>
      </section>
    `).join("")
    : `<p class="muted">Upload certificates to build the gallery.</p>`;
}

function galleryCard(row) {
  return `
    <article class="cert-card">
      ${previewBlock(row)}
      <div class="cert-card-body">
        <div class="cert-card-title"><strong>${cleanCertificateTitle(row)}</strong><span class="status ${row.status}">${escapeHtml(displayStatus(row))}</span></div>
        <p>${escapeHtml(row.student_name)} / ${escapeHtml(row.roll_number)}</p>
        <div class="cert-card-meta"><span>${escapeHtml(row.event_level)}</span><span>${row.map_points} pts</span><span>${Math.round(row.confidence * 100)}%</span></div>
        <div class="actions">${actionButtons(row)}</div>
      </div>
    </article>
  `;
}

function renderApprovals() {
  const rows = state.data.certificates.filter((row) => row.status === "pending");
  $("#approvalList").innerHTML = rows.length
    ? rows.map((row) => approvalCard(row)).join("")
    : `<p class="muted">No certificates are waiting for approval.</p>`;
  $$("[data-review-id]").forEach((form) => form.addEventListener("submit", saveApproval));
}

function approvalCard(row) {
  return `
    <article class="certificate-item">
      <div class="certificate-main">
        <div>
          <div class="review-head"><h3>${cleanCertificateTitle(row)}</h3><span class="status pending">Pending</span></div>
          <p class="muted">${escapeHtml(row.student_name)} / ${escapeHtml(row.roll_number)} / ${escapeHtml(row.department)}</p>
          <div class="certificate-meta">
            <div class="meta-box"><span>AI category</span><strong>${escapeHtml(row.category)}</strong></div>
            <div class="meta-box"><span>Event level</span><strong>${escapeHtml(row.event_level)}</strong></div>
            <div class="meta-box"><span>Auto points</span><strong>${row.map_points}</strong></div>
            <div class="meta-box"><span>Confidence</span><strong>${Math.round(row.confidence * 100)}%</strong></div>
            <div class="meta-box"><span>Certificate</span><strong><a href="${fileUrl(row)}" target="_blank" rel="noreferrer">Open file</a></strong></div>
          </div>
          ${previewBlock(row)}
        </div>
        <form class="review-form" data-review-id="${row.id}">
          <label>Category<select name="category">${ruleOptions(row.category)}</select></label>
          <label>Level<select name="event_level">${levelOptions(row.event_level)}</select></label>
          <label>Manual MAP points<input name="map_points" type="number" min="0" value="${row.map_points}"></label>
          <label>Faculty note<textarea name="faculty_note">${escapeHtml(row.faculty_note || "")}</textarea></label>
          <div class="actions">
            <button name="action" value="approve">Approve</button>
            <button class="danger" name="action" value="reject">Reject</button>
            <button class="subtle" name="action" value="auto">Auto calculate</button>
            <button class="subtle" name="action" value="save">Save manual points</button>
          </div>
        </form>
      </div>
    </article>
  `;
}

function renderStudents() {
  const query = ($("#studentSearchInput").value || "").toLowerCase();
  const certsByStudent = {};
  state.data.certificates.forEach((cert) => {
    certsByStudent[cert.student_id] ||= [];
    certsByStudent[cert.student_id].push(cert);
  });
  const students = state.data.students.filter((student) => {
    const text = `${student.name} ${student.roll_number} ${student.department} ${(certsByStudent[student.id] || []).map((c) => c.original_filename).join(" ")}`.toLowerCase();
    return text.includes(query);
  });
  $("#studentList").innerHTML = students.length
    ? students.map((student) => `
      <article class="student-card">
        <div class="student-card-head">
          <div><h3>${escapeHtml(student.name)}</h3><p>${escapeHtml(student.roll_number)} / ${escapeHtml(student.department)}</p></div>
          <div class="student-points"><strong>${student.total}</strong><span>calculated pts</span></div>
          <div class="student-points"><strong>${student.approved}</strong><span>approved pts</span></div>
        </div>
        <div class="student-certificates">
          ${(certsByStudent[student.id] || []).map(studentCertificateRow).join("") || '<p class="muted">No certificates uploaded.</p>'}
        </div>
      </article>
    `).join("")
    : `<p class="muted">No students found.</p>`;
}

function studentCertificateRow(row) {
  return `
    <div class="student-cert-row">
      <span>${cleanCertificateTitle(row)}</span>
      <span>${escapeHtml(row.category)}</span>
      <strong>${row.map_points} pts</strong>
      <span class="status ${row.status}">${escapeHtml(displayStatus(row))}</span>
      <a href="${fileUrl(row)}" target="_blank" rel="noreferrer">Open</a>
    </div>
  `;
}

async function saveApproval(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const action = event.submitter?.value || "save";
  const payload = Object.fromEntries(new FormData(form));
  if (action === "approve") payload.status = "approved";
  if (action === "reject") payload.status = "rejected";
  if (action === "auto") payload.recalculate = true;
  delete payload.action;
  try {
    await api(`/api/certificates/${form.dataset.reviewId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    await refresh();
  } catch (error) {
    alert(error.message);
  }
}

function renderRules() {
  $("#rulesRows").innerHTML = state.data.rules.map((rule) => `
    <tr>
      <td>${escapeHtml(rule.category)}</td><td>${escapeHtml(rule.document_required || "")}</td>
      <td>${valueOrDash(rule.college)}</td><td>${valueOrDash(rule.taluka)}</td><td>${valueOrDash(rule.district)}</td>
      <td>${valueOrDash(rule.university)}</td><td>${valueOrDash(rule.state)}</td><td>${valueOrDash(rule.national)}</td>
      <td>${valueOrDash(rule.international)}</td><td>${valueOrDash(rule.fixed_points)}</td>
    </tr>
  `).join("");
}

async function uploadCertificates(event) {
  event.preventDefault();
  const status = $("#uploadStatus");
  status.textContent = "Submitting certificate and calculating points...";
  try {
    const form = new FormData(event.currentTarget);
    const result = await api("/api/upload", { method: "POST", body: form });
    status.textContent = `Submitted ${result.uploaded.length} certificate(s). Points are calculated automatically.`;
    event.currentTarget.querySelector('[name="certificate_text"]').value = "";
    event.currentTarget.querySelector('[name="count"]').value = "1";
    $("#fileInput").value = "";
    $("#fileSummary").textContent = "No files selected";
    clearSelectedPreviews();
    populateUploadProfile();
    await refresh();
    setPanel("gallery");
  } catch (error) {
    status.textContent = error.message;
  }
}

async function saveRule(event) {
  event.preventDefault();
  try {
    await api("/api/rules", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Object.fromEntries(new FormData(event.currentTarget))),
    });
    event.currentTarget.reset();
    event.currentTarget.classList.add("hidden");
    await refresh();
  } catch (error) {
    alert(error.message);
  }
}

async function saveProfile(event) {
  event.preventDefault();
  const status = $("#profileStatus");
  try {
    const form = new FormData(event.currentTarget);
    form.set("notify_dashboard", event.currentTarget.elements.notify_dashboard.checked ? "1" : "0");
    form.set("notify_email", event.currentTarget.elements.notify_email.checked ? "1" : "0");
    await api("/api/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Object.fromEntries(form)),
    });
    status.textContent = "Profile saved.";
    await refresh();
  } catch (error) {
    status.textContent = error.message;
  }
}

async function saveSettings(event) {
  event.preventDefault();
  const status = $("#settingsStatus");
  try {
    const form = new FormData(event.currentTarget);
    form.set("notify_dashboard", event.currentTarget.elements.notify_dashboard.checked ? "1" : "0");
    form.set("notify_email", event.currentTarget.elements.notify_email.checked ? "1" : "0");
    await api("/api/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Object.fromEntries(form)),
    });
    status.textContent = "Settings saved.";
    event.currentTarget.elements.current_password.value = "";
    event.currentTarget.elements.new_password.value = "";
    await refresh();
  } catch (error) {
    status.textContent = error.message;
  }
}

async function deleteCertificate(id) {
  if (!confirm("Delete this certificate record and file?")) return;
  try {
    await api(`/api/certificates/${id}`, { method: "DELETE" });
    await refresh();
  } catch (error) {
    alert(error.message);
  }
}

async function refresh() {
  const current = state.activeTab;
  await bootstrap();
  setPanel(current);
}

function populateUploadProfile() {
  const profile = state.data?.studentProfile;
  const form = $("#uploadForm");
  if (!form) return;
  const fields = {
    student_name: profile?.name || "",
    roll_number: profile?.roll_number || "",
    department: profile?.department || "",
    semester: profile?.semester || "",
    academic_year: profile?.academic_year || "",
  };
  Object.entries(fields).forEach(([name, value]) => {
    const input = form.elements[name];
    if (!input) return;
    if (state.user?.role === "student") input.value = value;
    input.readOnly = state.user?.role === "student";
  });
  $("#profileNote").textContent = state.user?.role === "student"
    ? "These details come from your registered student profile."
    : "Select or type student details before uploading.";
}

function populateProfileForm() {
  const form = $("#profileForm");
  if (!form || !state.user) return;
  const profile = state.data.studentProfile || {};
  form.elements.name.value = profile.name || state.user.name || "";
  form.elements.roll_number.value = profile.roll_number || "";
  form.elements.department.value = profile.department || "";
  form.elements.semester.value = profile.semester || "";
  form.elements.academic_year.value = profile.academic_year || "";
  form.elements.email.value = profile.email || "";
  form.elements.notify_dashboard.checked = !!state.user.notify_dashboard;
  form.elements.notify_email.checked = !!state.user.notify_email;
  form.elements.profile_photo.value = state.user.profile_photo || "";
  ["name", "roll_number", "department", "semester", "academic_year", "email"].forEach((name) => {
    form.elements[name].readOnly = state.user.role !== "student";
  });
  renderAvatar($("#profileAvatar"), profile.name || state.user.name, state.user.profile_photo);
}

function populateSettingsForm() {
  const form = $("#settingsForm");
  if (!form || !state.user) return;
  form.elements.theme.value = state.user.theme || localStorage.getItem("certimapTheme") || "system";
  form.elements.notify_dashboard.checked = !!state.user.notify_dashboard;
  form.elements.notify_email.checked = !!state.user.notify_email;
}

function renderTopbarProfile() {
  const profile = state.data?.studentProfile || {};
  renderAvatar($("#topbarAvatar"), profile.name || state.user?.name, state.user?.profile_photo);
}

function renderAvatar(element, name, photo) {
  if (!element) return;
  if (photo) {
    element.innerHTML = `<img src="${escapeAttr(photo)}" alt="">`;
  } else {
    element.textContent = initials(name);
  }
}

function avatarMarkup(name, photo) {
  if (photo) {
    return `<div class="profile-avatar"><img src="${escapeAttr(photo)}" alt=""></div>`;
  }
  return `<div class="profile-avatar">${initials(name)}</div>`;
}

function applyTheme(theme) {
  const selected = theme || "system";
  localStorage.setItem("certimapTheme", selected);
  const dark = selected === "dark" || (selected === "system" && window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.body.classList.toggle("dark", dark);
}

function openOAuth(provider) {
  location.href = `/api/oauth/${provider}/start`;
}

function renderSelectedFiles(files) {
  clearSelectedPreviews();
  const preview = $("#filePreview");
  if (!files.length) return;
  preview.innerHTML = Array.from(files).map((file) => {
    const url = URL.createObjectURL(file);
    state.previewUrls.push(url);
    if (file.type.startsWith("image/")) {
      return `<article class="upload-preview-card"><img src="${url}" alt="${escapeAttr(file.name)}"><strong>${escapeHtml(file.name)}</strong></article>`;
    }
    if (file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")) {
      return `<article class="upload-preview-card"><iframe src="${url}" title="${escapeAttr(file.name)}"></iframe><strong>${escapeHtml(file.name)}</strong></article>`;
    }
    return `<article class="upload-preview-card file-only"><span>${escapeHtml(file.name.split(".").pop().toUpperCase() || "FILE")}</span><strong>${escapeHtml(file.name)}</strong></article>`;
  }).join("");
}

function clearSelectedPreviews() {
  state.previewUrls.forEach((url) => URL.revokeObjectURL(url));
  state.previewUrls = [];
  $("#filePreview").innerHTML = "";
}

function previewBlock(row) {
  const url = fileUrl(row);
  if (row.preview_kind === "image") return `<a class="cert-preview" href="${url}" target="_blank" rel="noreferrer"><img src="${url}" alt="${escapeAttr(row.original_filename)}"></a>`;
  if (row.preview_kind === "pdf") return `<a class="cert-preview pdf-preview" href="${url}" target="_blank" rel="noreferrer"><span>PDF</span><small>Open certificate</small></a>`;
  return `<a class="cert-preview text-preview" href="${url}" target="_blank" rel="noreferrer"><span>TXT</span><small>Open certificate</small></a>`;
}

function actionButtons(row) {
  const deletable = canReview() || (state.user.role === "student" && row.status !== "approved");
  return deletable ? `<button class="danger" data-delete-id="${row.id}" type="button">Delete</button>` : "";
}

function fileUrl(row) {
  return `${row.file_url}?token=${encodeURIComponent(state.token)}`;
}

function cleanCertificateTitle(row) {
  return escapeHtml(row.event_name || row.original_filename.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " "));
}

function displayStatus(row) {
  if (state.user?.role === "student" && row.status === "pending") return "Points calculated";
  return String(row.status || "").replace("_", " ");
}

function ruleOptions(selected) {
  return state.data.rules.map((rule) => `<option value="${escapeAttr(rule.category)}" ${rule.category === selected ? "selected" : ""}>${escapeHtml(rule.category)}</option>`).join("");
}

function levelOptions(selected) {
  return ["college", "taluka", "district", "university", "state", "national", "international"]
    .map((level) => `<option value="${level}" ${level === selected ? "selected" : ""}>${level}</option>`).join("");
}

function initials(name) {
  return String(name || "CM").split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0].toUpperCase()).join("") || "CM";
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[char]));
}

function escapeAttr(value) {
  return escapeHtml(value).replace(/"/g, "&quot;");
}

function valueOrDash(value) {
  return value === null || value === undefined || value === "" ? "-" : value;
}

function setAuthMode(mode) {
  const loginMode = mode === "login";
  $("#loginForm").classList.toggle("hidden", !loginMode);
  $("#registerForm").classList.toggle("hidden", loginMode);
  $("#showLogin").classList.toggle("active", loginMode);
  $("#showRegister").classList.toggle("active", !loginMode);
}

$("#loginForm").addEventListener("submit", (event) => { event.preventDefault(); authenticate("/api/login", new FormData(event.currentTarget)); });
$("#registerForm").addEventListener("submit", (event) => { event.preventDefault(); authenticate("/api/register", new FormData(event.currentTarget)); });
$("#showLogin").addEventListener("click", () => setAuthMode("login"));
$("#showRegister").addEventListener("click", () => setAuthMode("register"));
$("#uploadForm").addEventListener("submit", uploadCertificates);
$("#ruleForm").addEventListener("submit", saveRule);
$("#profileForm").addEventListener("submit", saveProfile);
$("#settingsForm").addEventListener("submit", saveSettings);
$("#newRuleButton").addEventListener("click", () => $("#ruleForm").classList.toggle("hidden"));
$("#searchInput").addEventListener("input", renderRows);
$("#studentSearchInput").addEventListener("input", renderStudents);
$("#galleryFilter").addEventListener("change", renderGallery);
$("#printButton").addEventListener("click", () => window.print());
$("#logoutButton").addEventListener("click", () => {
  localStorage.removeItem("certimapToken");
  state.token = "";
  location.reload();
});
$("#settingsButton").addEventListener("click", () => setPanel("settings"));
$("#profileButton").addEventListener("click", () => setPanel("profile"));
$("#openProfileFromSettings").addEventListener("click", () => setPanel("profile"));
$("#settingsForm").elements.theme.addEventListener("change", (event) => applyTheme(event.currentTarget.value));
$("#profilePhotoInput").addEventListener("change", (event) => {
  const file = event.currentTarget.files[0];
  if (!file) return;
  if (!file.type.startsWith("image/")) {
    $("#profileStatus").textContent = "Choose an image file.";
    return;
  }
  if (file.size > 650000) {
    $("#profileStatus").textContent = "Choose an image under 650 KB.";
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    $("#profileForm").elements.profile_photo.value = reader.result;
    renderAvatar($("#profileAvatar"), $("#profileForm").elements.name.value, reader.result);
    renderAvatar($("#topbarAvatar"), $("#profileForm").elements.name.value, reader.result);
  };
  reader.readAsDataURL(file);
});
$$("[data-oauth]").forEach((button) => button.addEventListener("click", () => openOAuth(button.dataset.oauth)));
$("#fileInput").addEventListener("change", (event) => {
  const count = event.currentTarget.files.length;
  $("#fileSummary").textContent = count ? `${count} file(s) selected` : "No files selected";
  renderSelectedFiles(event.currentTarget.files);
});
$$(".tabs button").forEach((button) => button.addEventListener("click", () => setPanel(button.dataset.tab)));
document.addEventListener("click", (event) => {
  const deleteButton = event.target.closest("[data-delete-id]");
  if (deleteButton) deleteCertificate(deleteButton.dataset.deleteId);
});

// Notification rendering and interactions
function renderNotifications() {
  const notifs = (state.data && state.data.notifications) || [];
  const badge = $("#notifBadge");
  const list = $("#notifList");
  if (badge) {
    badge.textContent = notifs.length || 0;
    badge.classList.toggle("hidden", notifs.length === 0);
  }
  if (list) {
    list.innerHTML = notifs.length
      ? notifs.map((n) => `<li>${escapeHtml(n.message || n.text || String(n))}</li>`).join("")
      : `<li class="muted">No notifications</li>`;
  }
}

document.addEventListener("click", (event) => {
  const notifBtn = $("#notifButton");
  const dropdown = $("#notifDropdown");
  if (!notifBtn || !dropdown) return;
  if (notifBtn.contains(event.target)) {
    dropdown.classList.toggle("hidden");
    return;
  }
  if (!dropdown.contains(event.target)) {
    dropdown.classList.add("hidden");
  }
});

const incomingToken = new URLSearchParams(location.search).get("token");
if (incomingToken) {
  state.token = incomingToken;
  localStorage.setItem("certimapToken", incomingToken);
  history.replaceState({}, "", location.pathname);
}
applyTheme(localStorage.getItem("certimapTheme") || "system");
bootstrap();
