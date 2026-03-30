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
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
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
  getHistory: () => request("/api/history"),
  getConfig: () => request("/api/config"),
  saveConfig: (payload) =>
    request("/api/config", {
      method: "PUT",
      body: JSON.stringify(payload)
    })
});
