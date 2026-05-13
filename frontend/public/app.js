const API_BASE = window.SECURSVIGHT_VISION_API_URL || "http://127.0.0.1:8000";
const API = `${API_BASE}/api`;

function assetUrl(url) {
  if (!url) return "";
  return url.startsWith("/api/") ? `${API_BASE}${url}` : url;
}

let peopleCache = [];
let currentReport = null;

const $ = (id) => document.getElementById(id);

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  }[ch]));
}


function ensureModalRoot() {
  let root = document.getElementById("modalRoot");
  if (root) return root;

  root = document.createElement("div");
  root.id = "modalRoot";
  root.className = "modal-root hidden";
  root.innerHTML = `
    <div class="modal-backdrop"></div>
    <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="modalTitle">
      <div class="modal-icon" id="modalIcon">!</div>
      <div class="modal-content">
        <h3 id="modalTitle">Confirm Action</h3>
        <p id="modalMessage"></p>
      </div>
      <div class="modal-actions" id="modalActions"></div>
    </div>
  `;
  document.body.appendChild(root);
  return root;
}

function openModal({ title = "Message", message = "", confirmText = "OK", cancelText = null, danger = false } = {}) {
  const root = ensureModalRoot();
  const titleEl = root.querySelector("#modalTitle");
  const messageEl = root.querySelector("#modalMessage");
  const iconEl = root.querySelector("#modalIcon");
  const actionsEl = root.querySelector("#modalActions");

  titleEl.textContent = title;
  messageEl.textContent = message;
  iconEl.textContent = danger ? "!" : "i";
  iconEl.classList.toggle("danger", danger);
  actionsEl.innerHTML = "";

  return new Promise((resolve) => {
    let settled = false;
    const finish = (value) => {
      if (settled) return;
      settled = true;
      root.classList.add("hidden");
      document.removeEventListener("keydown", onKeyDown);
      resolve(value);
    };

    const onKeyDown = (event) => {
      if (event.key === "Escape") finish(false);
      if (event.key === "Enter" && !cancelText) finish(true);
    };

    if (cancelText) {
      const cancelBtn = document.createElement("button");
      cancelBtn.type = "button";
      cancelBtn.textContent = cancelText;
      cancelBtn.addEventListener("click", () => finish(false));
      actionsEl.appendChild(cancelBtn);
    }

    const okBtn = document.createElement("button");
    okBtn.type = "button";
    okBtn.className = danger ? "danger" : "primary";
    okBtn.textContent = confirmText;
    okBtn.addEventListener("click", () => finish(true));
    actionsEl.appendChild(okBtn);

    root.classList.remove("hidden");
    document.addEventListener("keydown", onKeyDown);
    okBtn.focus();
  });
}

function showAlert(message, title = "SecureSight Vision") {
  return openModal({ title, message, confirmText: "OK" });
}

function showConfirm(message, title = "Are you sure?", confirmText = "OK") {
  return openModal({ title, message, confirmText, cancelText: "Cancel", danger: true });
}

async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, options);
  if (!res.ok) {
    let message = await res.text();
    try {
      message = JSON.parse(message).detail || message;
    } catch {}
    throw new Error(message);
  }
  return res.json();
}

function setPage(page) {
  document.querySelectorAll(".page").forEach((el) => el.classList.remove("active"));
  document.querySelectorAll(".nav").forEach((el) => el.classList.remove("active"));
  $(`page-${page}`).classList.add("active");
  document.querySelector(`[data-page="${page}"]`).classList.add("active");

  if (page === "people") loadPeople();
  if (page === "reports") loadReports();
}

async function loadHealth() {
  try {
    const data = await fetch(`${API_BASE}/health`).then((r) => r.json());
    const info = data.face_provider || {};
    $("deviceText").textContent = info.device || "--";
    $("providerText").textContent = (info.selected_providers || []).join(", ") || "No provider";
  } catch {
    $("deviceText").textContent = "--";
    $("providerText").textContent = "Backend not ready";
  }
}

