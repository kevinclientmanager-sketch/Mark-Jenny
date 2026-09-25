const { app, BrowserWindow, ipcMain, dialog, shell, Menu, Tray, nativeImage } = require('electron');
const path = require('path');
const { spawn, exec } = require('child_process');
const fs = require('fs');
const http = require('http');

// Data directories
const USER_DATA = app.getPath('userData');
const BACKEND_DIR = path.join(USER_DATA, 'backend');
const FRONTEND_DIR = path.join(__dirname, 'frontend');
const EXTENSIONS_DIR = path.join(USER_DATA, 'extensions');
const MODELS_DIR = path.join(USER_DATA, 'models');
const DB_DIR = path.join(USER_DATA, 'data');

// Ensure directories exist
[BACKEND_DIR, EXTENSIONS_DIR, MODELS_DIR, DB_DIR].forEach(dir => {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
});

let mainWindow = null;
let backendProcess = null;
let tray = null;
const BACKEND_PORT = 8000;
const FRONTEND_PORT = 3000;

// ==================== BACKEND MANAGEMENT ====================

function getBackendPath() {
  const isDev = !app.isPackaged;
  if (isDev) {
    return path.join(__dirname, '..', 'backend', 'venv', 'Scripts', 'python.exe');
  }
  // Packaged: backend is bundled as .exe
  return path.join(process.resourcesPath, 'backend', 'mark-imti-server.exe');
}

function getBackendArgs() {
  const isDev = !app.isPackaged;
  if (isDev) {
    return [path.join(__dirname, '..', 'backend', 'main.py')];
  }
  return [];
}

function startBackend() {
  return new Promise((resolve, reject) => {
    const backendPath = getBackendPath();
    const args = getBackendArgs();

    console.log('[Mark-Imti] Starting backend:', backendPath);

    backendProcess = spawn(backendPath, args, {
      cwd: isDev ? path.join(__dirname, '..', 'backend') : path.dirname(backendPath),
      env: {
        ...process.env,
        MARK_IMTI_DATA: DB_DIR,
        MARK_IMTI_PORT: String(BACKEND_PORT),
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    backendProcess.stdout.on('data', (data) => {
      const msg = data.toString();
      console.log('[Backend]', msg);
      if (msg.includes('Uvicorn running on') || msg.includes('Started server process')) {
        resolve();
      }
    });

    backendProcess.stderr.on('data', (data) => {
      console.error('[Backend]', data.toString());
    });

    backendProcess.on('error', (err) => {
      console.error('[Backend] Failed to start:', err);
      reject(err);
    });

    backendProcess.on('exit', (code) => {
      console.log('[Backend] Exited with code:', code);
      backendProcess = null;
    });

    // Timeout after 30 seconds
    setTimeout(() => resolve(), 30000);
  });
}

function stopBackend() {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }
}

function checkBackendHealth() {
  return new Promise((resolve) => {
    http.get(`http://localhost:${BACKEND_PORT}/health`, (res) => {
      resolve(res.statusCode === 200);
    }).on('error', () => resolve(false));
  });
}

// ==================== EXTENSION SYSTEM ====================

function getInstalledExtensions() {
  const manifestPath = path.join(EXTENSIONS_DIR, 'manifest.json');
  if (fs.existsSync(manifestPath)) {
    return JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
  }
  return { extensions: [] };
}

function saveExtensionManifest(manifest) {
  fs.writeFileSync(
    path.join(EXTENSIONS_DIR, 'manifest.json'),
    JSON.stringify(manifest, null, 2)
  );
}

async function installExtension(source) {
  // source can be: local path, URL, or { name, type, content }
  try {
    if (source.url) {
      // Download from URL
      const response = await fetch(source.url);
      const buffer = await response.arrayBuffer();
      const extDir = path.join(EXTENSIONS_DIR, source.name);
      fs.mkdirSync(extDir, { recursive: true });
      fs.writeFileSync(path.join(extDir, 'index.js'), Buffer.from(buffer));
    } else if (source.path) {
      // Copy from local path
      const extDir = path.join(EXTENSIONS_DIR, source.name);
      fs.mkdirSync(extDir, { recursive: true });
      fs.cpSync(source.path, extDir, { recursive: true });
    } else if (source.content) {
      // Direct content
      const extDir = path.join(EXTENSIONS_DIR, source.name);
      fs.mkdirSync(extDir, { recursive: true });
      fs.writeFileSync(path.join(extDir, 'index.js'), source.content);
    }

    // Update manifest
    const manifest = getInstalledExtensions();
    manifest.extensions.push({
      name: source.name,
      type: source.type || 'skill',
      installedAt: new Date().toISOString(),
      version: source.version || '1.0.0',
    });
    saveExtensionManifest(manifest);

    return { success: true, message: `Extension ${source.name} installed` };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

function uninstallExtension(name) {
  const extDir = path.join(EXTENSIONS_DIR, name);
  if (fs.existsSync(extDir)) {
    fs.rmSync(extDir, { recursive: true, force: true });
  }
  const manifest = getInstalledExtensions();
  manifest.extensions = manifest.extensions.filter(e => e.name !== name);
  saveExtensionManifest(manifest);
  return { success: true };
}

// ==================== MODEL MANAGEMENT ====================

async function downloadModel(modelId) {
  const modelDir = path.join(MODELS_DIR, modelId.replace(/\//g, '_'));
  fs.mkdirSync(modelDir, { recursive: true });

  // Call backend to download
  return new Promise((resolve, reject) => {
    const req = http.request(
      `http://localhost:${BACKEND_PORT}/api/v1/integrations/airllm/load`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      },
      (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => resolve(JSON.parse(data)));
      }
    );
    req.on('error', reject);
    req.write(JSON.stringify({ model_id: modelId }));
    req.end();
  });
}

// ==================== WINDOW ====================

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    title: 'Mark-Imti',
    icon: path.join(__dirname, 'assets', 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
    titleBarStyle: 'hidden',
    backgroundColor: '#0a0a0a',
  });

  // Load the frontend
  const isDev = !app.isPackaged;
  if (isDev) {
    mainWindow.loadURL(`http://localhost:${FRONTEND_PORT}/chat`);
  } else {
    mainWindow.loadFile(path.join(FRONTEND_DIR, 'chat.html'));
  }

  // Build menu
  const menu = Menu.buildFromTemplate([
    {
      label: 'File',
      submenu: [
        { label: 'New Chat', accelerator: 'CmdOrCtrl+N', click: () => mainWindow.webContents.send('new-chat') },
        { label: 'Open Settings', accelerator: 'CmdOrCtrl+,', click: () => mainWindow.webContents.send('open-settings') },
        { type: 'separator' },
        { label: 'Exit', accelerator: 'CmdOrCtrl+Q', click: () => app.quit() },
      ],
    },
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' }, { role: 'redo' }, { type: 'separator' },
        { role: 'cut' }, { role: 'copy' }, { role: 'paste' }, { role: 'selectAll' },
      ],
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' }, { role: 'forceReload' }, { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' }, { role: 'zoomIn' }, { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
      ],
    },
    {
      label: 'Help',
      submenu: [
        { label: 'Documentation', click: () => shell.openExternal('https://markimti.com/docs') },
        { label: 'Report Issue', click: () => shell.openExternal('https://github.com/markimti/MARK-IMTI/issues') },
        { type: 'separator' },
        { label: 'About Mark-Imti', click: () => dialog.showMessageBox(mainWindow, {
          type: 'info',
          title: 'About Mark-Imti',
          message: 'Mark-Imti v1.0.0',
          detail: 'Autonomous AI Operating Platform\n\nA self-building, self-sufficient AI system that runs locally on your machine.',
        })},
      ],
    },
  ]);
  Menu.setApplicationMenu(menu);

  mainWindow.on('closed', () => { mainWindow = null; });
}

