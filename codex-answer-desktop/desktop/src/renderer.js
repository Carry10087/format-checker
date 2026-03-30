const healthBadge = document.getElementById("healthBadge");
const statusText = document.getElementById("statusText");
const runButton = document.getElementById("runButton");
const newSessionButton = document.getElementById("newSessionButton");
const queryInput = document.getElementById("queryInput");
const modelSelect = document.getElementById("modelSelect");
const reasoningSelect = document.getElementById("reasoningSelect");
const webEnabled = document.getElementById("webEnabled");
const localKbEnabled = document.getElementById("localKbEnabled");
const debugEnabled = document.getElementById("debugEnabled");
const historyMeta = document.getElementById("historyMeta");
const historyContainer = document.getElementById("history");
const resultMeta = document.getElementById("resultMeta");
const resultSummary = document.getElementById("resultSummary");
const toggleViewButton = document.getElementById("toggleViewButton");
const saveEditButton = document.getElementById("saveEditButton");
const copyResultButton = document.getElementById("copyResultButton");
const translateButton = document.getElementById("translateButton");
const copyTranslationButton = document.getElementById("copyTranslationButton");
const answerModeText = document.getElementById("answerModeText");
const resultPreview = document.getElementById("resultPreview");
const resultEditor = document.getElementById("resultEditor");
const translationSection = document.getElementById("translationSection");
const translationMeta = document.getElementById("translationMeta");
const translationOutput = document.getElementById("translationOutput");
const debugPanel = document.getElementById("debugPanel");
const debugOutput = document.getElementById("debugOutput");

