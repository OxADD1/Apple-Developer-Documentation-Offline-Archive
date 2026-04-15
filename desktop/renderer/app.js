// App controller — navigation, state management, keyboard shortcuts

const App = {
  _currentPage: null,
  _navHistory: [],
  _navIndex: -1,
  _scrollSaveTimer: null,
  _frameworks: [],

  async init() {
    // Init modules
    Content.init();
    await Store.init();
    await Sidebar.init();
    await Search.ensureLoaded();

    // Load preferences
    const prefs = await Store.getPreferences();
    this.applyTheme(prefs.theme);
    this.applyFontSize(prefs.fontSize);
    this.applyTocVisible(prefs.tocVisible);

    // Cache frameworks
    this._frameworks = await window.api.getFrameworks();

    // Restore last session
    const session = await Store.getLastSession();
    if (session.page) {
      await this.navigate(session.page, false);
      // Restore scroll after a tick
      setTimeout(() => {
        const content = document.getElementById('page-content');
        if (content) content.scrollTop = session.scrollY || 0;
      }, 100);
    } else {
      this.showHome();
    }

    // Setup scroll position tracking
    const contentEl = document.getElementById('page-content');
    contentEl.addEventListener('scroll', () => {
      clearTimeout(this._scrollSaveTimer);
      this._scrollSaveTimer = setTimeout(() => this._saveScrollPosition(), 500);
    });

    // Setup shortcuts from main process
    window.api.onShortcut((action) => this.handleShortcut(action));

    // Theme changes from OS
    window.api.onThemeChanged((theme) => {
      Store.getPreferences().then(prefs => {
        if (prefs.theme === 'system') this._setThemeClass(theme);
      });
    });

    // Toolbar button handlers
    document.getElementById('btn-back').addEventListener('click', () => this.goBack());
    document.getElementById('btn-forward').addEventListener('click', () => this.goForward());
    document.getElementById('btn-home').addEventListener('click', () => this.showHome());
    document.getElementById('btn-bookmark').addEventListener('click', () => this.toggleBookmark());
    document.getElementById('btn-theme').addEventListener('click', () => this.cycleTheme());
    document.getElementById('btn-font-down').addEventListener('click', () => this.changeFontSize(-1));
    document.getElementById('btn-font-up').addEventListener('click', () => this.changeFontSize(1));
    document.getElementById('btn-toc-toggle').addEventListener('click', () => this.toggleToc());

    // Search bar in toolbar
    document.getElementById('toolbar-search').addEventListener('focus', () => {
      Sidebar.focusSearch();
      document.getElementById('toolbar-search').blur();
    });
  },

  // --- Navigation ---

  async navigate(filePath, addToHistory = true) {
    const page = await Content.loadPage(filePath);
    if (!page) {
      this._showError(`Page not found: ${filePath}`);
      return;
    }

    this._currentPage = page;

    // Render content
    const contentHtml = Content.addHeadingIds(page.html);
    const breadcrumbs = Content.renderBreadcrumbs(filePath);
    const platformBadges = Content.renderPlatformBadges(page.frontmatter);
    const roleBadge = Content.renderRoleBadge(page.frontmatter);

    const pageEl = document.getElementById('page-content');
    pageEl.innerHTML = `
      <div class="page-header">
        <div class="breadcrumbs">${breadcrumbs}</div>
        <div class="page-meta">
          ${roleBadge}
          ${platformBadges}
        </div>
      </div>
      <div class="page-body">${contentHtml}</div>
    `;
    pageEl.scrollTop = 0;

    // Handle clicks on internal links
    pageEl.querySelectorAll('a[href]').forEach(a => {
      const href = a.getAttribute('href');
      if (href && !href.startsWith('http') && !href.startsWith('#')) {
        a.addEventListener('click', (e) => {
          e.preventDefault();
          // Resolve relative path
          const resolved = this._resolveLink(filePath, href);
          if (resolved) this.navigate(resolved);
        });
      }
    });

    // Home link in breadcrumbs
    pageEl.querySelectorAll('[data-nav="home"]').forEach(a => {
      a.addEventListener('click', (e) => { e.preventDefault(); this.showHome(); });
    });

    // Render TOC
    const tocEl = document.getElementById('toc-content');
    tocEl.innerHTML = Content.renderToc(page.toc);
    tocEl.querySelectorAll('a').forEach(a => {
      a.addEventListener('click', (e) => {
        e.preventDefault();
        const target = pageEl.querySelector(a.getAttribute('href'));
        if (target) target.scrollIntoView({ behavior: 'smooth' });
      });
    });

    // Update nav history
    if (addToHistory) {
      this._navHistory = this._navHistory.slice(0, this._navIndex + 1);
      this._navHistory.push(filePath);
      this._navIndex = this._navHistory.length - 1;
    }
    this._updateNavButtons();

    // Update bookmark button
    this.updateBookmarkButton();

    // Highlight in sidebar
    Sidebar.highlightActive(filePath);

    // Track in history store
    await Store.addToHistory({
      path: filePath,
      title: page.title,
      framework: page.framework,
    });

    // Save session
    await Store.saveSession({
      page: filePath,
      scrollY: 0,
      sidebarTab: Sidebar._currentTab,
    });

    // Update window title
    document.title = `${page.title} — Apple Docs`;
  },

  _resolveLink(currentPath, href) {
    // Pattern: ../com.apple.{bundle}/{Framework}/{path}.md
    // Example: ../com.apple.tvuikit/TVUIKit/TVCaptionButtonView/contentText.md
    // Resolves to: tvuikit/TVCaptionButtonView/contentText.md
    const appleMatch = href.match(/\.\.\/com\.apple\.[\w.]+\/(\w+)\/(.*)/);
    if (appleMatch) {
      const framework = appleMatch[1].toLowerCase(); // "TVUIKit" -> "tvuikit"
      const symbolPath = appleMatch[2]; // "TVCaptionButtonView/contentText.md"
      let result = `${framework}/${symbolPath}`;
      if (!result.endsWith('.md')) result += '.md';
      return result;
    }

    // Fallback: generic relative path resolution
    const currentParts = currentPath.split('/');
    currentParts.pop(); // Remove filename

    const hrefParts = href.split('/');
    const resolved = [...currentParts];

    for (const part of hrefParts) {
      if (part === '..') resolved.pop();
      else if (part !== '.') resolved.push(part);
    }

    let result = resolved.join('/');
    if (!result.endsWith('.md')) result += '.md';
    return result;
  },

  showHome() {
    this._currentPage = null;
    const pageEl = document.getElementById('page-content');

    // Build framework grid
    let cards = '';
    for (const fw of this._frameworks) {
      cards += `
        <div class="fw-card" data-framework="${fw.name}">
          <div class="fw-card-name">${fw.name}</div>
          <div class="fw-card-count">${fw.count.toLocaleString()} pages</div>
        </div>
      `;
    }

    // Recent history
    Store.getHistory().then(async history => {
      const recent = history.slice(0, 5);
      let recentHtml = '';
      if (recent.length > 0) {
        recentHtml = `
          <div class="home-section">
            <h3>Recently Viewed</h3>
            <div class="recent-list">
              ${recent.map(h => `
                <div class="recent-item" data-path="${h.path}">
                  <span class="recent-title">${h.title}</span>
                  <span class="recent-meta">${h.framework}</span>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      }

      const bookmarks = await Store.getBookmarks();
      let bookmarkHtml = '';
      if (bookmarks.length > 0) {
        const topBookmarks = bookmarks.slice(0, 5);
        bookmarkHtml = `
          <div class="home-section">
            <h3>Bookmarks</h3>
            <div class="recent-list">
              ${topBookmarks.map(b => `
                <div class="recent-item" data-path="${b.path}">
                  <span class="recent-title">${b.title}</span>
                  <span class="recent-meta">${b.framework}</span>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      }

      pageEl.innerHTML = `
        <div class="home">
          <h1 class="home-title">Apple Developer Documentation</h1>
          <p class="home-subtitle">${this._frameworks.length} Frameworks &middot; ${this._frameworks.reduce((s, f) => s + f.count, 0).toLocaleString()} Pages</p>
          ${recentHtml}
          ${bookmarkHtml}
          <div class="home-section">
            <h3>Frameworks</h3>
            <div class="fw-grid">${cards}</div>
          </div>
        </div>
      `;

      // Attach handlers
      pageEl.querySelectorAll('.fw-card').forEach(el => {
        el.addEventListener('click', () => {
          Sidebar.switchTab('frameworks');
          Sidebar.toggleFramework(el.dataset.framework);
        });
      });

      pageEl.querySelectorAll('.recent-item').forEach(el => {
        el.addEventListener('click', () => this.navigate(el.dataset.path));
      });
    });

    // Clear TOC
    document.getElementById('toc-content').innerHTML = '';
    document.title = 'Apple Developer Documentation';

    // Update bookmark button
    const btn = document.getElementById('btn-bookmark');
    btn.classList.remove('bookmarked');
    btn.innerHTML = '&#9734;';
  },

  goBack() {
    if (this._navIndex > 0) {
      this._navIndex--;
      this.navigate(this._navHistory[this._navIndex], false);
    }
  },

  goForward() {
    if (this._navIndex < this._navHistory.length - 1) {
      this._navIndex++;
      this.navigate(this._navHistory[this._navIndex], false);
    }
  },

  _updateNavButtons() {
    document.getElementById('btn-back').disabled = this._navIndex <= 0;
    document.getElementById('btn-forward').disabled = this._navIndex >= this._navHistory.length - 1;
  },

  _showError(msg) {
    document.getElementById('page-content').innerHTML = `
      <div class="error-state">
        <h2>Page Not Found</h2>
        <p>${msg}</p>
        <button onclick="App.showHome()">Go Home</button>
      </div>
    `;
  },

  // --- Bookmarks ---

  async toggleBookmark() {
    if (!this._currentPage) return;
    const path = this._currentPage.path;

    if (await Store.isBookmarked(path)) {
      await Store.removeBookmark(path);
    } else {
      await Store.addBookmark({
        path,
        title: this._currentPage.title,
        framework: this._currentPage.framework,
      });
    }

    this.updateBookmarkButton();
    // Refresh bookmarks tab if visible
    if (Sidebar._currentTab === 'bookmarks') {
      Sidebar.renderBookmarks(document.getElementById('sidebar-content'));
    }
  },

  async updateBookmarkButton() {
    const btn = document.getElementById('btn-bookmark');
    if (!this._currentPage) {
      btn.classList.remove('bookmarked');
      btn.innerHTML = '&#9734;';
      return;
    }
    const isBookmarked = await Store.isBookmarked(this._currentPage.path);
    btn.classList.toggle('bookmarked', isBookmarked);
    btn.innerHTML = isBookmarked ? '&#9733;' : '&#9734;';
  },

  // --- Theme ---

  async applyTheme(theme) {
    if (theme === 'system') {
      const osTheme = await window.api.getTheme();
      this._setThemeClass(osTheme);
    } else {
      this._setThemeClass(theme);
    }
  },

  _setThemeClass(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    const btn = document.getElementById('btn-theme');
    btn.innerHTML = theme === 'dark' ? '&#9790;' : '&#9728;';
  },

  async cycleTheme() {
    const prefs = await Store.getPreferences();
    const cycle = { light: 'dark', dark: 'system', system: 'light' };
    const next = cycle[prefs.theme] || 'light';
    await Store.setPreference('theme', next);
    this.applyTheme(next);
  },

  // --- Font size ---

  async applyFontSize(size) {
    document.documentElement.style.setProperty('--content-font-size', `${size}px`);
  },

  async changeFontSize(delta) {
    const prefs = await Store.getPreferences();
    const newSize = Math.max(12, Math.min(24, prefs.fontSize + delta));
    await Store.setPreference('fontSize', newSize);
    this.applyFontSize(newSize);
  },

  // --- TOC ---

  async applyTocVisible(visible) {
    document.getElementById('toc-panel').style.display = visible ? 'block' : 'none';
  },

  async toggleToc() {
    const prefs = await Store.getPreferences();
    const newVal = !prefs.tocVisible;
    await Store.setPreference('tocVisible', newVal);
    this.applyTocVisible(newVal);
  },

  // --- Scroll save ---

  async _saveScrollPosition() {
    if (!this._currentPage) return;
    const scrollY = document.getElementById('page-content').scrollTop;
    await Store.saveSession({
      page: this._currentPage.path,
      scrollY,
      sidebarTab: Sidebar._currentTab,
    });
  },

  // --- Shortcuts ---

  handleShortcut(action) {
    switch (action) {
      case 'search': Sidebar.focusSearch(); break;
      case 'home': this.showHome(); break;
      case 'bookmark': this.toggleBookmark(); break;
      case 'toggleToc': this.toggleToc(); break;
      case 'back': this.goBack(); break;
      case 'forward': this.goForward(); break;
      case 'fontIncrease': this.changeFontSize(1); break;
      case 'fontDecrease': this.changeFontSize(-1); break;
    }
  },
};

window.App = App;

// Boot
document.addEventListener('DOMContentLoaded', () => {
  App.init().catch(err => {
    console.error('App init failed:', err);
    document.getElementById('page-content').innerHTML = `
      <div class="error-state">
        <h2>Startup Error</h2>
        <pre style="text-align:left;background:var(--bg-code-block);color:var(--text-code);padding:16px;border-radius:8px;overflow:auto;margin-top:12px;">${err.stack || err}</pre>
      </div>
    `;
  });
});
