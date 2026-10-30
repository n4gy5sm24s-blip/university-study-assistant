const { app, BrowserWindow, dialog, shell } = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const net = require("node:net");
const path = require("node:path");

let mainWindow;
let backendProcess;
let isQuitting = false;

function log(message) {
  try {
    fs.appendFileSync(
      path.join(app.getPath("userData"), "desktop.log"),
      `${new Date().toISOString()} ${message}\n`,
    );
  } catch (_) {
    // Logging must never prevent the app from starting.
  }
}

function reservePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.on("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
  });
}

function backendCommand(port) {
  if (app.isPackaged) {
    return {
      command: path.join(process.resourcesPath, "runtime", "python", "python.exe"),
      args: ["-m", "app.desktop_server", "--port", String(port)],
      options: {
        cwd: path.join(process.resourcesPath, "backend"),
        env: {
          ...process.env,
          PYTHONPATH: [
            path.join(process.resourcesPath, "backend"),
            path.join(process.resourcesPath, "runtime", "packages"),
          ].join(path.delimiter),
        },
      },
    };
  }

  const projectRoot = path.resolve(__dirname, "..");
  const python = path.join(projectRoot, ".venv", "Scripts", "python.exe");
  const packagePath = path.join(projectRoot, ".packages");
  return {
    command: python,
    args: ["-m", "app.desktop_server", "--port", String(port)],
    options: {
      cwd: projectRoot,
      env: {
        ...process.env,
        PYTHONPATH: [packagePath, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter),
      },
    },
  };
}

function startBackend(port) {
  const userData = app.getPath("userData");
  const dataDirectory = path.join(userData, "data");
  fs.mkdirSync(dataDirectory, { recursive: true });
  const launch = backendCommand(port);
  backendProcess = spawn(launch.command, launch.args, {
    ...launch.options,
    windowsHide: true,
    env: {
      ...(launch.options.env || process.env),
      STUDY_ASSISTANT_DB: path.join(dataDirectory, "study_assistant.db"),
      STUDY_ASSISTANT_ENV: path.join(userData, ".env"),
    },
  });
  log(`backend start: ${launch.command} --port ${port}`);
  backendProcess.stdout?.on("data", (data) => log(`backend stdout: ${String(data).trim()}`));
  backendProcess.stderr?.on("data", (data) => log(`backend stderr: ${String(data).trim()}`));
  backendProcess.on("error", (error) => log(`backend spawn error: ${error.message}`));
  backendProcess.on("exit", (code) => {
    log(`backend exit: ${code ?? "unknown"}`);
    if (!isQuitting && code !== 0) {
      dialog.showErrorBox("Coursework AI 无法继续运行", `本地服务意外停止（代码 ${code ?? "未知"}）。请重新打开应用。`);
      app.quit();
    }
  });
}

async function waitForBackend(url) {
  let lastError;
  for (let attempt = 0; attempt < 80; attempt += 1) {
    try {
      const response = await fetch(`${url}/api/health`);
      if (response.ok) return;
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw lastError || new Error("本地服务启动超时");
}

async function createWindow() {
  log("desktop startup");
  const port = await reservePort();
  const localUrl = `http://127.0.0.1:${port}`;
  startBackend(port);
  await waitForBackend(localUrl);

  mainWindow = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 980,
    minHeight: 680,
    backgroundColor: "#000000",
    title: "Coursework AI",
    autoHideMenuBar: true,
    show: false,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  mainWindow.once("ready-to-show", () => mainWindow.show());
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (!url.startsWith(localUrl)) shell.openExternal(url);
    return { action: "deny" };
  });
  await mainWindow.loadURL(localUrl);
  log(`window loaded: ${localUrl}`);
}

app.whenReady().then(createWindow).catch((error) => {
  log(`startup failed: ${error?.stack || error}`);
  dialog.showErrorBox("Coursework AI 启动失败", String(error?.message || error));
  app.quit();
});

app.on("window-all-closed", () => app.quit());
app.on("before-quit", () => {
  isQuitting = true;
  if (backendProcess && !backendProcess.killed) backendProcess.kill();
});