// ==================== IPC HANDLERS ====================

ipcMain.handle('get-user-data', () => USER_DATA);
ipcMain.handle('get-extensions', () => getInstalledExtensions());
ipcMain.handle('install-extension', (_, source) => installExtension(source));
ipcMain.handle('uninstall-extension', (_, name) => uninstallExtension(name));
ipcMain.handle('download-model', (_, modelId) => downloadModel(modelId));
ipcMain.handle('get-backend-status', () => checkBackendHealth());
ipcMain.handle('open-external', (_, url) => shell.openExternal(url));
ipcMain.handle('show-save-dialog', (_, options) => dialog.showSaveDialog(mainWindow, options));
ipcMain.handle('show-open-dialog', (_, options) => dialog.showOpenDialog(mainWindow, options));

// ==================== APP LIFECYCLE ====================

const gotSingleInstanceLock = app.requestSingleInstanceLock();
if (!gotSingleInstanceLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });

  app.whenReady().then(async () => {
    createWindow();

    // Start backend
    try {
      await startBackend();
      console.log('[Mark-Imti] Backend started');
    } catch (err) {
      console.error('[Mark-Imti] Backend failed to start:', err);
      dialog.showErrorBox('Backend Error', 'Failed to start Mark-Imti backend. The app may not function correctly.');
    }

    // Create tray
    tray = new Tray(nativeImage.createEmpty());
    tray.setToolTip('Mark-Imti');
    tray.setContextMenu(Menu.buildFromTemplate([
      { label: 'Show Mark-Imti', click: () => mainWindow?.show() },
      { label: 'Quit', click: () => app.quit() },
    ]));
  });

  app.on('window-all-closed', () => {
    stopBackend();
    if (process.platform !== 'darwin') app.quit();
  });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });

  app.on('before-quit', () => {
    stopBackend();
  });
}