async function testFaceEngine() {
  try {
    $("providerText").textContent = "Testing face engine...";
    const data = await fetch(`${API_BASE}/face/test`).then((r) => r.json());
    $("deviceText").textContent = data.face_provider?.device || "--";
    $("providerText").textContent = `Loaded: ${(data.loaded_models || []).join(", ")}`;
    await showAlert("Face engine loaded successfully.", "Face Engine");
  } catch (err) {
    await showAlert(`Face test failed:
${err.message}`, "Face Engine Error");
    loadHealth();
  }
}

async function startAnalyze() {
  const file = $("videoFile").files[0];
  const sampleEvery = $("sampleEvery").value || "1";

  if (!file) {
    await showAlert("Choose a video first.", "Missing Video");
    return;
  }

  $("reportView").innerHTML = "";
  $("statusCard").classList.remove("hidden");
  $("statusText").textContent = "Uploading";
  $("statusStep").textContent = "Uploading video...";
  $("progressBar").style.width = "2%";

  const form = new FormData();
  form.append("file", file);
  form.append("sample_every", sampleEvery);

  try {
    const started = await api("/analyze/start", { method: "POST", body: form });
    pollStatus(started.job_id);
  } catch (err) {
    await showAlert(`Could not start analysis:
${err.message}`, "Analysis Error");
  }
}

function pollStatus(jobId) {
  const timer = setInterval(async () => {
    try {
      const status = await api(`/analyze/status/${jobId}`);

      $("statusText").textContent = `Status: ${status.status}`;
      $("statusDevice").textContent = `Device: ${status.face_device || "--"}`;
      $("statusStep").textContent = status.step || "--";
      $("progressBar").style.width = `${status.progress || 0}%`;
      $("elapsedText").textContent = `Analyze Time: ${status.analysis_time || `${status.elapsed_seconds || 0}s`}`;

      if (status.status === "done") {
        clearInterval(timer);
        const result = await api(`/analyze/result/${jobId}`);
        currentReport = result;
        renderReport(result);
        loadReports();
      }

      if (status.status === "error") {
        clearInterval(timer);
        await showAlert(`Analysis failed:
${status.error || "Unknown error"}`, "Analysis Failed");
      }
    } catch (err) {
      clearInterval(timer);
      await showAlert(`Status error:
${err.message}`, "Status Error");
    }
  }, 1000);
}