const TEXT = {
  connected: "\u5df2\u8fde\u63a5",
  ready: "\u5df2\u5c31\u7eea",
  emptyContent: "\u6682\u65e0\u5185\u5bb9\u3002",
  tokenUnknown: "Token\uff1a\u672a\u8fd4\u56de",
  copyFailed: "\u590d\u5236\u5931\u8d25\uff0c\u8bf7\u68c0\u67e5\u7cfb\u7edf\u526a\u8d34\u677f\u6743\u9650\u3002",
  summaryPlaceholder: "\u8fd0\u884c\u4e00\u6b21\u67e5\u8be2\u540e\uff0c\u8fd9\u91cc\u4f1a\u663e\u793a\u6a21\u578b\u3001\u6765\u6e90\u6570\u548c token \u7528\u91cf\u3002",
  modelLabel: "\u6a21\u578b\uff1a",
  reasoningLabel: "\u63a8\u7406\uff1a",
  sourceLabel: "\u6765\u6e90\uff1a",
  citationLabel: "\u5f15\u7528\uff1a",
  translationLabel: "\u7ffb\u8bd1\uff1a\u5df2\u751f\u6210",
  yes: "\u6709",
  no: "\u65e0",
  translationPending: "\u5c1a\u672a\u751f\u6210",
  translationPlaceholder: "\u70b9\u51fb\u201c\u7ffb\u8bd1\u6210\u4e2d\u6587\u201d\u540e\uff0c\u8fd9\u91cc\u4f1a\u663e\u793a\u4e2d\u6587\u7248\u672c\u3002",
  loadedAt: "\u5df2\u8f7d\u5165",
  sessionSuffix: "\u7684\u4f1a\u8bdd",
  loadedHistory: "\u5df2\u8f7d\u5165\u5386\u53f2\u4f1a\u8bdd\uff1a",
  noResultYet: "\u6682\u65f6\u8fd8\u6ca1\u6709\u7ed3\u679c\u3002",
  resultPlaceholder: "\u8fd0\u884c\u4e00\u6b21\u67e5\u8be2\u540e\uff0c\u8fd9\u91cc\u4f1a\u663e\u793a\u7b54\u6848\u3002",
  noHistory: "\u8fd8\u6ca1\u6709\u8fd0\u884c\u8bb0\u5f55\u3002",
  historyEmptyMeta: "\u8fd8\u6ca1\u6709\u5386\u53f2\u8bb0\u5f55\u3002",
  historyCountSuffix: "\u6761\u5386\u53f2\u8bb0\u5f55",
  sourceCountSuffix: "\u4e2a\u6765\u6e90",
  translated: "\u5df2\u7ffb\u8bd1",
  original: "\u539f\u6587",
  backendOffline: "\u540e\u7aef\u672a\u8fde\u63a5",
  savingAnswer: "\u6b63\u5728\u4fdd\u5b58\u7f16\u8f91\u540e\u7684\u7b54\u6848...",
  savedAnswer: "\u5df2\u4fdd\u5b58\u7f16\u8f91\u540e\u7684\u7b54\u6848\u3002",
  deletingSession: "\u6b63\u5728\u5220\u9664\u4f1a\u8bdd...",
  deletedCurrent: "\u5df2\u5220\u9664\u5f53\u524d\u4f1a\u8bdd\uff0c\u5df2\u5207\u6362\u5230\u65b0\u4f1a\u8bdd\u3002",
  deletedSession: "\u4f1a\u8bdd\u5df2\u5220\u9664\u3002",
  noAnswerToTranslate: "\u5f53\u524d\u6ca1\u6709\u53ef\u7ffb\u8bd1\u7684\u7b54\u6848\u5185\u5bb9\u3002",
  translating: "\u6b63\u5728\u751f\u6210\u4e2d\u6587\u7ffb\u8bd1...",
  translatedDone: "\u4e2d\u6587\u7ffb\u8bd1\u5df2\u751f\u6210\u3002",
  translatingButton: "\u7ffb\u8bd1\u4e2d...",
  translateButton: "\u7ffb\u8bd1\u6210\u4e2d\u6587",
  inputRequired: "\u8bf7\u8f93\u5165\u95ee\u9898\u3002",
  inputRequiredBody: "\u8bf7\u8f93\u5165\u95ee\u9898\u540e\u518d\u8fd0\u884c\u3002",
  runningStatus: "\u6b63\u5728\u68c0\u7d22\u8d44\u6599\u5e76\u751f\u6210\u7b54\u6848\uff0c\u8bf7\u7a0d\u7b49...",
  runningMeta: "\u6b63\u5728\u8fd0\u884c...",
  runningSummary: "\u7cfb\u7edf\u6b63\u5728\u6536\u96c6\u6765\u6e90\u3001\u6574\u7406\u89c4\u5219\u5e76\u8bf7\u6c42\u6a21\u578b\u3002",
  generatingAnswer: "\u6b63\u5728\u751f\u6210\u7b54\u6848...",
  answerReady: "\u7b54\u6848\u5df2\u751f\u6210\uff0c\u53ef\u4ee5\u7ee7\u7eed\u7f16\u8f91\u3001\u590d\u5236\u6216\u7ffb\u8bd1\u3002",
  runFailed: "\u8fd0\u884c\u5931\u8d25",
  runFailedSummary: "\u672c\u6b21\u8fd0\u884c\u672a\u80fd\u5b8c\u6210\u3002",
  newSessionReady: "\u5df2\u521b\u5efa\u65b0\u4f1a\u8bdd\uff0c\u8bf7\u8f93\u5165\u65b0\u7684\u95ee\u9898\u3002",
  copiedAnswer: "\u5df2\u590d\u5236\u7b54\u6848",
  copiedTranslation: "\u5df2\u590d\u5236\u7ffb\u8bd1",
  previewMode: "\u9884\u89c8\u6a21\u5f0f",
  editMode: "\u7f16\u8f91\u6a21\u5f0f",
  switchToEdit: "\u5207\u6362\u5230\u7f16\u8f91",
  switchToPreview: "\u5207\u6362\u5230\u9884\u89c8",
  untitledQuestion: "\u672a\u547d\u540d\u95ee\u9898",
  preparingSession: "\u51c6\u5907\u5c31\u7eea\uff0c\u53ef\u4ee5\u5f00\u59cb\u4e00\u6b21\u65b0\u4f1a\u8bdd\u3002",
  deleteTitle: "\u5220\u9664\u4f1a\u8bdd",
  configSaved: "\u5df2\u4fdd\u5b58\u6a21\u578b\u548c\u63a8\u7406\u5f3a\u5ea6\u8bbe\u7f6e\u3002",
  configLoadFailed: "\u65e0\u6cd5\u8bfb\u53d6\u6a21\u578b\u914d\u7f6e\uff0c\u5c06\u4f7f\u7528\u9ed8\u8ba4\u503c\u3002",
  configSaveFailed: "\u4fdd\u5b58\u6a21\u578b\u8bbe\u7f6e\u5931\u8d25\u3002"
};

