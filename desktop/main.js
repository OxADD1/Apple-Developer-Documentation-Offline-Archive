const { app, BrowserWindow, ipcMain, Menu, shell, nativeTheme } = require('electron');
const path = require('path');
const fs = require('fs');
const os = require('os');

// --- Path resolution ---

function getBasePath() {
  // Packaged build: resources dir
  const resourceMd = path.join(process.resourcesPath, 'markdown');
  if (fs.existsSync(resourceMd)) return process.resourcesPath;
  // Dev: parent of desktop/
  const devMd = path.join(__dirname, '..', 'markdown');
  if (fs.existsSync(devMd)) return path.join(__dirname, '..');
  return path.join(__dirname, '..');
}

const BASE_PATH = getBasePath();
const MARKDOWN_DIR = path.join(BASE_PATH, 'markdown');

// --- User data store ---

const STORE_DIR = path.join(os.homedir(), '.apple-docs-viewer');
const STORE_FILE = path.join(STORE_DIR, 'user-data.json');

let storeData = {
  bookmarks: [],
  history: [],
  lastSession: { page: null, scrollY: 0, sidebarTab: 'frameworks', sidebarWidth: 280 },
  preferences: { theme: 'system', fontSize: 16, tocVisible: true },
};

function loadStore() {
  try {
    if (fs.existsSync(STORE_FILE)) {
      const raw = fs.readFileSync(STORE_FILE, 'utf-8');
      const parsed = JSON.parse(raw);
      storeData = { ...storeData, ...parsed };
    }
  } catch (e) {
    console.error('Failed to load store:', e.message);
  }
}

function saveStore() {
  try {
    if (!fs.existsSync(STORE_DIR)) fs.mkdirSync(STORE_DIR, { recursive: true });
    fs.writeFileSync(STORE_FILE, JSON.stringify(storeData, null, 2));
  } catch (e) {
    console.error('Failed to save store:', e.message);
  }
}

loadStore();

// --- IPC handlers ---

// Get list of framework directories
ipcMain.handle('docs:getFrameworks', () => {
  try {
    const entries = fs.readdirSync(MARKDOWN_DIR, { withFileTypes: true });
    return entries
      .filter(e => e.isDirectory())
      .map(e => {
        const fwDir = path.join(MARKDOWN_DIR, e.name);
        let count = 0;
        try {
          // Count .md files recursively (fast: just count, don't read)
          const countFiles = (dir) => {
            const items = fs.readdirSync(dir, { withFileTypes: true });
            for (const item of items) {
              if (item.isFile() && item.name.endsWith('.md')) count++;
              else if (item.isDirectory()) countFiles(path.join(dir, item.name));
            }
          };
          countFiles(fwDir);
        } catch (_) {}
        return { name: e.name, count };
      })
      .sort((a, b) => a.name.localeCompare(b.name));
  } catch (e) {
    return [];
  }
});

// Get directory tree for a path (lazy loading)
ipcMain.handle('docs:getTree', (_, framework, subpath) => {
  try {
    const dirPath = subpath
      ? path.join(MARKDOWN_DIR, framework, subpath)
      : path.join(MARKDOWN_DIR, framework);

    const entries = fs.readdirSync(dirPath, { withFileTypes: true });
    return entries
      .map(e => {
        const relPath = subpath ? `${subpath}/${e.name}` : e.name;
        if (e.isDirectory()) {
          return { name: e.name, type: 'dir', path: relPath };
        } else if (e.name.endsWith('.md')) {
          return { name: e.name.replace('.md', ''), type: 'file', path: relPath };
        }
        return null;
      })
      .filter(Boolean)
      .sort((a, b) => {
        // Dirs first, then files
        if (a.type !== b.type) return a.type === 'dir' ? -1 : 1;
        return a.name.localeCompare(b.name);
      });
  } catch (e) {
    return [];
  }
});

