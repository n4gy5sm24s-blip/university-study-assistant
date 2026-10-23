const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];

const state = { courses: [], selectedCourse: null, mode: "draft", busy: false, homeworkImage: null, reviewSession: null };
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
  $("#attach-button").classList.toggle("hidden", mode === "ask");
  if (mode === "ask") clearHomeworkImage();
  if (mode !== "review") $("#attempt-input").value = "";
  $("#composer-input").focus();
}

function addMessage(role, content, citations = [], meta = "", assessment = null) {
  $("#welcome").classList.add("hidden");
  const message = document.createElement("article");
  message.className = `message ${role}`;
  const sourceChips = citations.map(citation => `
    <span class="citation-chip">[${citation.number}] ${escapeHtml(citation.filename)}${citation.section_title ? ` · ${escapeHtml(citation.section_title)}` : ""}</span>
  `).join("");
  const assessmentCard = assessment && assessment.level !== "sufficient" ? `
    <section class="evidence-card ${escapeHtml(assessment.level)}">
      <div class="evidence-card-head"><strong>资料充分度</strong><span>${assessment.coverage_percent}%</span></div>
      <p>${escapeHtml(assessment.summary)}</p>
      ${assessment.missing?.length ? `<h4>还缺少</h4><ul>${assessment.missing.map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : ""}
      ${assessment.capture_suggestions?.length ? `<h4>建议补拍</h4><ol>${assessment.capture_suggestions.map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ol><small>请把小节标题、正文、图表和页码一起拍清楚。</small>` : ""}
    </section>
  ` : "";
  message.innerHTML = `
    <div class="message-avatar">${role === "user" ? "你" : "C"}</div>
    <div>
      <div class="message-role">${role === "user" ? "你" : "Coursework AI"}</div>
      <div class="message-content">${escapeHtml(content)}</div>
      ${assessmentCard}
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
  if ((!prompt && !state.homeworkImage) || state.busy) return;
  if (!state.selectedCourse) {
    $("#composer-status").textContent = "请先在左侧创建或选择一门课程。";
    return;
  }
  if (state.mode === "review" && !attempt) {
    $("#composer-status").textContent = "检查答案模式需要粘贴你已经写好的内容。";
    return;
  }
  const displayedPrompt = prompt || "请完成图片中的作业题";
  const imageNote = state.homeworkImage ? `\n\n📷 已上传题目图片：${state.homeworkImage.name}` : "";
  addMessage("user", (state.mode === "review" ? `${displayedPrompt}\n\n我的答案：\n${attempt}` : displayedPrompt) + imageNote, [], modeCopy[state.mode].label);
  const imageDataUrl = state.homeworkImage?.dataUrl || "";
  $("#composer-input").value = "";
  $("#attempt-input").value = "";
  clearHomeworkImage();
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
        body: JSON.stringify({question: prompt, mode: state.mode, student_attempt: attempt, image_data_url: imageDataUrl})
      });
      addMessage("assistant", result.guidance, result.citations, generationLabel(result.generation_method), result.evidence_assessment);
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
  `).join("") : '<p class="form-message">还没有资料。优先上传老师的 PPTX，也支持 TXT 和 Markdown。</p>';
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

function clearHomeworkImage() {
  state.homeworkImage = null;
  $("#homework-image").value = "";
  $("#image-preview-thumb").removeAttribute("src");
  $("#image-preview").classList.add("hidden");
}

$("#homework-image").addEventListener("change", event => {
  const file = event.target.files[0];
  if (!file) return;
  if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
    $("#composer-status").textContent = "题目图片只支持 JPG、PNG 或 WebP。";
    clearHomeworkImage();
    return;
  }
  if (file.size > 5 * 1024 * 1024) {
    $("#composer-status").textContent = "题目图片不能超过 5MB。";
    clearHomeworkImage();
    return;
  }
  const reader = new FileReader();
  reader.addEventListener("load", () => {
    state.homeworkImage = {name: file.name, dataUrl: reader.result};
    $("#image-preview-thumb").src = reader.result;
    $("#image-preview-name").textContent = file.name;
    $("#image-preview").classList.remove("hidden");
    $("#composer-status").textContent = "";
  });
  reader.readAsDataURL(file);
});
$("#image-remove").addEventListener("click", clearHomeworkImage);

$("#materials-open").addEventListener("click", async () => { $("#materials-dialog").showModal(); await loadDocuments(); });
$("#document-form").addEventListener("submit", async event => {
  event.preventDefault();
  const files = [...$("#document-file").files];
  if (!files.length) return;
  const submitButton = event.target.querySelector('button[type="submit"]');
  submitButton.disabled = true;
  let succeeded = 0;
  const failures = [];
  for (let index = 0; index < files.length; index += 1) {
    const file = files[index];
    $("#document-message").textContent = `正在处理 ${index + 1}/${files.length}：${file.name}`;
    try {
      await uploadDocument(file);
      succeeded += 1;
    } catch (error) {
      failures.push(`${file.name}：${error.message}`);
    }
  }
  event.target.reset();
  submitButton.disabled = false;
  const result = `已成功上传 ${succeeded}/${files.length} 份资料。`;
  $("#document-message").textContent = failures.length
    ? `${result} 失败：${failures.join("；")}`
    : result;
  await loadDocuments();
});

async function uploadDocument(file) {
  const suffix = file.name.toLowerCase().split(".").pop();
  if (!["pptx", "md", "txt"].includes(suffix)) throw new Error("不支持这种文件格式");
  const isPresentation = suffix === "pptx";
  if (isPresentation && file.size > 25 * 1024 * 1024) throw new Error("PPTX 不能超过 25MB");
  if (!isPresentation && file.size > 2 * 1024 * 1024) throw new Error("文本资料不能超过 2MB");
  const payload = isPresentation
    ? {filename: file.name, file_data_url: await readFileAsDataUrl(file)}
    : {filename: file.name, content: await file.text()};
  return api(`/api/courses/${state.selectedCourse.id}/documents`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => resolve(reader.result));
    reader.addEventListener("error", () => reject(new Error("没有成功读取文件")));
    reader.readAsDataURL(file);
  });
}
$("#document-list").addEventListener("click", async event => {
  const id = event.target.dataset.deleteDocument;
  if (!id || !window.confirm("删除这份资料？")) return;
  await api(`/api/courses/${state.selectedCourse.id}/documents/${id}`, {method: "DELETE"});
  await loadDocuments();
});

$("#review-open").addEventListener("click", () => $("#review-dialog").showModal());
$("#review-form").addEventListener("submit", async event => {
  event.preventDefault();
  $("#review-message").textContent = "正在读取课程资料并安排第一轮复习…";
  $("#review-result").innerHTML = "";
  try {
    const result = await api(`/api/courses/${state.selectedCourse.id}/review-plans`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({scope: $("#review-scope").value, available_hours: Number($("#review-hours").value), weak_topics: $("#weak-topics").value})});
    if (result.status !== "ready") { $("#review-message").textContent = result.overview; return; }
    $("#review-message").textContent = "";
    state.reviewSession = {citations: result.citations, questions: result.self_test, index: 0};
    $("#review-form").classList.add("hidden");
    renderCoachStep();
  } catch (error) { $("#review-message").textContent = error.message; }
});

function renderCoachStep(feedback = "") {
  const session = state.reviewSession;
  if (!session || session.index >= session.citations.length) {
    $("#review-result").innerHTML = `
      <div class="coach-complete"><span>REVIEW COMPLETE</span><h3>本轮急救复习完成</h3>
      <p>你已经对全部主题做过一次闭卷回忆。现在只回看答不清的部分，然后再进行一轮自测。</p>
      <button class="primary-button" data-review-restart type="button">再复习一轮</button></div>`;
    return;
  }
  const citation = session.citations[session.index];
  const topic = citation.section_title || citation.filename;
  $("#review-result").innerHTML = `
    <div class="coach-progress"><span>第 ${session.index + 1} / ${session.citations.length} 个主题</span><strong>${escapeHtml(topic)}</strong></div>
    <section class="coach-lesson">
      <span>先理解</span>
      <p>${escapeHtml(citation.excerpt)}</p>
      <small>来源：${escapeHtml(citation.filename)}${citation.section_title ? ` · ${escapeHtml(citation.section_title)}` : ""}</small>
    </section>
    <section class="coach-question">
      <span>现在闭卷回答</span>
      <h3>${escapeHtml(session.questions[session.index])}</h3>
      <textarea id="coach-answer" rows="4" placeholder="不要看上面的资料，用自己的话回答…">${escapeHtml(session.lastAnswer || "")}</textarea>
      <button class="primary-button" data-coach-submit type="button">提交回答并纠错</button>
    </section>
    ${feedback ? `<section class="coach-feedback"><span>纠错反馈</span><p>${escapeHtml(feedback)}</p><button class="primary-button" data-coach-next type="button">进入下一个知识点</button></section>` : ""}
  `;
  if (feedback) {
    $("#coach-answer").disabled = true;
    $("[data-coach-submit]").classList.add("hidden");
  }
}

$("#review-result").addEventListener("click", async event => {
  if (event.target.closest("[data-coach-submit]")) {
    const answer = $("#coach-answer").value.trim();
    if (!answer) { $("#review-message").textContent = "请先用自己的话回答，再提交纠错。"; return; }
    const citation = state.reviewSession.citations[state.reviewSession.index];
    const topic = citation.section_title || citation.filename;
    $("#review-message").textContent = "正在根据课程资料检查你的回答…";
    try {
      const result = await api(`/api/courses/${state.selectedCourse.id}/review-coach`, {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({topic, answer})
      });
      state.reviewSession.lastAnswer = answer;
      $("#review-message").textContent = "";
      renderCoachStep(result.feedback);
    } catch (error) { $("#review-message").textContent = error.message; }
  }
  if (event.target.closest("[data-coach-next]")) {
    state.reviewSession.index += 1;
    state.reviewSession.lastAnswer = "";
    renderCoachStep();
  }
  if (event.target.closest("[data-review-restart]")) {
    state.reviewSession.index = 0;
    state.reviewSession.lastAnswer = "";
    renderCoachStep();
  }
});

$$("[data-close]").forEach(button => button.addEventListener("click", () => $(`#${button.dataset.close}`).close()));
$("#menu-button").addEventListener("click", () => { $("#sidebar").classList.add("open"); $("#sidebar-scrim").classList.add("open"); });
$("#sidebar-scrim").addEventListener("click", closeSidebar);

loadCourses().catch(error => { $("#course-list").innerHTML = `<p class="sidebar-empty">${escapeHtml(error.message)}</p>`; });