const MODEL_PRESETS = [
  { value: "gpt-5.4", efforts: ["none", "low", "medium", "high", "xhigh"] },
  { value: "gpt-5.3-codex", efforts: ["low", "medium", "high", "xhigh"] },
  { value: "gpt-5.2-codex", efforts: ["low", "medium", "high", "xhigh"] },
  { value: "gpt-5.2", efforts: ["low", "medium", "high", "xhigh"] },
  { value: "gpt-5.1", efforts: ["none", "low", "medium", "high"] },
  { value: "gpt-5", efforts: ["minimal", "low", "medium", "high"] }
];

const REASONING_LABELS = {
  none: "\u4e0d\u63a8\u7406",
  minimal: "\u6700\u4f4e",
  low: "\u4f4e",
  medium: "\u4e2d",
  high: "\u9ad8",
  xhigh: "\u6700\u9ad8"
};

const DEFAULT_MODEL = "gpt-5";

const state = {
  history: [],
  activeRunId: null,
  currentItem: null,
  config: null,
  answerMode: "preview",
  running: false,
  translating: false,
  saving: false,
  deletingRunId: null
};

function translateHealth(status) {
  if (!status) {
    return TEXT.connected;
  }
  if (String(status).toLowerCase() === "ready") {
    return TEXT.ready;
  }
  return status;
}

function setHealth(ok, text) {
  healthBadge.textContent = text;
  healthBadge.className = `badge ${ok ? "badge-ok" : "badge-warn"}`;
}

function setStatus(text, tone = "muted") {
  statusText.textContent = text;
  statusText.className = `status-text ${tone}`;
}

function formatDateTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value || "";
  }

  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function safeUrl(url) {
  const value = String(url || "").trim();
  if (!value) {
    return "#";
  }
  if (value.startsWith("#")) {
    return value;
  }
  if (/^https?:\/\//i.test(value)) {
    return value;
  }
  return "#";
}

function renderInline(text) {
  let html = escapeHtml(text);
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, label, url) => {
    const href = safeUrl(url);
    const target = href === "#" ? "" : ' target="_blank" rel="noreferrer"';
    return `<a href="${href}"${target}>${label}</a>`;
  });
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  return html;
}

