const form = document.querySelector("#course-form");
const list = document.querySelector("#course-list");
const message = document.querySelector("#form-message");
const refresh = document.querySelector("#refresh");
const materialsPanel = document.querySelector("#materials-panel");
const selectedCourseTitle = document.querySelector("#selected-course");
const documentForm = document.querySelector("#document-form");
const documentFile = document.querySelector("#document-file");
const documentList = document.querySelector("#document-list");
const documentMessage = document.querySelector("#document-message");
const closeMaterials = document.querySelector("#close-materials");
const searchForm = document.querySelector("#search-form");
const searchQuery = document.querySelector("#search-query");
const searchMessage = document.querySelector("#search-message");
const searchResults = document.querySelector("#search-results");
const questionForm = document.querySelector("#question-form");
const questionInput = document.querySelector("#question-input");
const questionMessage = document.querySelector("#question-message");
const answerCard = document.querySelector("#answer-card");
const homeworkForm = document.querySelector("#homework-form");
const homeworkMode = document.querySelector("#homework-mode");
const homeworkQuestion = document.querySelector("#homework-question");
const studentAttempt = document.querySelector("#student-attempt");
const homeworkMessage = document.querySelector("#homework-message");
const homeworkCard = document.querySelector("#homework-card");
const reviewForm = document.querySelector("#review-form");
const reviewScope = document.querySelector("#review-scope");
const reviewHours = document.querySelector("#review-hours");
const weakTopics = document.querySelector("#weak-topics");
const reviewMessage = document.querySelector("#review-message");
const reviewCard = document.querySelector("#review-card");
let selectedCourse = null;

function escapeHtml(value) {
  const element = document.createElement("div");
  element.textContent = value;
  return element.innerHTML;
}

async function loadCourses() {
  list.innerHTML = '<p class="empty">正在读取课程……</p>';
  const response = await fetch("/api/courses");
  const courses = await response.json();
  if (!courses.length) {
    list.innerHTML = '<p class="empty">还没有课程。先创建第一门课程吧。</p>';
    return;
  }
  list.innerHTML = courses.map(course => `
    <article class="course-card">
      <h3>${escapeHtml(course.name)}</h3>
      <p>${escapeHtml(course.description || "暂时没有说明")}</p>
      <button class="secondary" data-open="${course.id}" data-name="${escapeHtml(course.name)}">管理资料</button>
      <button class="danger" data-delete="${course.id}">删除课程</button>
    </article>
  `).join("");
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  message.textContent = "正在创建……";
  const response = await fetch("/api/courses", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      name: form.name.value,
      description: form.description.value
    })
  });
  if (!response.ok) {
    const error = await response.json();
    message.textContent = error.detail || "创建失败";
    return;
  }
  form.reset();
  message.textContent = "课程已创建";
  await loadCourses();
});

list.addEventListener("click", async event => {
  const openId = event.target.dataset.open;
  if (openId) {
    selectedCourse = Number(openId);
    selectedCourseTitle.textContent = `${event.target.dataset.name} · 课程资料`;
    materialsPanel.classList.remove("hidden");
    await loadDocuments();
    return;
  }
  const courseId = event.target.dataset.delete;
  if (!courseId) return;
  if (!window.confirm("确定删除这门课程吗？")) return;
  const response = await fetch(`/api/courses/${courseId}`, {method: "DELETE"});
  if (!response.ok) {
    window.alert("删除失败，请刷新后重试。");
    return;
  }
  await loadCourses();
});

async function loadDocuments() {
  if (!selectedCourse) return;
  documentList.innerHTML = '<p class="empty">正在读取资料……</p>';
  const response = await fetch(`/api/courses/${selectedCourse}/documents`);
  const documents = await response.json();
  if (!documents.length) {
    documentList.innerHTML = '<p class="empty">还没有资料。可先上传自制的 TXT 或 Markdown 文件。</p>';
    return;
  }
  documentList.innerHTML = documents.map(document => `
    <div class="document-row">
      <div>
        <strong>${escapeHtml(document.filename)}</strong>
        <div class="document-meta">${document.status} · ${document.size_bytes} bytes</div>
      </div>
      <button class="danger" data-document-delete="${document.id}">删除</button>
    </div>
  `).join("");
}