function getReportRecommendations(report) {
  const recommendations = report.summary?.recommendations || [];
  if (!recommendations.length) return `<p class="muted">No immediate action needed.</p>`;
  return `<ul class="recommendations">${recommendations.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function downloadReportCsv(report) {
  const rows = [[
    "Name", "Employee ID", "Role", "Department", "Device Date", "Entry", "Exit", "Confidence", "Analyze Time"
  ]];

  (report.attendance || []).forEach((row) => rows.push([
    row.name || "", row.employee_id || "", row.role || "", row.department || "",
    row.device_date || report.device_date || "", row.entry_time || "", row.exit_time || "",
    row.confidence || "", report.summary?.analysis_time || ""
  ]));

  const csv = rows.map((cols) => cols.map((v) => `"${String(v).replaceAll('"', '""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `securesight-vision-report-${report.job_id || Date.now()}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function renderReport(report) {
  const peopleOptions = peopleCache.map((p) => `<option value="${p.id}">${escapeHtml(p.name)} (${escapeHtml(p.employee_id)})</option>`).join("");
  const knownEvents = report.summary.known_events ?? report.attendance?.length ?? 0;
  const uniqueKnown = report.summary.known_count ?? 0;

  $("reportView").innerHTML = `
    <div class="card report-dashboard">
      <div class="report-head report-head-wrap">
        <div>
          <h3>Security Attendance Report</h3>
          <p class="muted">Operational summary for the monitoring team. Re-entry is counted again after the person leaves the frame and appears later.</p>
        </div>
        <div class="report-actions">
          <button onclick="downloadReportCsv(currentReport)">Export CSV</button>
          <button onclick="window.print()">Print</button>
        </div>
      </div>

      <div class="stats six-stats">
        <div class="stat"><strong>${uniqueKnown}</strong><span>Unique Known People</span></div>
        <div class="stat"><strong>${knownEvents}</strong><span>Known Detections</span></div>
        <div class="stat"><strong>${report.summary.repeated_detections || report.summary.repeat_visitors || 0}</strong><span>Repeated Detections</span></div>
        <div class="stat"><strong>${report.summary.unknown_count}</strong><span>Unknown Faces</span></div>
        <div class="stat"><strong>${report.summary.analysis_time || "--"}</strong><span>Analyze Time</span></div>
        <div class="stat"><strong>${escapeHtml(report.face_device || "--")}</strong><span>Device</span></div>
      </div>

      <div class="insight-box">
        <h4>Guard Notes</h4>
        ${getReportRecommendations(report)}
        <p class="muted">Video analysis completed in <b>${escapeHtml(report.summary.analysis_time || "--")}</b> using ${escapeHtml(report.summary.parallel_workers || "--")} side-worker(s) for saving unknown face crops.</p>
      </div>
    </div>

    <div class="card">
      <h3>Known Person Detection Log</h3>
      <p class="muted">Each row is one known-person detection event. The date is always taken from this device.</p>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>ID</th>
              <th>Role</th>
              <th>Department</th>
              <th>Device Date</th>
              <th>Entry</th>
              <th>Exit</th>
              <th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            ${(report.attendance || []).map((row) => `
              <tr>
                <td>${escapeHtml(row.name)}</td>
                <td>${escapeHtml(row.employee_id)}</td>
                <td>${escapeHtml(row.role)}</td>
                <td>${escapeHtml(row.department)}</td>
                <td>${escapeHtml(row.device_date || report.device_date || "-")}</td>
                <td>${escapeHtml(row.entry_time || "-")}</td>
                <td>${escapeHtml(row.exit_time || "-")}</td>
                <td>${escapeHtml(row.confidence)}</td>
              </tr>
            `).join("") || `<tr><td colspan="8">No known people detected.</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>

    <div class="card">
      <h3>Unknown Faces Review</h3>
      <p class="muted">Link unknown faces to a profile or create a new known person from a clear snapshot.</p>
      <div class="unknown-grid">
        ${(report.unknown || []).map((u) => `
          <div class="unknown-card">
            <img src="${assetUrl(u.snapshot_url)}" />
            <div class="unknown-meta">
              <small>Device Date: ${escapeHtml(u.device_date || report.device_date || "-")}</small>
              <small>Score: ${escapeHtml(u.score)}</small>
            </div>

            <div class="unknown-section">
              <b>Save to existing person</b>
              <select id="link-${u.snapshot}">
                <option value="">Choose person...</option>
                ${peopleOptions}
              </select>
              <button onclick="linkUnknown('${u.snapshot}')">Save to Profile</button>
              <button class="danger" onclick="ignoreUnknown('${u.snapshot}')">Ignore Future</button>
            </div>

            <div class="unknown-section create-new">
              <b>Create new known person</b>
              <input id="new-name-${u.snapshot}" placeholder="Name" />
              <input id="new-employee-${u.snapshot}" placeholder="Employee ID / Student ID" />
              <input id="new-role-${u.snapshot}" placeholder="Role" />
              <input id="new-department-${u.snapshot}" placeholder="Department" />
              <button class="primary" onclick="createPersonFromUnknown('${u.snapshot}')">Create Person</button>
            </div>
          </div>
        `).join("") || `<p class="muted">No unknown faces.</p>`}
      </div>
    </div>
  `;
}

async function loadPeople() {
  peopleCache = await api("/people");
  const grid = $("peopleGrid");

  grid.innerHTML = peopleCache.map((person) => `
    <div class="card person-card">
      <h3>${escapeHtml(person.name)}</h3>
      <p class="muted">
        ${escapeHtml(person.employee_id)} ·
        ${escapeHtml(person.role)} ·
        ${escapeHtml(person.department)}
      </p>

      <div class="thumbs">
        ${(person.image_urls || []).map((url, index) => `
          <div class="thumb">
            <img src="${assetUrl(url)}" />
            <button onclick="deletePersonImage('${person.id}', '${person.images[index]}')">Delete</button>
          </div>
        `).join("")}
      </div>

      <div class="add-images">
        <input id="new-images-${person.id}" type="file" accept="image/*" multiple />
        <button onclick="addImages('${person.id}')">Add Images</button>
      </div>

      <div class="person-actions">
        <button onclick="editPerson('${person.id}')">Edit</button>
        <button onclick="deletePerson('${person.id}')">Delete Person</button>
      </div>
    </div>
  `).join("") || `<div class="card">No people yet.</div>`;
}

async function savePerson(event) {
  event.preventDefault();

  const personId = $("personId").value;
  const form = new FormData();
  form.append("name", $("name").value);
  form.append("employee_id", $("employeeId").value);
  form.append("role", $("role").value);
  form.append("department", $("department").value);

  [...$("faceImages").files].forEach((file) => form.append("images", file));

  try {
    if (personId) {
      await api(`/people/${personId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: $("name").value,
          employee_id: $("employeeId").value,
          role: $("role").value,
          department: $("department").value,
        }),
      });

      if ($("faceImages").files.length) {
        const imgForm = new FormData();
        [...$("faceImages").files].forEach((file) => imgForm.append("images", file));
        await api(`/people/${personId}/images`, { method: "POST", body: imgForm });
      }
    } else {
      await api("/people", { method: "POST", body: form });
    }

    resetPersonForm();
    await loadPeople();
    await loadHealth();
  } catch (err) {
    await showAlert(`Save failed:
${err.message}`, "Save Failed");
  }
}

function editPerson(id) {
  const person = peopleCache.find((p) => p.id === id);
  if (!person) return;

  $("personId").value = person.id;
  $("name").value = person.name || "";
  $("employeeId").value = person.employee_id || "";
  $("role").value = person.role || "";
  $("department").value = person.department || "";
  $("savePersonBtn").textContent = "Save Changes";
  $("cancelEditBtn").classList.remove("hidden");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function resetPersonForm() {
  $("personForm").reset();
  $("personId").value = "";
  $("savePersonBtn").textContent = "Add Person";
  $("cancelEditBtn").classList.add("hidden");
}

async function deletePerson(id) {
  if (!(await showConfirm("Delete this person?", "Delete Person", "Delete"))) return;
  await api(`/people/${id}`, { method: "DELETE" });
  loadPeople();
}

async function addImages(id) {
  const input = $(`new-images-${id}`);
  if (!input.files.length) return showAlert("Choose images first.", "Missing Images");

  const form = new FormData();
  [...input.files].forEach((file) => form.append("images", file));
  await api(`/people/${id}/images`, { method: "POST", body: form });
  loadPeople();
}

async function deletePersonImage(personId, filename) {
  if (!(await showConfirm("Delete this image?", "Delete Image", "Delete"))) return;
  await api(`/people/${personId}/images/${filename}`, { method: "DELETE" });
  loadPeople();
}

async function linkUnknown(snapshot) {
  const select = $(`link-${snapshot}`);
  const personId = select.value;

  if (!personId) return showAlert("Choose a person first.", "Choose Person");

  try {
    const result = await api("/unknown/link", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ snapshot, person_id: personId }),
    });

    if (currentReport) {
      currentReport.unknown = (currentReport.unknown || []).filter((u) => u.snapshot !== snapshot);
      if (currentReport.summary) currentReport.summary.unknown_count = currentReport.unknown.length;
      renderReport(currentReport);
    }

    await showAlert(result.embedding_created
      ? "Unknown face saved to the person profile. The exact detection embedding was also saved for future matching."
      : "Image saved, but no reusable embedding was created. Add a clearer face photo if this person still appears as unknown.", "Saved");
    await loadPeople();
    await loadReports();
  } catch (err) {
    await showAlert(`Link failed:
${err.message}`, "Link Failed");
  }
}


async function ignoreUnknown(snapshot) {
  if (!(await showConfirm("Ignore this unknown face? Similar future detections will be hidden.", "Ignore Future Detections", "Ignore"))) return;

  try {
    const result = await api("/unknown/ignore", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ snapshot }),
    });

    if (currentReport) {
      currentReport.unknown = (currentReport.unknown || []).filter((u) => u.snapshot !== snapshot);
      if (currentReport.summary) currentReport.summary.unknown_count = currentReport.unknown.length;
      renderReport(currentReport);
    }

    await loadReports();
    await showAlert(result.embedding_created
      ? "Ignored. Similar future detections will be hidden."
      : "Ignored in reports. No reusable face embedding was created, so future suppression may be limited.", "Ignored");
  } catch (err) {
    await showAlert(`Ignore failed:
${err.message}`, "Ignore Failed");
  }
}


async function createPersonFromUnknown(snapshot) {
  const name = $(`new-name-${snapshot}`).value.trim();
  const employeeId = $(`new-employee-${snapshot}`).value.trim();
  const role = $(`new-role-${snapshot}`).value.trim();
  const department = $(`new-department-${snapshot}`).value.trim();

  if (!name) {
    await showAlert("Name is required to create a new known person.", "Name Required");
    return;
  }

  try {
    const result = await api("/unknown/create-person", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        snapshot,
        name,
        employee_id: employeeId,
        role,
        department,
      }),
    });

    const embMessage = result.embedding_created
      ? "Face embedding saved. This person can be recognized in future videos."
      : "Person created, but no face embedding was created. Try adding a clearer image later.";

    await showAlert(`New known person created successfully.
${embMessage}`, "Person Created");
    await loadPeople();
    await loadReports();

    if (currentReport) {
      currentReport.unknown = (currentReport.unknown || []).filter((u) => u.snapshot !== snapshot);
      if (currentReport.summary) currentReport.summary.unknown_count = currentReport.unknown.length;
      renderReport(currentReport);
    }
  } catch (err) {
    await showAlert(`Create person failed:
${err.message}`, "Create Person Failed");
  }
}


async function loadReports() {
  const reports = await api("/reports");
  const list = $("reportsList");

  list.innerHTML = reports.map((report, index) => `
    <div class="card saved-report-card">
      <div class="report-head report-head-wrap">
        <div>
          <h3>${escapeHtml(report.video)}</h3>
          <p class="muted">Created: ${report.created_at ? new Date(report.created_at * 1000).toLocaleString() : "--"}</p>
        </div>
        <div class="report-actions">
          <button onclick="currentReport = savedReportsCache[${index}]; renderReport(currentReport); setPage('analyze'); window.scrollTo({ top: 0, behavior: 'smooth' });">Open Report</button>
          <button class="danger" onclick="deleteReport('${report.job_id}')">Delete Report</button>
        </div>
      </div>
      <div class="report-summary">
        <div><strong>${report.summary.known_count || 0}</strong><br><span class="muted">Unique Known</span></div>
        <div><strong>${report.summary.known_events ?? report.attendance?.length ?? 0}</strong><br><span class="muted">Known Detections</span></div>
        <div><strong>${report.summary.repeated_detections || report.summary.repeat_visitors || 0}</strong><br><span class="muted">Repeated</span></div>
        <div><strong>${report.summary.unknown_count || 0}</strong><br><span class="muted">Unknown</span></div>
        <div><strong>${report.summary.analysis_time || "--"}</strong><br><span class="muted">Analyze Time</span></div>
        <div><strong>${escapeHtml(report.face_device || "--")}</strong><br><span class="muted">Device</span></div>
      </div>
    </div>
  `).join("") || `<div class="card">No saved reports yet.</div>`;

  window.savedReportsCache = reports;
}

async function deleteReport(jobId) {
  if (!(await showConfirm("Delete this saved report?", "Delete Report", "Delete"))) return;

  try {
    await api(`/reports/${jobId}`, { method: "DELETE" });
    if (currentReport?.job_id === jobId) {
      currentReport = null;
      $("reportView").innerHTML = "";
    }
    await loadReports();
  } catch (err) {
    await showAlert(`Delete report failed:
${err.message}`, "Delete Report Failed");
  }
}


document.querySelectorAll(".nav").forEach((btn) => {
  btn.addEventListener("click", () => setPage(btn.dataset.page));
});

$("faceTestBtn").addEventListener("click", testFaceEngine);
$("startAnalyzeBtn").addEventListener("click", startAnalyze);
$("personForm").addEventListener("submit", savePerson);
$("cancelEditBtn").addEventListener("click", resetPersonForm);

loadHealth();
loadPeople();
loadReports();
