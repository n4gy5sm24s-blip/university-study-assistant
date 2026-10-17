const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];

const state = { courses: [], selectedCourse: null, mode: "draft", busy: false };
const modeCopy = {
  draft: { placeholder: "粘贴作业题目，按 Enter 发送…", hint: "将根据当前课程资料生成作业草稿", label: "写作业" },
  ask: { placeholder: "输入你想问的问题…", hint: "将优先依据当前课程资料回答", label: "随时问答" },
  review: { placeholder: "输入原作业题目…", hint: "请同时粘贴你已经写好的答案", label: "检查答案" }
};

function escapeHtml(value) {
  const element = document.createElement("div");
  element.textContent = value ?? "";
  return element.innerHTML;
}

function closeSidebar() {
  $("#sidebar").classList.remove("open");
  $("#sidebar-scrim").classList.remove("open");
}

async function api(url, options = {}) {
  const response = await fetch(url, options);
  const body = response.status === 204 ? null : await response.json();
  if (!response.ok) throw new Error(body?.detail || "请求失败");
  return body;
}

async function loadCourses(preferredId = null) {
  state.courses = await api("/api/courses");
  renderCourses();
  const nextId = preferredId ?? state.selectedCourse?.id ?? state.courses[0]?.id;
  const course = state.courses.find(item => item.id === Number(nextId));
  selectCourse(course || null);
}

function renderCourses() {
  const list = $("#course-list");
  if (!state.courses.length) {
    list.innerHTML = '<p class="sidebar-empty">还没有课程。创建课程并上传资料后，就可以开始写作业。</p>';
    return;
  }
  list.innerHTML = state.courses.map(course => `
    <button class="course-item ${state.selectedCourse?.id === course.id ? "active" : ""}" data-course-id="${course.id}" type="button">
      <strong>${escapeHtml(course.name)}</strong>
      <span class="course-delete" data-delete-course="${course.id}" title="删除课程">×</span>
    </button>
  `).join("");
}

function selectCourse(course) {
  state.selectedCourse = course;
  $("#active-course-name").textContent = course?.name || "选择一门课程";
  $("#active-course-detail").textContent = course?.description || (course ? "课程工作区" : "创建课程后开始写作业");
  $("#materials-open").disabled = !course;
  $("#review-open").disabled = !course;
  renderCourses();
  closeSidebar();
}

function setMode(mode) {
  state.mode = mode;
  $$(".mode-tab").forEach(button => button.classList.toggle("active", button.dataset.mode === mode));
  $("#composer-input").placeholder = modeCopy[mode].placeholder;
  $("#composer-hint").textContent = modeCopy[mode].hint;
  $("#attempt-input").classList.toggle("hidden", mode !== "review");
  if (mode !== "review") $("#attempt-input").value = "";
  $("#composer-input").focus();
}

function addMessage(role, content, citations = [], meta = "") {
  $("#welcome").classList.add("hidden");
  const message = document.createElement("article");
  message.className = `message ${role}`;
  const sourceChips = citations.map(citation => `
    <span class="citation-chip">[${citation.number}] ${escapeHtml(citation.filename)}${citation.section_title ? ` · ${escapeHtml(citation.section_title)}` : ""}</span>
  `).join("");
  message.innerHTML = `
    <div class="message-avatar">${role === "user" ? "你" : "C"}</div>
    <div>
      <div class="message-role">${role === "user" ? "你" : "Coursework AI"}</div>
      <div class="message-content">${escapeHtml(content)}</div>
      ${sourceChips ? `<div class="citations">${sourceChips}</div>` : ""}
      ${meta ? `<div class="message-meta">${escapeHtml(meta)}</div>` : ""}
    </div>
  `;
  $("#message-list").append(message);
  $("#conversation").scrollTop = $("#conversation").scrollHeight;
}

async function submitPrompt() {
  const prompt = $("#composer-input").value.trim();
  const attempt = $("#attempt-input").value.trim();
  if (!prompt || state.busy) return;
  if (!state.selectedCourse) {
    $("#composer-status").textContent = "请先在左侧创建或选择一门课程。";
    return;
  }
  if (state.mode === "review" && !attempt) {
    $("#composer-status").textContent = "检查答案模式需要粘贴你已经写好的内容。";
    return;
  }
  addMessage("user", state.mode === "review" ? `${prompt}\n\n我的答案：\n${attempt}` : prompt, [], modeCopy[state.mode].label);
  $("#composer-input").value = "";
  $("#attempt-input").value = "";
  state.busy = true;
  $("#send-button").disabled = true;
  $("#composer-status").textContent = state.mode === "draft" ? "正在检索资料并起草作业…" : "正在检索课程资料…";
  try {
    let result;
    if (state.mode === "ask") {
      result = await api(`/api/courses/${state.selectedCourse.id}/questions`, {
        method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({question: prompt})
      });
      addMessage("assistant", result.answer, result.citations, generationLabel(result.generation_method));
    } else {
      result = await api(`/api/courses/${state.selectedCourse.id}/homework-guidance`, {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({question: prompt, mode: state.mode, student_attempt: attempt})
      });
      addMessage("assistant", result.guidance, result.citations, generationLabel(result.generation_method));
    }
    $("#composer-status").textContent = result.grounding_status === "no_evidence" ? "课程资料依据不足" : "";
  } catch (error) {
    addMessage("assistant", `没有完成这次请求：${error.message}`);
    $("#composer-status").textContent = "";
  } finally {
    state.busy = false;
    $("#send-button").disabled = false;
    $("#composer-input").focus();
  }
}

