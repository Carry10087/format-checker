const healthBadge = document.getElementById("healthBadge");
const runButton = document.getElementById("runButton");
const queryInput = document.getElementById("queryInput");
const webEnabled = document.getElementById("webEnabled");
const localKbEnabled = document.getElementById("localKbEnabled");
const debugEnabled = document.getElementById("debugEnabled");
const resultOutput = document.getElementById("resultOutput");
const resultMeta = document.getElementById("resultMeta");
const historyContainer = document.getElementById("history");
const debugPanel = document.getElementById("debugPanel");
const debugOutput = document.getElementById("debugOutput");

function setHealth(ok, text) {
  healthBadge.textContent = text;
  healthBadge.className = `badge ${ok ? "badge-ok" : "badge-warn"}`;
}

function renderHistory(items) {
  historyContainer.innerHTML = "";
  if (!items.length) {
    historyContainer.innerHTML = '<p class="muted">No runs yet.</p>';
    return;
  }

  for (const item of items.slice(0, 20)) {
    const div = document.createElement("button");
    div.className = "history-item";
    div.innerHTML = `
      <strong>${item.query}</strong>
      <span>${item.created_at}</span>
    `;
    div.addEventListener("click", () => {
      resultMeta.textContent = `Loaded from history • ${item.created_at}`;
      resultOutput.textContent = item.final_answer;
      if (item.debug_trace) {
        debugPanel.classList.remove("hidden");
        debugOutput.textContent = JSON.stringify(item.debug_trace, null, 2);
      } else {
        debugPanel.classList.add("hidden");
      }
    });
    historyContainer.appendChild(div);
  }
}

async function refreshHistory() {
  try {
    const history = await window.codexDesktop.getHistory();
    renderHistory(history.items || []);
  } catch (error) {
    historyContainer.innerHTML = `<p class="muted">${error.message}</p>`;
  }
}

async function checkHealth() {
  try {
    const health = await window.codexDesktop.health();
    setHealth(true, health.status || "Ready");
  } catch {
    setHealth(false, "Backend offline");
  }
}

runButton.addEventListener("click", async () => {
  const query = queryInput.value.trim();
  if (!query) {
    resultOutput.textContent = "Please enter a query.";
    return;
  }

  runButton.disabled = true;
  resultMeta.textContent = "Running…";
  resultOutput.textContent = "Generating answer…";
  debugPanel.classList.add("hidden");

  try {
    const result = await window.codexDesktop.runTask({
      query,
      web_enabled: webEnabled.checked,
      local_kb_enabled: localKbEnabled.checked,
      rules_profile: "strict-answer-formatter",
      debug: debugEnabled.checked
    });

    resultMeta.textContent = `Run ${result.run_id} • ${result.source_count} sources • citations: ${result.citations_present ? "yes" : "no"}`;
    resultOutput.textContent = result.final_answer;

    if (result.debug_trace) {
      debugPanel.classList.remove("hidden");
      debugOutput.textContent = JSON.stringify(result.debug_trace, null, 2);
    }

    await refreshHistory();
  } catch (error) {
    resultMeta.textContent = "Run failed";
    resultOutput.textContent = error.message;
  } finally {
    runButton.disabled = false;
  }
});

checkHealth();
refreshHistory();
setInterval(checkHealth, 4000);
