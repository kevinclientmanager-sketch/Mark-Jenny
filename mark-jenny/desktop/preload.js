const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('markimti', {
  // App info
  getUserData: () => ipcRenderer.invoke('get-user-data'),
  getBackendStatus: () => ipcRenderer.invoke('get-backend-status'),

  // Extensions
  getExtensions: () => ipcRenderer.invoke('get-extensions'),
  installExtension: (source) => ipcRenderer.invoke('install-extension', source),
  uninstallExtension: (name) => ipcRenderer.invoke('uninstall-extension', name),

  // Models
  downloadModel: (modelId) => ipcRenderer.invoke('download-model', modelId),

  // System
  openExternal: (url) => ipcRenderer.invoke('open-external', url),
  showSaveDialog: (options) => ipcRenderer.invoke('show-save-dialog', options),
  showOpenDialog: (options) => ipcRenderer.invoke('show-open-dialog', options),

  // Events from main process
  onNewChat: (callback) => ipcRenderer.on('new-chat', callback),
  onOpenSettings: (callback) => ipcRenderer.on('open-settings', callback),
});
