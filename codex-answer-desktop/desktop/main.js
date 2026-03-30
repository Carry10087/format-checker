const { app, BrowserWindow } = require("electron");
const path = require("path");
const { spawn } = require("child_process");

const BACKEND_PORT = process.env.CODEX_DESKTOP_BACKEND_PORT || "8765";
let backendProcess = null;

function resolvePythonCommand() {
  return process.env.CODEX_DESKTOP_PYTHON || "python";
}

function startBackend() {
  const backendDir = path.join(__dirname, "..", "backend");
  const python = resolvePythonCommand();
  const args = [
    "-m",
    "uvicorn",
    "app.main:app",
    "--host",
    "127.0.0.1",
    "--port",
    BACKEND_PORT
  ];

  backendProcess = spawn(python, args, {
    cwd: backendDir,
    env: {
      ...process.env,
      PYTHONPATH: backendDir
    },
    stdio: "pipe"
  });

  backendProcess.stdout.on("data", (data) => {
    console.log(`[backend] ${data}`.trim());
  });

  backendProcess.stderr.on("data", (data) => {
    console.error(`[backend] ${data}`.trim());
  });

  backendProcess.on("exit", (code) => {
    console.log(`Backend exited with code ${code}`);
    backendProcess = null;
  });
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 1080,
    minHeight: 760,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js")
    }
  });

  win.loadFile(path.join(__dirname, "src", "index.html"));
}

app.whenReady().then(() => {
  startBackend();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  if (backendProcess) {
    backendProcess.kill();
  }
});
