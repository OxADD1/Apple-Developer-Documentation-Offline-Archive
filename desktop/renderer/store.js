// Persistent storage wrapper
// All data persisted to ~/.apple-docs-viewer/user-data.json via main process IPC

const HISTORY_MAX = 200;

const Store = {
  _cache: {},

  async init() {
    const data = await window.api.store.get(null);
    this._cache = data || {};
  },

  // --- Bookmarks ---

  async getBookmarks() {
    return (await window.api.store.get('bookmarks')) || [];
  },

  async addBookmark(page) {
    const bookmarks = await this.getBookmarks();
    if (bookmarks.find(b => b.path === page.path)) return; // already exists
    bookmarks.unshift({
      path: page.path,
      title: page.title,
      framework: page.framework,
      addedAt: new Date().toISOString(),
    });
    await window.api.store.set('bookmarks', bookmarks);
  },

  async removeBookmark(path) {
    let bookmarks = await this.getBookmarks();
    bookmarks = bookmarks.filter(b => b.path !== path);
    await window.api.store.set('bookmarks', bookmarks);
  },

  async isBookmarked(path) {
    const bookmarks = await this.getBookmarks();
    return bookmarks.some(b => b.path === path);
  },

  async clearBookmarks() {
    await window.api.store.set('bookmarks', []);
  },

  // --- History ---

  async getHistory() {
    return (await window.api.store.get('history')) || [];
  },

  async addToHistory(page) {
    let history = await this.getHistory();
    // Remove existing entry for same page
    history = history.filter(h => h.path !== page.path);
    // Add to front
    history.unshift({
      path: page.path,
      title: page.title,
      framework: page.framework,
      viewedAt: new Date().toISOString(),
    });
    // Cap
    if (history.length > HISTORY_MAX) history = history.slice(0, HISTORY_MAX);
    await window.api.store.set('history', history);
  },

  async clearHistory() {
    await window.api.store.set('history', []);
  },

  // --- Session ---

  async getLastSession() {
    return (await window.api.store.get('lastSession')) || {
      page: null, scrollY: 0, sidebarTab: 'frameworks', sidebarWidth: 280,
    };
  },

  async saveSession(session) {
    await window.api.store.set('lastSession', session);
  },

  // --- Preferences ---

  async getPreferences() {
    return (await window.api.store.get('preferences')) || {
      theme: 'system', fontSize: 16, tocVisible: true,
    };
  },

  async setPreference(key, value) {
    const prefs = await this.getPreferences();
    prefs[key] = value;
    await window.api.store.set('preferences', prefs);
  },
};

window.Store = Store;
