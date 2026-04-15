const { contextBridge, ipcRenderer } = require('electron');
const { Marked } = require('marked');
const { markedHighlight } = require('marked-highlight');
const hljs = require('highlight.js');

// Create a configured marked instance with syntax highlighting
const marked = new Marked(
  markedHighlight({
    langPrefix: 'hljs language-',
    highlight(code, lang) {
      if (lang && hljs.getLanguage(lang)) {
        return hljs.highlight(code, { language: lang }).value;
      }
      return hljs.highlightAuto(code).value;
    },
  })
);

contextBridge.exposeInMainWorld('api', {
  // Documentation access
  getFrameworks: () => ipcRenderer.invoke('docs:getFrameworks'),
  getTree: (framework, subpath) => ipcRenderer.invoke('docs:getTree', framework, subpath),
  readMarkdownFile: (filePath) => ipcRenderer.invoke('docs:readFile', filePath),
  getSearchIndex: () => ipcRenderer.invoke('docs:getSearchIndex'),

  // Persistent store
  store: {
    get: (key) => ipcRenderer.invoke('store:get', key),
    set: (key, value) => ipcRenderer.invoke('store:set', key, value),
  },

  // App info
  getBasePath: () => ipcRenderer.invoke('app:getBasePath'),
  getTheme: () => ipcRenderer.invoke('app:getTheme'),

  // Markdown rendering (runs in preload context where require works)
  renderMarkdown: (text) => marked.parse(text),

  // Listen for events from main process
  onShortcut: (callback) => ipcRenderer.on('shortcut', (_, action) => callback(action)),
  onThemeChanged: (callback) => ipcRenderer.on('theme-changed', (_, theme) => callback(theme)),
});
