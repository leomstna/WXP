const { app, BrowserWindow } = require('electron');
const path = require('path');

function createWindow () {
  const win = new BrowserWindow({
    width: 1280,
    height: 720,
    title: "WXP GameHub", // O NOME NA JANELA DO PC
    icon: path.join(__dirname, 'icon-512.png'), // O ÍCONE NA BARRA DE TAREFAS
    autoHideMenuBar: true, // ESCONDE O MENU SUPERIOR CHATO (Arquivo, Editar...)
    webPreferences: {
      nodeIntegration: true
    }
  });

  win.loadFile('index.html');
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});