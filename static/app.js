// ─── Screen references ────────────────────────────────────────────────────────
const authScreen        = document.getElementById("auth-screen");
const setupScreen       = document.getElementById("setup-screen");
const interviewScreen   = document.getElementById("interview-screen");
const feedbackScreen    = document.getElementById("feedback-screen");
const historyScreen     = document.getElementById("history-screen");
const modelAlert        = document.getElementById("model-alert");

// ─── Auth elements ────────────────────────────────────────────────────────────
const tabLogin          = document.getElementById("tab-login");
const tabRegister       = document.getElementById("tab-register");
const loginFormEl       = document.getElementById("login-form");
const registerFormEl    = document.getElementById("register-form");
const loginBtn          = document.getElementById("login-btn");
const registerBtn       = document.getElementById("register-btn");
const gotoRegister      = document.getElementById("goto-register");
const gotoLogin         = document.getElementById("goto-login");
const authError         = document.getElementById("auth-error");
const logoutBtn         = document.getElementById("logout-btn");

// ─── Setup elements ───────────────────────────────────────────────────────────
const startBtn          = document.getElementById("start-btn");
const showHistoryBtn    = document.getElementById("show-history-btn");
// model-select-alert const modelSelectEl     = document.getElementById("model-select");
const modelSelectEl     = document.getElementById("model-select-alert");
const downloadModelBtn  = document.getElementById("download-model-btn");
const downloadStatus    = document.getElementById("download-status");

// ─── Interview elements ───────────────────────────────────────────────────────
const recordBtn         = document.getElementById("record-btn");
const stopBtn           = document.getElementById("stop-btn");
const sendTextBtn       = document.getElementById("send-text-btn");
const finishBtn         = document.getElementById("finish-btn");
const timerEl           = document.getElementById("timer");
const questionEl        = document.getElementById("question");
const conversationEl    = document.getElementById("conversation");
const headerTitle       = document.getElementById("header-title");

// ─── Feedback / history elements ──────────────────────────────────────────────
const feedbackContentEl        = document.getElementById("feedback-content");
const newInterviewBtn          = document.getElementById("new-interview-btn");
const openHistoryFromFeedback  = document.getElementById("open-history-from-feedback");
const historyListEl            = document.getElementById("history-list");
const historyDetailEl          = document.getElementById("history-detail");
const backBtn                  = document.getElementById("back-btn");
const downloadJsonBtn          = document.getElementById("download-json-btn");
const downloadPdfBtn           = document.getElementById("download-pdf-btn");

// ─── App state ────────────────────────────────────────────────────────────────
let jwtToken          = localStorage.getItem("jwt_token") || "";
let interviewId       = null;
let language          = "es";
let secondsLeft       = 0;
let timerInterval     = null;
let mediaRecorder     = null;
let recordedChunks    = [];
let selectedSessionId = null;

// ─── Utilities ────────────────────────────────────────────────────────────────
function show(screen) {
  [authScreen, setupScreen, interviewScreen, feedbackScreen, historyScreen].forEach(
    (el) => el.classList.add("hidden")
  );
  screen.classList.remove("hidden");
}

function formatTime(s) {
  const m = Math.floor(s / 60).toString().padStart(2, "0");
  return `${m}:${(s % 60).toString().padStart(2, "0")}`;
}

function setTimer(seconds) {
  secondsLeft = seconds;
  timerEl.textContent = `Time left: ${formatTime(secondsLeft)}`;
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = setInterval(() => {
    secondsLeft = Math.max(secondsLeft - 1, 0);
    timerEl.textContent = `Time left: ${formatTime(secondsLeft)}`;
  }, 1000);
}

function addBubble(text, type) {
  const el = document.createElement("div");
  el.className = `bubble ${type}`;
  el.textContent = text;
  conversationEl.appendChild(el);
  conversationEl.scrollTop = conversationEl.scrollHeight;
}

