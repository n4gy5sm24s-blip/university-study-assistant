const API = "http://127.0.0.1:8000";
const courseSelect = document.querySelector("#course");
const status = document.querySelector("#status");
const result = document.querySelector("#result");
const actions = document.querySelector("#actions");
const followUpForm = document.querySelector("#follow-up-form");
const followUpInput = document.querySelector("#follow-up");
const allowGeneralKnowledge = document.querySelector("#allow-general-knowledge");
let latestDraft = "";
let conversation = [];
let currentTab = null;

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  if (!tab?.id) throw new Error("没有找到当前标签页");
  currentTab = tab;
  return tab;
}

function chatSessionKey(tabId, courseId) {
  return `chatSession:${tabId}:${courseId}`;
}

function hideConversation() {
  latestDraft = "";
  conversation = [];
  result.replaceChildren();
  result.hidden = true;
  followUpForm.hidden = true;
  actions.hidden = true;
}

async function saveConversation() {
  const tab = currentTab || await getActiveTab();
  const courseId = Number(courseSelect.value);
  const key = chatSessionKey(tab.id, courseId);
  await chrome.storage.local.set({
    [key]: {
      url: tab.url || "",
      conversation: conversation.slice(-6),
      latestDraft,
      updatedAt: Date.now()
    }
  });
}

async function restoreConversation() {
  hideConversation();
  const tab = await getActiveTab();
  const courseId = Number(courseSelect.value);
  if (!courseId) return;
  const key = chatSessionKey(tab.id, courseId);
  const saved = await chrome.storage.local.get(key);
  const session = saved[key];
  if (!session || session.url !== (tab.url || "") || !Array.isArray(session.conversation) || !session.conversation.length) return;
  conversation = session.conversation.slice(-6);
  latestDraft = session.latestDraft || conversation.filter(item => item.role === "assistant").at(-1)?.content || "";
  renderConversation();
  result.hidden = false;
  followUpForm.hidden = false;
  actions.hidden = false;
  status.textContent = "已恢复这个网页上一次的问答记录。";
}

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
    await restoreConversation();
  } catch (error) {
    status.textContent = `${error.message}。请确认 http://127.0.0.1:8000 正在运行。`;
    document.querySelector("#analyze").disabled = true;
  }
}

async function readCurrentPage() {
  const tab = await getActiveTab();
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

function renderConversation() {
  result.replaceChildren(...conversation.map(message => {
    const section = document.createElement("section");
    const label = document.createElement("strong");
    label.textContent = message.role === "user" ? "你的追问" : "Coursework AI";
    const content = document.createElement("div");
    content.textContent = message.content;
    section.append(label, content);
    return section;
  }));
  result.scrollTop = result.scrollHeight;
}

async function generate(question, history = []) {
  const courseId = Number(courseSelect.value);
  return request(`/api/courses/${courseId}/homework-guidance`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      question,
      mode: "draft",
      allow_general_knowledge: allowGeneralKnowledge.checked,
      history: history.slice(-6)
    })
  });
}

function showGenerationStatus(response) {
  if (response.grounding_status === "grounded") {
    status.textContent = `已生成，引用 ${response.citations.length} 条课程依据。`;
  } else if (response.grounding_status === "general_knowledge") {
    status.textContent = "已使用 AI 通用知识生成，未使用课程资料。";
  } else {
    status.textContent = allowGeneralKnowledge.checked
      ? "未成功使用通用知识，请检查 AI 模型配置。"
      : "课程资料不足，请补充相关页面或允许通用知识。";
  }
}

document.querySelector("#analyze").addEventListener("click", async () => {
  status.textContent = "正在读取当前页面并检索课程资料…";
  result.hidden = true;
  actions.hidden = true;
  try {
    const question = await readCurrentPage();
    const courseId = Number(courseSelect.value);
    await chrome.storage.local.set({courseId, allowGeneralKnowledge: allowGeneralKnowledge.checked});
    const response = await generate(question);
    latestDraft = response.guidance;
    conversation = [
      {role: "user", content: "请根据当前网页完成这道作业。"},
      {role: "assistant", content: latestDraft}
    ];
    renderConversation();
    result.hidden = false;
    followUpForm.hidden = false;
    actions.hidden = false;
    showGenerationStatus(response);
    await saveConversation();
  } catch (error) {
    status.textContent = error.message;
  }
});

followUpForm.addEventListener("submit", async event => {
  event.preventDefault();
  const question = followUpInput.value.trim();
  if (!question) return;
  const history = conversation.slice(-6);
  conversation.push({role: "user", content: question});
  renderConversation();
  followUpInput.value = "";
  document.querySelector("#follow-up-send").disabled = true;
  status.textContent = "正在继续回答…";
  try {
    const response = await generate(question, history);
    latestDraft = response.guidance;
    conversation.push({role: "assistant", content: latestDraft});
    conversation = conversation.slice(-6);
    renderConversation();
    showGenerationStatus(response);
    await saveConversation();
  } catch (error) {
    status.textContent = error.message;
  } finally {
    document.querySelector("#follow-up-send").disabled = false;
    followUpInput.focus();
  }
});

document.querySelector("#copy").addEventListener("click", async () => {
  await navigator.clipboard.writeText(latestDraft);
  status.textContent = "草稿已复制。请在提交前检查和修改。";
});
document.querySelector("#open").addEventListener("click", () => chrome.tabs.create({url: `${API}/`}));
courseSelect.addEventListener("change", async () => {
  await chrome.storage.local.set({courseId: Number(courseSelect.value)});
  await restoreConversation();
});
allowGeneralKnowledge.addEventListener("change", () => chrome.storage.local.set({allowGeneralKnowledge: allowGeneralKnowledge.checked}));
loadCourses();