function renderMarkdown(markdown) {
  const text = String(markdown || "").trim();
  if (!text) {
    return `<p class="muted">${TEXT.emptyContent}</p>`;
  }

  const codeBlocks = [];
  const withPlaceholders = text.replace(/```([\s\S]*?)```/g, (_, code) => {
    const token = `@@CODEBLOCK_${codeBlocks.length}@@`;
    codeBlocks.push(`<pre><code>${escapeHtml(code.trim())}</code></pre>`);
    return token;
  });

  const lines = withPlaceholders.split(/\r?\n/);
  const htmlParts = [];
  let paragraph = [];
  let listItems = [];
  let listType = null;

  function flushParagraph() {
    if (!paragraph.length) {
      return;
    }
    htmlParts.push(`<p>${renderInline(paragraph.join(" "))}</p>`);
    paragraph = [];
  }

  function flushList() {
    if (!listItems.length || !listType) {
      return;
    }
    const tag = listType === "ol" ? "ol" : "ul";
    htmlParts.push(`<${tag}>${listItems.map((item) => `<li>${renderInline(item)}</li>`).join("")}</${tag}>`);
    listItems = [];
    listType = null;
  }

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (!line) {
      flushParagraph();
      flushList();
      continue;
    }

    if (/^@@CODEBLOCK_\d+@@$/.test(line)) {
      flushParagraph();
      flushList();
      htmlParts.push(line);
      continue;
    }

    const headingMatch = line.match(/^(#{1,4})\s+(.*)$/);
    if (headingMatch) {
      flushParagraph();
      flushList();
      const level = headingMatch[1].length;
      htmlParts.push(`<h${level}>${renderInline(headingMatch[2])}</h${level}>`);
      continue;
    }

    const unorderedMatch = line.match(/^[-*]\s+(.*)$/);
    if (unorderedMatch) {
      flushParagraph();
      if (listType && listType !== "ul") {
        flushList();
      }
      listType = "ul";
      listItems.push(unorderedMatch[1]);
      continue;
    }

    const orderedMatch = line.match(/^\d+\.\s+(.*)$/);
    if (orderedMatch) {
      flushParagraph();
      if (listType && listType !== "ol") {
        flushList();
      }
      listType = "ol";
      listItems.push(orderedMatch[1]);
      continue;
    }

    flushList();
    paragraph.push(line);
  }

  flushParagraph();
  flushList();

  let html = htmlParts.join("");
  codeBlocks.forEach((block, index) => {
    html = html.replace(`@@CODEBLOCK_${index}@@`, block);
  });
  return html;
}

function formatTokenUsage(usage) {
  const tokenUsage = usage || {};
  const total = tokenUsage.total_tokens || 0;
  if (!total) {
    return TEXT.tokenUnknown;
  }
  return `Token\uff1a${total}\uff08\u8f93\u5165 ${tokenUsage.prompt_tokens || 0} / \u8f93\u51fa ${tokenUsage.completion_tokens || 0}\uff09`;
}

function getModelPreset(model) {
  return MODEL_PRESETS.find((item) => item.value === model) || MODEL_PRESETS[0];
}

function getCurrentReasoningOptions(model) {
  return getModelPreset(model).efforts;
}

function formatReasoningLabel(value) {
  return `${value} \u00b7 ${REASONING_LABELS[value] || value}`;
}

function populateModelSelect(selectedModel) {
  modelSelect.innerHTML = "";
  for (const item of MODEL_PRESETS) {
    const option = document.createElement("option");
    option.value = item.value;
    option.textContent = item.value;
    option.selected = item.value === selectedModel;
    modelSelect.appendChild(option);
  }
}

function populateReasoningSelect(selectedModel, selectedReasoningEffort) {
  const options = getCurrentReasoningOptions(selectedModel);
  const nextReasoningEffort = options.includes(selectedReasoningEffort) ? selectedReasoningEffort : options[0];
  reasoningSelect.innerHTML = "";

  for (const value of options) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = formatReasoningLabel(value);
    option.selected = value === nextReasoningEffort;
    reasoningSelect.appendChild(option);
  }

  return nextReasoningEffort;
}

function playNotification(kind = "success") {
  try {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) {
      return;
    }

    const audio = new AudioContextClass();
    const oscillator = audio.createOscillator();
    const gain = audio.createGain();
    oscillator.connect(gain);
    gain.connect(audio.destination);

    const now = audio.currentTime;
    oscillator.type = kind === "error" ? "sawtooth" : "sine";
    oscillator.frequency.setValueAtTime(kind === "error" ? 220 : 660, now);
    if (kind === "success") {
      oscillator.frequency.exponentialRampToValueAtTime(880, now + 0.18);
    }
    gain.gain.setValueAtTime(0.001, now);
    gain.gain.exponentialRampToValueAtTime(0.08, now + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.28);
    oscillator.start(now);
    oscillator.stop(now + 0.3);
    oscillator.onended = () => audio.close();
  } catch {
    // Ignore sound failures.
  }
}

async function copyText(text, successLabel, button) {
  try {
    await navigator.clipboard.writeText(text || "");
    const original = button.textContent;
    button.textContent = successLabel;
    setTimeout(() => {
      button.textContent = original;
    }, 1500);
  } catch {
    setStatus(TEXT.copyFailed);
  }
}

