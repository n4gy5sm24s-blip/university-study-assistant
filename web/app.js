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

closeMaterials.addEventListener("click", () => {
  materialsPanel.classList.add("hidden");
  selectedCourse = null;
  documentMessage.textContent = "";
});

refresh.addEventListener("click", loadCourses);
loadCourses();