function generationLabel(method) {
  if (method === "openai_responses") return "生成模型 · 已使用课程资料";
  if (method === "extractive_fallback") return "模型不可用 · 已退回资料框架";
  if (method === "extractive") return "本地资料模式";
  return "未生成";
}

async function loadDocuments() {
  const list = $("#document-list");
  list.innerHTML = '<p class="form-message">正在读取资料…</p>';
  const documents = await api(`/api/courses/${state.selectedCourse.id}/documents`);
  list.innerHTML = documents.length ? documents.map(document => `
    <div class="document-row"><div><strong>${escapeHtml(document.filename)}</strong><div class="document-meta">${document.status} · ${document.size_bytes} bytes</div></div><button class="delete-button" data-delete-document="${document.id}" type="button">删除</button></div>
  `).join("") : '<p class="form-message">还没有资料。上传 TXT 或 Markdown 后即可使用。</p>';
}

$("#new-course").addEventListener("click", () => $("#course-dialog").showModal());
$("#course-form").addEventListener("submit", async event => {
  event.preventDefault();
  $("#course-message").textContent = "正在创建…";
  try {
    const course = await api("/api/courses", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({name: $("#course-name").value, description: $("#course-description").value})});
    event.target.reset();
    $("#course-dialog").close();
    await loadCourses(course.id);
  } catch (error) { $("#course-message").textContent = error.message; }
});

$("#course-list").addEventListener("click", async event => {
  const deleteId = event.target.dataset.deleteCourse;
  if (deleteId) {
    event.stopPropagation();
    if (!window.confirm("删除这门课程及其全部资料？")) return;
    await api(`/api/courses/${deleteId}`, {method: "DELETE"});
    if (state.selectedCourse?.id === Number(deleteId)) state.selectedCourse = null;
    await loadCourses();
    return;
  }
  const button = event.target.closest("[data-course-id]");
  if (button) selectCourse(state.courses.find(course => course.id === Number(button.dataset.courseId)));
});

$$(".mode-tab").forEach(button => button.addEventListener("click", () => setMode(button.dataset.mode)));
$("#composer-form").addEventListener("submit", event => { event.preventDefault(); submitPrompt(); });
$("#composer-input").addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); submitPrompt(); }
});
$("#composer-input").addEventListener("input", event => {
  event.target.style.height = "auto";
  event.target.style.height = `${Math.min(event.target.scrollHeight, 190)}px`;
});

$("#materials-open").addEventListener("click", async () => { $("#materials-dialog").showModal(); await loadDocuments(); });
$("#document-form").addEventListener("submit", async event => {
  event.preventDefault();
  const file = $("#document-file").files[0];
  if (!file) return;
  $("#document-message").textContent = "正在上传并建立索引…";
  try {
    await api(`/api/courses/${state.selectedCourse.id}/documents`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({filename: file.name, content: await file.text()})});
    event.target.reset();
    $("#document-message").textContent = "资料已加入当前课程。";
    await loadDocuments();
  } catch (error) { $("#document-message").textContent = error.message; }
});
$("#document-list").addEventListener("click", async event => {
  const id = event.target.dataset.deleteDocument;
  if (!id || !window.confirm("删除这份资料？")) return;
  await api(`/api/courses/${state.selectedCourse.id}/documents/${id}`, {method: "DELETE"});
  await loadDocuments();
});

$("#review-open").addEventListener("click", () => $("#review-dialog").showModal());
$("#review-form").addEventListener("submit", async event => {
  event.preventDefault();
  $("#review-message").textContent = "正在生成计划…";
  $("#review-result").innerHTML = "";
  try {
    const result = await api(`/api/courses/${state.selectedCourse.id}/review-plans`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({scope: $("#review-scope").value, available_hours: Number($("#review-hours").value), weak_topics: $("#weak-topics").value})});
    $("#review-message").textContent = result.overview;
    if (result.status !== "ready") return;
    $("#review-result").innerHTML = result.blocks.map(block => `<div class="review-block"><strong>${block.minutes} 分钟 · ${escapeHtml(block.topic)}</strong><br>${escapeHtml(block.activity)}</div>`).join("") + `<h3>闭卷自测</h3><ol>${result.self_test.map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ol>`;
  } catch (error) { $("#review-message").textContent = error.message; }
});

$$("[data-close]").forEach(button => button.addEventListener("click", () => $(`#${button.dataset.close}`).close()));
$("#menu-button").addEventListener("click", () => { $("#sidebar").classList.add("open"); $("#sidebar-scrim").classList.add("open"); });
$("#sidebar-scrim").addEventListener("click", closeSidebar);

loadCourses().catch(error => { $("#course-list").innerHTML = `<p class="sidebar-empty">${escapeHtml(error.message)}</p>`; });