// Read and parse a markdown file
ipcMain.handle('docs:readFile', (_, filePath) => {
  try {
    const fullPath = path.join(MARKDOWN_DIR, filePath);
    if (!fs.existsSync(fullPath)) return null;

    const raw = fs.readFileSync(fullPath, 'utf-8');

    // Parse YAML frontmatter
    let frontmatter = {};
    let content = raw;

    if (raw.startsWith('---')) {
      const parts = raw.split('---');
      if (parts.length >= 3) {
        const yamlStr = parts[1];
        content = parts.slice(2).join('---').trim();

        // Simple YAML parser for our needs
        for (const line of yamlStr.split('\n')) {
          const match = line.match(/^(\w+):\s*(.+)/);
          if (match) {
            let val = match[2].trim().replace(/^["']|["']$/g, '');
            frontmatter[match[1]] = val;
          }
          // Handle platforms list
          if (line.trim().startsWith('- name:')) {
            if (!frontmatter.platformsList) frontmatter.platformsList = [];
            const pMatch = line.match(/- name:\s*(.+)/);
            if (pMatch) frontmatter.platformsList.push(pMatch[1].trim());
          }
        }
      }
    }

    return { frontmatter, content, raw };
  } catch (e) {
    return null;
  }
});

// Load search index
ipcMain.handle('docs:getSearchIndex', () => {
  try {
    // Try html/search-index.json first
    const htmlIndex = path.join(BASE_PATH, 'html', 'search-index.json');
    if (fs.existsSync(htmlIndex)) {
      const raw = fs.readFileSync(htmlIndex, 'utf-8');
      return JSON.parse(raw);
    }
    // Fallback: packaged
    const pkgIndex = path.join(process.resourcesPath, 'search-index.json');
    if (fs.existsSync(pkgIndex)) {
      const raw = fs.readFileSync(pkgIndex, 'utf-8');
      return JSON.parse(raw);
    }
    return [];
  } catch (e) {
    return [];
  }
});

// Store get/set
ipcMain.handle('store:get', (_, key) => {
  return key ? storeData[key] : storeData;
});

ipcMain.handle('store:set', (_, key, value) => {
  storeData[key] = value;
  saveStore();
});

// App info
ipcMain.handle('app:getBasePath', () => BASE_PATH);
ipcMain.handle('app:getTheme', () => nativeTheme.shouldUseDarkColors ? 'dark' : 'light');

// --- Window ---

function createWindow() {
  const win = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 900,
    minHeight: 600,
    title: 'Apple Developer Documentation',
    titleBarStyle: 'hiddenInset',
    trafficLightPosition: { x: 16, y: 16 },
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false,
    },
  });

  win.loadFile(path.join(__dirname, 'renderer', 'index.html'));

  // Log renderer console to main process stderr for debugging
  win.webContents.on('console-message', (_, level, msg) => {
    if (level >= 2) console.error(`[renderer] ${msg}`);
  });
  win.webContents.on('preload-error', (_, pp, error) => {
    console.error(`[preload-error] ${error.message}`);
  });

  // Menu
  const template = [
    {
      label: app.name,
      submenu: [
        { role: 'about' },
        { type: 'separator' },
        { role: 'quit' },
      ],
    },
    {
      label: 'File',
      submenu: [
        {
          label: 'Search',
          accelerator: 'CmdOrCtrl+K',
          click: () => win.webContents.send('shortcut', 'search'),
        },
        {
          label: 'Home',
          accelerator: 'CmdOrCtrl+Shift+H',
          click: () => win.webContents.send('shortcut', 'home'),
        },
        {
          label: 'Bookmark Page',
          accelerator: 'CmdOrCtrl+D',
          click: () => win.webContents.send('shortcut', 'bookmark'),
        },
        { type: 'separator' },
        { role: 'close' },
      ],
    },
    {
      label: 'Edit',
      submenu: [
        { role: 'copy' },
        { role: 'selectAll' },
      ],
    },
    {
      label: 'View',
      submenu: [
        {
          label: 'Toggle Table of Contents',
          accelerator: 'CmdOrCtrl+T',
          click: () => win.webContents.send('shortcut', 'toggleToc'),
        },
        { type: 'separator' },
        {
          label: 'Increase Font Size',
          accelerator: 'CmdOrCtrl+=',
          click: () => win.webContents.send('shortcut', 'fontIncrease'),
        },
        {
          label: 'Decrease Font Size',
          accelerator: 'CmdOrCtrl+-',
          click: () => win.webContents.send('shortcut', 'fontDecrease'),
        },
        { type: 'separator' },
        { role: 'reload' },
        { role: 'togglefullscreen' },
      ],
    },
    {
      label: 'Go',
      submenu: [
        {
          label: 'Back',
          accelerator: 'CmdOrCtrl+[',
          click: () => win.webContents.send('shortcut', 'back'),
        },
        {
          label: 'Forward',
          accelerator: 'CmdOrCtrl+]',
          click: () => win.webContents.send('shortcut', 'forward'),
        },
      ],
    },
  ];

  Menu.setApplicationMenu(Menu.buildFromTemplate(template));

  // External links in default browser
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http')) shell.openExternal(url);
    return { action: 'deny' };
  });

  // Theme change notification
  nativeTheme.on('updated', () => {
    win.webContents.send('theme-changed', nativeTheme.shouldUseDarkColors ? 'dark' : 'light');
  });
}

app.whenReady().then(createWindow);
app.on('window-all-closed', () => app.quit());
app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
