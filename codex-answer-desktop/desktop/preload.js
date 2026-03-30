const { contextBridge } = require("electron");

const BACKEND_PORT = process.env.CODEX_DESKTOP_BACKEND_PORT || "8765";
const API_BASE = `http://127.0.0.1:${BACKEND_PORT}`;

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json"
    },
    ...options
  });

  if (!response.ok) {
    let message = `请求失败：${response.status}`;
    const text = await response.text();

    try {
      const data = JSON.parse(text);
      if (typeof data?.detail === "string" && data.detail.trim()) {
        message = data.detail.trim();
      }
    } catch {
      if (text && text.trim()) {
        message = text.trim();
      }
    }

    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

contextBridge.exposeInMainWorld("codexDesktop", {
  health: () => request("/health"),
  runTask: (payload) =>
    request("/api/run", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  translateText: (payload) =>
    request("/api/translate", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  getHistory: () => request("/api/history"),
  updateHistory: (runId, payload) =>
    request(`/api/history/${runId}`, {
      method: "PUT",
      body: JSON.stringify(payload)
    }),
  deleteHistory: (runId) =>
    request(`/api/history/${runId}`, {
      method: "DELETE"
    }),
  getConfig: () => request("/api/config"),
  saveConfig: (payload) =>
    request("/api/config", {
      method: "PUT",
      body: JSON.stringify(payload)
    })
});