function getCurrentAnswerText() {
  const draft = resultEditor.value.trim();
  if (draft) {
    return draft;
  }
  return state.currentItem?.final_answer || "";
}

function getCurrentConfig() {
  if (!state.config) {
    return {
      api_url: "",
      model: DEFAULT_MODEL,
      reasoning_effort: getCurrentReasoningOptions(DEFAULT_MODEL)[0],
      skill_path: "",
      local_kb_roots: []
    };
  }

  return {
    ...state.config,
    model: modelSelect.value || state.config.model,
    reasoning_effort: reasoningSelect.value || state.config.reasoning_effort
  };
}

function syncCurrentItem(partial) {
  if (!state.currentItem) {
    return;
  }

  state.currentItem = { ...state.currentItem, ...partial };
  state.history = state.history.map((item) => (item.run_id === state.currentItem.run_id ? { ...item, ...partial } : item));
}

function updateToolbarState() {
  const hasAnswer = Boolean(getCurrentAnswerText().trim());
  toggleViewButton.disabled = !state.currentItem;
  saveEditButton.disabled = state.saving || !state.currentItem;
  copyResultButton.disabled = !hasAnswer;
  translateButton.disabled = !hasAnswer || state.translating;
  copyTranslationButton.disabled = !(state.currentItem?.translated_answer || "").trim();
  runButton.disabled = state.running;
  newSessionButton.disabled = state.running || state.translating || state.saving;
}

function setAnswerMode(mode) {
  state.answerMode = mode;
  const editing = mode === "edit";
  if (!editing) {
    resultPreview.innerHTML = renderMarkdown(getCurrentAnswerText());
  }
  resultPreview.classList.toggle("hidden", editing);
  resultEditor.classList.toggle("hidden", !editing);
  saveEditButton.classList.toggle("hidden", !editing);
  toggleViewButton.textContent = editing ? TEXT.switchToPreview : TEXT.switchToEdit;
  answerModeText.textContent = editing ? TEXT.editMode : TEXT.previewMode;
  updateToolbarState();
}

function updateResultSummary(item) {
  if (!item) {
    resultSummary.textContent = TEXT.summaryPlaceholder;
    return;
  }

  const pieces = [
    `${TEXT.modelLabel}${item.model || "\u672a\u8bb0\u5f55"}`,
    `${TEXT.reasoningLabel}${item.reasoning_effort || "\u672a\u8bb0\u5f55"}`,
    `${TEXT.sourceLabel}${item.source_count || 0}`,
    `${TEXT.citationLabel}${item.citations_present ? TEXT.yes : TEXT.no}`,
    formatTokenUsage(item.token_usage)
  ];

  if (item.translated_answer) {
    const translationTokenText = item.translated_token_usage ? `\uff0c${formatTokenUsage(item.translated_token_usage)}` : "";
    pieces.push(`${TEXT.translationLabel}${translationTokenText}`);
  }

  resultSummary.textContent = pieces.join(" \u00b7 ");
}

function renderTranslation(item) {
  if (!item?.translated_answer) {
    translationSection.classList.add("hidden");
    translationMeta.textContent = TEXT.translationPending;
    translationOutput.innerHTML = TEXT.translationPlaceholder;
    copyTranslationButton.classList.add("hidden");
    updateToolbarState();
    return;
  }

  translationSection.classList.remove("hidden");
  translationMeta.textContent = item.translated_token_usage?.total_tokens
    ? `\u5df2\u751f\u6210 \u00b7 ${formatTokenUsage(item.translated_token_usage)}`
    : "\u5df2\u751f\u6210";
  translationOutput.innerHTML = renderMarkdown(item.translated_answer);
  copyTranslationButton.classList.remove("hidden");
  updateToolbarState();
}

function renderDebug(item) {
  if (item?.debug_trace) {
    debugPanel.classList.remove("hidden");
    debugOutput.textContent = JSON.stringify(item.debug_trace, null, 2);
    return;
  }

  debugPanel.classList.add("hidden");
  debugOutput.textContent = "";
}

