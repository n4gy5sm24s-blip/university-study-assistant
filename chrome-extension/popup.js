const API = "http://127.0.0.1:8000";
const courseSelect = document.querySelector("#course");
const status = document.querySelector("#status");
const result = document.querySelector("#result");
const actions = document.querySelector("#actions");
const allowGeneralKnowledge = document.querySelector("#allow-general-knowledge");
let latestDraft = "";

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail || "本地作业机请求失败");
  return body;
}

async function loadCourses() {
  try {
    const courses = await request("/api/courses");
    const saved = await chrome.storage.local.get(["courseId", "allowGeneralKnowledge"]);
    courseSelect.replaceChildren(...courses.map(course => {
      const option = document.createElement("option");
      option.value = course.id;
      option.textContent = course.name;
      return option;
    }));
    if (saved.courseId && courses.some(course => course.id === Number(saved.courseId))) courseSelect.value = saved.courseId;
    allowGeneralKnowledge.checked = saved.allowGeneralKnowledge !== false;
    if (!courses.length) throw new Error("请先在本地作业机创建课程并上传资料");
  } catch (error) {
    status.textContent = `${error.message}。请确认 http://127.0.0.1:8000 正在运行。`;
    document.querySelector("#analyze").disabled = true;
  }
}

async function readCurrentPage() {
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  if (!tab?.id) throw new Error("没有找到当前标签页");
  const frames = await chrome.scripting.executeScript({
    target: {tabId: tab.id, allFrames: true},
    func: () => ({
      title: document.title,
      selected: window.getSelection()?.toString().trim() || "",
      visible: document.body?.innerText?.trim() || ""
    })
  });
  const values = frames.map(item => item.result).filter(Boolean);
  const selected = values.map(item => item.selected).filter(Boolean).join("\n");
  const visible = values.map(item => item.visible).filter(Boolean).join("\n");
  const text = (selected || visible).replace(/\n{3,}/g, "\n\n").slice(0, 4500);
  if (text.length < 3) throw new Error("没有读到题目文字。若页面使用图片或画布，请先选中文字，或把截图拖入作业机");
  return `网页标题：${values[0]?.title || tab.title || "当前作业页面"}\n\n页面中的作业内容：\n${text}`;
}

document.querySelector("#analyze").addEventListener("click", async () => {
  status.textContent = "正在读取当前页面并检索课程资料…";
  result.hidden = true;
  actions.hidden = true;
  try {
    const question = await readCurrentPage();
    const courseId = Number(courseSelect.value);
    await chrome.storage.local.set({courseId, allowGeneralKnowledge: allowGeneralKnowledge.checked});
    const response = await request(`/api/courses/${courseId}/homework-guidance`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        question,
        mode: "draft",
        allow_general_knowledge: allowGeneralKnowledge.checked
      })
    });
    latestDraft = response.guidance;
    result.textContent = latestDraft;
    result.hidden = false;
    actions.hidden = false;
    if (response.grounding_status === "grounded") {
      status.textContent = `已生成，引用 ${response.citations.length} 条课程依据。`;
    } else if (response.grounding_status === "general_knowledge") {
      status.textContent = "已使用 AI 通用知识生成，未使用课程资料。";
    } else {
      status.textContent = allowGeneralKnowledge.checked
        ? "未成功使用通用知识，请检查 AI 模型配置。"
        : "课程资料不足，请补充相关页面或允许通用知识。";
    }
  } catch (error) {
    status.textContent = error.message;
  }
});

document.querySelector("#copy").addEventListener("click", async () => {
  await navigator.clipboard.writeText(latestDraft);
  status.textContent = "草稿已复制。请在提交前检查和修改。";
});
document.querySelector("#open").addEventListener("click", () => chrome.tabs.create({url: `${API}/`}));
courseSelect.addEventListener("change", () => chrome.storage.local.set({courseId: Number(courseSelect.value)}));
allowGeneralKnowledge.addEventListener("change", () => chrome.storage.local.set({allowGeneralKnowledge: allowGeneralKnowledge.checked}));
loadCourses();