function speak(text) {
  const u = new SpeechSynthesisUtterance(text);
  u.lang = language === "es" ? "es-MX" : "en-US";
  speechSynthesis.speak(u);
}

function showAuthError(msg) {
  authError.textContent = msg;
  authError.classList.remove("hidden");
  setTimeout(() => authError.classList.add("hidden"), 5000);
}

// ─── Authenticated fetch ──────────────────────────────────────────────────────
async function apiFetch(url, options = {}) {
  const headers = new Headers(options.headers || {});
  const controller = new AbortController();
  const timeoutId = setTimeout(() => timeout.abort(), options.timeout || 120000);
  if (jwtToken) headers.set("Authorization", `Bearer ${jwtToken}`);
  const response = await fetch(url, { ...options, headers, signal: controller.signal });
  if (response.status === 401) {
    jwtToken = "";
    localStorage.removeItem("jwt_token");
    show(authScreen);
  }
  clearTimeout(timeoutId);
  return response;
}

// ─── Auth tab toggle ──────────────────────────────────────────────────────────
function showLoginTab() {
  tabLogin.classList.add("active");
  tabRegister.classList.remove("active");
  loginFormEl.classList.remove("hidden");
  registerFormEl.classList.add("hidden");
  authError.classList.add("hidden");
}

function showRegisterTab() {
  tabRegister.classList.add("active");
  tabLogin.classList.remove("active");
  registerFormEl.classList.remove("hidden");
  loginFormEl.classList.add("hidden");
  authError.classList.add("hidden");
}

tabLogin.onclick    = showLoginTab;
tabRegister.onclick = showRegisterTab;
gotoRegister.onclick = (e) => { e.preventDefault(); showRegisterTab(); };
gotoLogin.onclick    = (e) => { e.preventDefault(); showLoginTab(); };

// ─── Login ────────────────────────────────────────────────────────────────────
async function login() {
  const username = document.getElementById("login-user").value.trim();
  const password = document.getElementById("login-pass").value;
  if (!username || !password) { showAuthError("Username and password are required."); return; }

  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    showAuthError(err.detail || "Invalid credentials.");
    return;
  }

  const data = await res.json();
  jwtToken = data.access_token;
  localStorage.setItem("jwt_token", jwtToken);
  afterLogin();
}

// ─── Register ─────────────────────────────────────────────────────────────────
async function register() {
  const username  = document.getElementById("reg-user").value.trim();
  const email     = document.getElementById("reg-email").value.trim();
  const password  = document.getElementById("reg-pass").value;
  const password2 = document.getElementById("reg-pass2").value;

  if (!username || !email || !password) { showAuthError("All fields are required."); return; }
  if (password !== password2)            { showAuthError("Passwords do not match."); return; }
  if (password.length < 8)              { showAuthError("Password must be at least 8 characters."); return; }

  const res = await fetch("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, email, password }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    showAuthError(err.detail || "Registration failed.");
    return;
  }

  const data = await res.json();
  jwtToken = data.access_token;
  localStorage.setItem("jwt_token", jwtToken);
  afterLogin();
}

loginBtn.onclick   = login;
registerBtn.onclick = register;

// ─── After successful login / register ────────────────────────────────────────
async function afterLogin() {
  show(setupScreen);
  await loadModels();
}

// ─── Logout ───────────────────────────────────────────────────────────────────
logoutBtn.onclick = () => {
  jwtToken = "";
  localStorage.removeItem("jwt_token");
  show(authScreen);
  showLoginTab();
};

// ─── Model management ────────────────────────────────────────────────────────
async function loadModels() {
  const res = await apiFetch("/api/models");
  if (!res.ok) return;

  const data = await res.json();
  const models = data.models || [];

  modelSelectEl.innerHTML = "";
  if (models.length === 0) {
    modelSelectEl.innerHTML = '<option value="">No models available</option>';
    modelAlert.classList.remove("hidden");
    return;
  }

  modelAlert.classList.add("hidden");
  models.forEach((m) => {
    const opt = document.createElement("option");
    opt.value = m.name;
    opt.textContent = m.name;
    modelSelectEl.appendChild(opt);
  });
}