function loadSession(item, options = {}) {
  state.activeRunId = item.run_id;
  state.currentItem = { ...item };
  queryInput.value = item.query || "";
  webEnabled.checked = item.web_enabled ?? true;
  localKbEnabled.checked = item.local_kb_enabled ?? true;
  debugEnabled.checked = item.debug ?? false;
  resultEditor.value = item.final_answer || "";
  resultPreview.innerHTML = renderMarkdown(item.final_answer || "");
  resultMeta.textContent = `${TEXT.loadedAt} ${formatDateTime(item.created_at)} ${TEXT.sessionSuffix}`;
  updateResultSummary(item);
  renderTranslation(item);
  renderDebug(item);
  renderHistory();
  setAnswerMode(options.answerMode || state.answerMode);
  if (!options.silent) {
    setStatus(`${TEXT.loadedHistory}${item.query}`);
  }
}

function clearWorkspace() {
  state.activeRunId = null;
  state.currentItem = null;
  queryInput.value = "";
  resultMeta.textContent = TEXT.noResultYet;
  resultSummary.textContent = TEXT.summaryPlaceholder;
  resultPreview.innerHTML = TEXT.resultPlaceholder;
  resultEditor.value = "";
  translationSection.classList.add("hidden");
  translationMeta.textContent = TEXT.translationPending;
  translationOutput.textContent = TEXT.translationPlaceholder;
  copyTranslationButton.classList.add("hidden");
  renderDebug(null);
  setAnswerMode("preview");
  renderHistory();
}

function renderHistory() {
  historyContainer.innerHTML = "";
  historyMeta.textContent = state.history.length ? `\u5171 ${state.history.length} ${TEXT.historyCountSuffix}` : TEXT.historyEmptyMeta;

  if (!state.history.length) {
    historyContainer.innerHTML = `<p class="muted">${TEXT.noHistory}</p>`;
    return;
  }

  for (const item of state.history.slice(0, 40)) {
    const card = document.createElement("div");
    const openButton = document.createElement("button");
    const title = document.createElement("div");
    const time = document.createElement("div");
    const meta = document.createElement("div");
    const deleteButton = document.createElement("button");

    card.className = `history-card${item.run_id === state.activeRunId ? " active" : ""}`;
    openButton.className = "history-open";
    openButton.type = "button";
    title.className = "history-title";
    time.className = "history-time";
    meta.className = "history-meta";
    deleteButton.className = "history-delete";
    deleteButton.type = "button";
    deleteButton.title = TEXT.deleteTitle;
    deleteButton.textContent = state.deletingRunId === item.run_id ? "..." : "\u00d7";
    deleteButton.disabled = state.deletingRunId === item.run_id;

    title.textContent = item.query || TEXT.untitledQuestion;
    time.textContent = formatDateTime(item.created_at);
    meta.textContent = `${item.model || "-"} \u00b7 ${item.reasoning_effort || "-"} \u00b7 ${item.source_count || 0} ${TEXT.sourceCountSuffix} \u00b7 ${item.translated_answer ? TEXT.translated : TEXT.original}`;

    openButton.appendChild(title);
    openButton.appendChild(time);
    openButton.appendChild(meta);
    openButton.addEventListener("click", () => {
      loadSession(item);
    });

    deleteButton.addEventListener("click", async (event) => {
      event.stopPropagation();
      await deleteSession(item.run_id);
    });

    card.appendChild(openButton);
    card.appendChild(deleteButton);
    historyContainer.appendChild(card);
  }
}

async function refreshHistory() {
  try {
    const history = await window.codexDesktop.getHistory();
    state.history = history.items || [];

    if (state.activeRunId) {
      const selected = state.history.find((item) => item.run_id === state.activeRunId);
      if (selected) {
        loadSession(selected, { silent: true, answerMode: state.answerMode });
      } else {
        clearWorkspace();
      }
    } else {
      renderHistory();
    }
  } catch (error) {
    historyContainer.innerHTML = `<p class="muted">${error.message}</p>`;
  }
}