documentForm.addEventListener("submit", async event => {
  event.preventDefault();
  const file = documentFile.files[0];
  if (!file || !selectedCourse) return;
  documentMessage.textContent = "正在读取并上传……";
  const content = await file.text();
  const response = await fetch(`/api/courses/${selectedCourse}/documents`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({filename: file.name, content})
  });
  const result = response.status === 204 ? null : await response.json();
  if (!response.ok) {
    documentMessage.textContent = result.detail || "上传失败";
    return;
  }
  documentForm.reset();
  documentMessage.textContent = "资料已上传并完成文字解析";
  await loadDocuments();
});

documentList.addEventListener("click", async event => {
  const documentId = event.target.dataset.documentDelete;
  if (!documentId || !selectedCourse) return;
  if (!window.confirm("确定删除这份资料吗？")) return;
  const response = await fetch(
    `/api/courses/${selectedCourse}/documents/${documentId}`,
    {method: "DELETE"}
  );
  if (!response.ok) {
    documentMessage.textContent = "删除失败";
    return;
  }
  documentMessage.textContent = "资料已删除";
  await loadDocuments();
});

searchForm.addEventListener("submit", async event => {
  event.preventDefault();
  if (!selectedCourse) return;
  searchMessage.textContent = "正在搜索……";
  searchResults.innerHTML = "";
  const response = await fetch(
    `/api/courses/${selectedCourse}/search?q=${encodeURIComponent(searchQuery.value)}`
  );
  const results = await response.json();
  if (!response.ok) {
    searchMessage.textContent = results.detail || "搜索失败";
    return;
  }
  if (!results.length) {
    searchMessage.textContent = "这门课程的资料中没有找到相关内容。";
    return;
  }
  searchMessage.textContent = `找到 ${results.length} 条相关片段`;
  searchResults.innerHTML = results.map(result => `
    <article class="document-row">
      <div>
        <strong>${escapeHtml(result.filename)}${result.section_title ? ` · ${escapeHtml(result.section_title)}` : ""}</strong>
        <p>${escapeHtml(result.content)}</p>
        <div class="document-meta">片段 ${result.sequence + 1}</div>
      </div>
    </article>
  `).join("");
});

questionForm.addEventListener("submit", async event => {
  event.preventDefault();
  if (!selectedCourse) return;
  questionMessage.textContent = "正在课程资料中查找依据……";
  answerCard.classList.add("hidden");
  const response = await fetch(`/api/courses/${selectedCourse}/questions`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({question: questionInput.value})
  });
  const result = await response.json();
  if (!response.ok) {
    questionMessage.textContent = result.detail || "提问失败";
    return;
  }
  questionMessage.textContent = result.grounding_status === "grounded"
    ? "已找到资料依据"
    : "资料依据不足";
  const citations = result.citations.map(citation => `
    <li><strong>[${citation.number}] ${escapeHtml(citation.filename)}</strong>${citation.section_title ? ` · ${escapeHtml(citation.section_title)}` : ""} · 片段 ${citation.sequence + 1}</li>
  `).join("");
  answerCard.innerHTML = `
    <h3>回答</h3>
    <p>${escapeHtml(result.answer).replaceAll("\n", "<br>")}</p>
    ${citations ? `<h4>资料来源</h4><ol>${citations}</ol>` : ""}
    <div class="document-meta">生成方式：${result.generation_method === "openai_responses" ? "生成模型讲解" : result.generation_method === "extractive_fallback" ? "模型不可用，已退回原文依据" : result.generation_method === "extractive" ? "原文依据整理" : "未生成"}</div>
  `;
  answerCard.classList.remove("hidden");
});