downloadModelBtn.onclick = async () => {
  const modelName = document.getElementById("model-select-alert").value;
  if (!modelName) return;

  downloadModelBtn.disabled = true;
  downloadStatus.textContent = `⏳ Downloading ${modelName}…`;

  const res = await apiFetch(`/api/models/download?model_name=${encodeURIComponent(modelName)}`, { method: "POST" });
  if (res.ok) {
    downloadStatus.textContent = `✅ ${modelName} downloaded!`;
    await loadModels();
  } else {
    downloadStatus.textContent = `❌ Download failed.`;
  }
  downloadModelBtn.disabled = false;
};

// ─── Start interview ──────────────────────────────────────────────────────────
async function startInterview() {
  const payload = {
    candidate_name:       document.getElementById("candidate").value.trim(),
    candidate_email:      document.getElementById("candidate-email").value.trim() || null,
    position:             document.getElementById("position").value.trim(),
    position_description: document.getElementById("position-desc").value.trim() || null,
    duration_minutes:     Number(document.getElementById("duration").value),
    language:             document.getElementById("language").value,
    model:                modelSelectEl.value || "qwen3.5",
  };

  if (!payload.candidate_name || !payload.position) {
    alert("Candidate name and position are required.");
    return;
  }

  const res = await apiFetch("/api/interviews/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    timeout: 600000, // 60 seconds timeout for starting the interview
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    alert(err.detail || "Could not start interview.");
    return;
  }

  const data = await res.json();
  interviewId = data.interview_id;
  language = payload.language;
  conversationEl.innerHTML = "";
  questionEl.textContent = data.first_question;
  addBubble(data.first_question, "ai");
  speak(data.first_question);
  headerTitle.textContent = `${payload.candidate_name} — ${payload.position}`;
  setTimer(data.seconds_left);
  show(interviewScreen);
}

startBtn.onclick = startInterview;

// ─── Interview turn ───────────────────────────────────────────────────────────
async function sendTurn({ transcript, audioBlob }) {
  if (!interviewId) return;
  const formData = new FormData();
  if (transcript)  formData.append("transcript", transcript);
  if (audioBlob)   formData.append("audio", audioBlob, "answer.webm");

  const res = await apiFetch(`/api/interviews/${interviewId}/turn`, { method: "POST", body: formData, timeout: 600000 });
  const data = await res.json();
  if (!res.ok) { alert(data.detail || "Could not process turn."); return; }

  addBubble(data.transcript, "user");
  questionEl.textContent = data.next_question;
  addBubble(data.next_question, "ai");
  speak(data.next_question);
  setTimer(data.seconds_left);
}

sendTextBtn.onclick = async () => {
  const ta = document.getElementById("text-answer");
  const text = ta.value.trim();
  if (!text) return;
  ta.value = "";
  await sendTurn({ transcript: text });
};

// ─── Finish interview ─────────────────────────────────────────────────────────
finishBtn.onclick = async () => {
  if (!interviewId) return;
  const res  = await apiFetch(`/api/interviews/${interviewId}/finish`, { method: "POST" });
  const data = await res.json();
  if (!res.ok) { alert(data.detail || "Could not finish interview."); return; }
  if (timerInterval) clearInterval(timerInterval);
  feedbackContentEl.innerHTML = markdownToHtml(data.feedback || "No feedback.");
  show(feedbackScreen);
};