async function loadConfig() {
  try {
    const config = await window.codexDesktop.getConfig();
    const model = getModelPreset(config.model || DEFAULT_MODEL).value;
    const reasoningEffort = populateReasoningSelect(model, config.reasoning_effort || "medium");

    state.config = {
      ...config,
      model,
      reasoning_effort: reasoningEffort
    };

    populateModelSelect(model);
    modelSelect.value = model;
    reasoningSelect.value = reasoningEffort;
    modelSelect.disabled = false;
    reasoningSelect.disabled = false;
  } catch {
    const fallbackModel = DEFAULT_MODEL;
    const fallbackReasoningEffort = populateReasoningSelect(fallbackModel, "medium");
    state.config = {
      api_url: "",
      model: fallbackModel,
      reasoning_effort: fallbackReasoningEffort,
      skill_path: "",
      local_kb_roots: []
    };
    populateModelSelect(fallbackModel);
    modelSelect.value = fallbackModel;
    reasoningSelect.value = fallbackReasoningEffort;
    modelSelect.disabled = false;
    reasoningSelect.disabled = false;
    setStatus(TEXT.configLoadFailed);
  }
}

async function saveConfigSelection() {
  const nextConfig = getCurrentConfig();
  state.config = nextConfig;

  try {
    await window.codexDesktop.saveConfig(nextConfig);
    setStatus(TEXT.configSaved);
  } catch {
    setStatus(TEXT.configSaveFailed);
  }
}

async function checkHealth() {
  try {
    const health = await window.codexDesktop.health();
    setHealth(true, translateHealth(health.status));
  } catch {
    setHealth(false, TEXT.backendOffline);
  }
}

async function saveEditedAnswer() {
  if (!state.currentItem) {
    return;
  }

  const nextAnswer = resultEditor.value.trim();
  state.saving = true;
  updateToolbarState();
  setStatus(TEXT.savingAnswer);

  try {
    const updated = await window.codexDesktop.updateHistory(state.currentItem.run_id, {
      final_answer: nextAnswer
    });
    syncCurrentItem(updated);
    loadSession(updated, { silent: true, answerMode: "preview" });
    setStatus(TEXT.savedAnswer);
  } catch (error) {
    setStatus(error.message);
    playNotification("error");
  } finally {
    state.saving = false;
    updateToolbarState();
  }
}

async function deleteSession(runId) {
  state.deletingRunId = runId;
  renderHistory();
  setStatus(TEXT.deletingSession);

  try {
    const history = await window.codexDesktop.deleteHistory(runId);
    state.history = history.items || [];

    if (state.activeRunId === runId) {
      clearWorkspace();
      setStatus(TEXT.deletedCurrent);
    } else {
      renderHistory();
      setStatus(TEXT.deletedSession);
    }
  } catch (error) {
    setStatus(error.message);
    playNotification("error");
  } finally {
    state.deletingRunId = null;
    renderHistory();
  }
}

async function translateCurrentAnswer() {
  const answerText = getCurrentAnswerText().trim();
  const config = getCurrentConfig();
  if (!answerText) {
    setStatus(TEXT.noAnswerToTranslate);
    return;
  }

  if (state.answerMode === "edit" && state.currentItem && answerText !== state.currentItem.final_answer) {
    await saveEditedAnswer();
  }

  state.translating = true;
  updateToolbarState();
  translateButton.textContent = TEXT.translatingButton;
  setStatus(TEXT.translating);

  try {
    const result = await window.codexDesktop.translateText({
      text: answerText,
      run_id: state.currentItem?.run_id || null,
      model: config.model,
      reasoning_effort: config.reasoning_effort
    });

    syncCurrentItem({
      translated_answer: result.translated_text,
      translated_token_usage: result.token_usage
    });
    renderTranslation(state.currentItem);
    updateResultSummary(state.currentItem);
    setStatus(TEXT.translatedDone);
    playNotification("success");
  } catch (error) {
    setStatus(error.message);
    playNotification("error");
  } finally {
    state.translating = false;
    translateButton.textContent = TEXT.translateButton;
    updateToolbarState();
  }
}