homeworkForm.addEventListener("submit", async event => {
  event.preventDefault();
  if (!selectedCourse) return;
  homeworkMessage.textContent = "正在课程资料中寻找作业依据……";
  homeworkCard.classList.add("hidden");
  const response = await fetch(`/api/courses/${selectedCourse}/homework-guidance`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      question: homeworkQuestion.value,
      mode: homeworkMode.value,
      student_attempt: studentAttempt.value
    })
  });
  const result = await response.json();
  if (!response.ok) {
    homeworkMessage.textContent = result.detail || "辅导请求失败";
    return;
  }
  homeworkMessage.textContent = result.grounding_status === "grounded"
    ? "已根据课程资料生成辅导"
    : "课程资料依据不足";
  const citations = result.citations.map(citation => `
    <li><strong>[${citation.number}] ${escapeHtml(citation.filename)}</strong>${citation.section_title ? ` · ${escapeHtml(citation.section_title)}` : ""} · 片段 ${citation.sequence + 1}</li>
  `).join("");
  homeworkCard.innerHTML = `
    <h3>辅导建议</h3>
    <p>${escapeHtml(result.guidance).replaceAll("\n", "<br>")}</p>
    ${citations ? `<h4>课程依据</h4><ol>${citations}</ol>` : ""}
  `;
  homeworkCard.classList.remove("hidden");
});

reviewForm.addEventListener("submit", async event => {
  event.preventDefault();
  if (!selectedCourse) return;
  reviewMessage.textContent = "正在根据课程资料安排复习……";
  reviewCard.classList.add("hidden");
  const response = await fetch(`/api/courses/${selectedCourse}/review-plans`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      scope: reviewScope.value,
      available_hours: Number(reviewHours.value),
      weak_topics: weakTopics.value
    })
  });
  const result = await response.json();
  if (!response.ok) {
    reviewMessage.textContent = result.detail || "计划生成失败";
    return;
  }
  if (result.status !== "ready") {
    reviewMessage.textContent = result.overview;
    return;
  }
  reviewMessage.textContent = `已安排 ${result.total_minutes} 分钟`;
  const blocks = result.blocks.map(block => `
    <li><strong>${block.minutes} 分钟 · ${escapeHtml(block.topic)}</strong><br>${escapeHtml(block.activity)}${block.citation_number ? ` [${block.citation_number}]` : ""}</li>
  `).join("");
  const tests = result.self_test.map(question => `<li>${escapeHtml(question)}</li>`).join("");
  const assumptions = result.assumptions.map(item => `<li>${escapeHtml(item)}</li>`).join("");
  reviewCard.innerHTML = `
    <h3>紧急复习计划</h3>
    <p>${escapeHtml(result.overview)}</p>
    <ol>${blocks}</ol>
    <h4>闭卷自测</h4><ul>${tests}</ul>
    <h4>计划依据与限制</h4><ul>${assumptions}</ul>
  `;
  reviewCard.classList.remove("hidden");
});

closeMaterials.addEventListener("click", () => {
  materialsPanel.classList.add("hidden");
  selectedCourse = null;
  documentMessage.textContent = "";
  searchForm.reset();
  searchMessage.textContent = "";
  searchResults.innerHTML = "";
  questionForm.reset();
  questionMessage.textContent = "";
  answerCard.innerHTML = "";
  answerCard.classList.add("hidden");
  homeworkForm.reset();
  homeworkMessage.textContent = "";
  homeworkCard.innerHTML = "";
  homeworkCard.classList.add("hidden");
  reviewForm.reset();
  reviewMessage.textContent = "";
  reviewCard.innerHTML = "";
  reviewCard.classList.add("hidden");
});

refresh.addEventListener("click", loadCourses);
loadCourses();