// ─── Simple markdown → HTML (bold, headers, lists) ───────────────────────────
function markdownToHtml(md) {
  return md
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/^#### (.+)$/gm, "<h4>$1</h4>")
    .replace(/^### (.+)$/gm,  "<h3>$1</h3>")
    .replace(/^## (.+)$/gm,   "<h2>$1</h2>")
    .replace(/^# (.+)$/gm,    "<h1>$1</h1>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/^- (.+)$/gm,    "<li>$1</li>")
    .replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>")
    .replace(/\n{2,}/g, "</p><p>")
    .replace(/\n/g, "<br>");
}

// ─── History ──────────────────────────────────────────────────────────────────
async function openHistory() {
  const res = await apiFetch("/api/interviews");
  if (!res.ok) { alert("Could not load history."); return; }
  const data = await res.json();
  const interviews = data.interviews || [];

  historyListEl.innerHTML = "";
  historyDetailEl.innerHTML = "";
  selectedSessionId = null;
  downloadJsonBtn.disabled = true;
  downloadPdfBtn.disabled = true;

  if (interviews.length === 0) {
    historyListEl.textContent = "No interviews yet.";
  } else {
    interviews.forEach((iv) => {
      const btn = document.createElement("button");
      btn.className = "secondary";
      const date = iv.started_at ? new Date(iv.started_at).toLocaleDateString() : "–";
      btn.textContent = `${iv.candidate_name} — ${iv.position} (${iv.language?.toUpperCase()}) · ${date}`;
      btn.onclick = () => loadSessionDetail(iv.id || iv.interview_id);
      historyListEl.appendChild(btn);
    });
  }
  show(historyScreen);
}

async function loadSessionDetail(id) {
  const res  = await apiFetch(`/api/sessions/${id}`);
  const data = await res.json();
  if (!res.ok) { alert(data.detail || "Could not load session."); return; }

  const lines = [
    `Candidate: ${data.candidate_name}`,
    `Position: ${data.position}`,
    `Language: ${data.language?.toUpperCase()}`,
    `Duration: ${data.duration_minutes} min`,
    "",
    "── Transcript ──────────────────────────────────────────",
  ];
  (data.messages || []).forEach((m) => {
    lines.push(`${m.role === "assistant" ? "Interviewer" : "Candidate"}: ${m.content}`);
  });
  lines.push("", "── Feedback ────────────────────────────────────────────");
  lines.push(data.feedback || "No feedback generated.");

  historyDetailEl.textContent = lines.join("\n");
  selectedSessionId = id;
  downloadJsonBtn.disabled = false;
  downloadPdfBtn.disabled = false;
}

async function downloadSession(format) {
  if (!selectedSessionId) return;
  const res = await apiFetch(`/api/sessions/${selectedSessionId}/export/${format}`);
  if (!res.ok) { alert("Could not export session."); return; }
  const blob = await res.blob();
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href     = url;
  a.download = `session-${selectedSessionId}.${format === "json" ? "json" : "pdf"}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// ─── Recording ────────────────────────────────────────────────────────────────
recordBtn.onclick = async () => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);
  recordedChunks = [];
  mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) recordedChunks.push(e.data); };
  mediaRecorder.onstop = async () => {
    const blob = new Blob(recordedChunks, { type: "audio/webm" });
    await sendTurn({ audioBlob: blob });
    stream.getTracks().forEach((t) => t.stop());
  };
  mediaRecorder.start();
  recordBtn.disabled = true;
  stopBtn.disabled   = false;
};

stopBtn.onclick = () => {
  if (!mediaRecorder) return;
  mediaRecorder.stop();
  recordBtn.disabled = false;
  stopBtn.disabled   = true;
};

// ─── Navigation wiring ───────────────────────────────────────────────────────
showHistoryBtn.onclick             = openHistory;
backBtn.onclick                    = () => show(setupScreen);
newInterviewBtn.onclick            = () => { interviewId = null; show(setupScreen); };
openHistoryFromFeedback.onclick    = openHistory;
downloadJsonBtn.onclick            = () => downloadSession("json");
downloadPdfBtn.onclick             = () => downloadSession("pdf");

// ─── Boot ─────────────────────────────────────────────────────────────────────
if (jwtToken) {
  afterLogin();
} else {
  show(authScreen);
}