async function runQuery() {
  const query = queryInput.value.trim();
  const config = getCurrentConfig();
  if (!query) {
    resultMeta.textContent = TEXT.inputRequired;
    resultPreview.innerHTML = TEXT.inputRequiredBody;
    resultEditor.value = "";
    return;
  }

  state.running = true;
  updateToolbarState();
  setStatus(TEXT.runningStatus);
  resultMeta.textContent = TEXT.runningMeta;
  resultSummary.textContent = TEXT.runningSummary;
  resultPreview.innerHTML = TEXT.generatingAnswer;
  resultEditor.value = "";
  translationSection.classList.add("hidden");
  renderDebug(null);

  try {
    const result = await window.codexDesktop.runTask({
      query,
      web_enabled: webEnabled.checked,
      local_kb_enabled: localKbEnabled.checked,
      rules_profile: "strict-answer-formatter",
      debug: debugEnabled.checked,
      model: config.model,
      reasoning_effort: config.reasoning_effort
    });

    const item = {
      run_id: result.run_id,
      query,
      created_at: new Date().toISOString(),
      final_answer: result.final_answer,
      source_count: result.source_count,
      citations_present: result.citations_present,
      model: result.model,
      reasoning_effort: result.reasoning_effort,
      token_usage: result.token_usage,
      translated_answer: result.translated_answer || "",
      translated_token_usage: result.translated_token_usage || null,
      web_enabled: webEnabled.checked,
      local_kb_enabled: localKbEnabled.checked,
      debug: debugEnabled.checked,
      debug_trace: result.debug_trace || null
    };

    await refreshHistory();
    const selected = state.history.find((historyItem) => historyItem.run_id === result.run_id) || item;
    loadSession(selected, { silent: true, answerMode: "preview" });
    resultMeta.textContent = `\u4efb\u52a1 ${result.run_id} \u00b7 ${result.source_count} ${TEXT.sourceCountSuffix} \u00b7 ${TEXT.citationLabel}${result.citations_present ? TEXT.yes : TEXT.no}`;
    setStatus(TEXT.answerReady);
    playNotification("success");
  } catch (error) {
    resultMeta.textContent = TEXT.runFailed;
    resultSummary.textContent = TEXT.runFailedSummary;
    resultPreview.textContent = error.message;
    resultEditor.value = "";
    translationSection.classList.add("hidden");
    setStatus(error.message);
    playNotification("error");
  } finally {
    state.running = false;
    updateToolbarState();
  }
}

newSessionButton.addEventListener("click", () => {
  clearWorkspace();
  setStatus(TEXT.newSessionReady);
});

runButton.addEventListener("click", runQuery);
toggleViewButton.addEventListener("click", () => {
  if (!state.currentItem) {
    return;
  }
  setAnswerMode(state.answerMode === "preview" ? "edit" : "preview");
});
saveEditButton.addEventListener("click", saveEditedAnswer);
copyResultButton.addEventListener("click", () => {
  copyText(getCurrentAnswerText(), TEXT.copiedAnswer, copyResultButton);
});
translateButton.addEventListener("click", translateCurrentAnswer);
copyTranslationButton.addEventListener("click", () => {
  copyText(state.currentItem?.translated_answer || "", TEXT.copiedTranslation, copyTranslationButton);
});
modelSelect.addEventListener("change", async () => {
  const nextReasoningEffort = populateReasoningSelect(modelSelect.value, reasoningSelect.value || "medium");
  reasoningSelect.value = nextReasoningEffort;
  await saveConfigSelection();
});
reasoningSelect.addEventListener("change", saveConfigSelection);
resultEditor.addEventListener("input", updateToolbarState);

loadConfig();
checkHealth();
refreshHistory();
setStatus(TEXT.preparingSession);
updateToolbarState();
setInterval(checkHealth, 4000);
