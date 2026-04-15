// Sidebar — framework tree, search, bookmarks, history tabs

const Sidebar = {
  _frameworks: [],
  _expandedDirs: new Set(),
  _currentTab: 'frameworks',
  _treeCache: new Map(),

  async init() {
    this._frameworks = await window.api.getFrameworks();
    this.renderTabs();
    this.switchTab('frameworks');
  },

  renderTabs() {
    const tabs = document.getElementById('sidebar-tabs');
    tabs.innerHTML = `
      <button data-tab="frameworks" class="active">Frameworks</button>
      <button data-tab="search">Search</button>
      <button data-tab="bookmarks">Bookmarks</button>
      <button data-tab="history">History</button>
    `;

    tabs.querySelectorAll('button').forEach(btn => {
      btn.addEventListener('click', () => this.switchTab(btn.dataset.tab));
    });
  },

  switchTab(tab) {
    this._currentTab = tab;
    document.querySelectorAll('#sidebar-tabs button').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === tab);
    });

    const content = document.getElementById('sidebar-content');

    switch (tab) {
      case 'frameworks': this.renderFrameworks(content); break;
      case 'search': this.renderSearch(content); break;
      case 'bookmarks': this.renderBookmarks(content); break;
      case 'history': this.renderHistory(content); break;
    }
  },

  // --- Frameworks tab ---

  renderFrameworks(container) {
    let html = '<div class="tree">';
    for (const fw of this._frameworks) {
      const expanded = this._expandedDirs.has(fw.name);
      html += `
        <div class="tree-item tree-framework" data-framework="${fw.name}">
          <span class="tree-toggle">${expanded ? '&#9660;' : '&#9654;'}</span>
          <span class="tree-label">${fw.name}</span>
          <span class="tree-count">${fw.count.toLocaleString()}</span>
        </div>
        <div class="tree-children" id="tree-${fw.name}" style="display: ${expanded ? 'block' : 'none'}"></div>
      `;
    }
    html += '</div>';
    container.innerHTML = html;

    // Attach click handlers
    container.querySelectorAll('.tree-framework').forEach(el => {
      el.addEventListener('click', () => this.toggleFramework(el.dataset.framework));
    });
  },

  async toggleFramework(framework) {
    const childrenEl = document.getElementById(`tree-${framework}`);
    if (!childrenEl) return;

    if (this._expandedDirs.has(framework)) {
      this._expandedDirs.delete(framework);
      childrenEl.style.display = 'none';
      childrenEl.previousElementSibling.querySelector('.tree-toggle').innerHTML = '&#9654;';
    } else {
      this._expandedDirs.add(framework);
      childrenEl.style.display = 'block';
      childrenEl.previousElementSibling.querySelector('.tree-toggle').innerHTML = '&#9660;';

      if (!childrenEl.dataset.loaded) {
        childrenEl.innerHTML = '<div class="tree-loading">Loading...</div>';
        await this.loadTreeChildren(framework, '', childrenEl);
        childrenEl.dataset.loaded = 'true';
      }
    }
  },

  async loadTreeChildren(framework, subpath, container) {
    const cacheKey = `${framework}/${subpath}`;
    let items = this._treeCache.get(cacheKey);

    if (!items) {
      items = await window.api.getTree(framework, subpath);
      this._treeCache.set(cacheKey, items);
    }

    let html = '';
    for (const item of items) {
      const fullPath = `${framework}/${item.path}`;
      if (item.type === 'dir') {
        html += `
          <div class="tree-item tree-dir" data-framework="${framework}" data-path="${item.path}">
            <span class="tree-toggle">&#9654;</span>
            <span class="tree-label">${item.name}</span>
          </div>
          <div class="tree-children" id="tree-${framework}-${item.path.replace(/\//g, '-')}" style="display:none"></div>
        `;
      } else {
        html += `
          <div class="tree-item tree-file" data-path="${fullPath}">
            <span class="tree-label">${item.name}</span>
          </div>
        `;
      }
    }
    container.innerHTML = html;

    // Attach handlers
    container.querySelectorAll('.tree-dir').forEach(el => {
      el.addEventListener('click', async () => {
        const fw = el.dataset.framework;
        const p = el.dataset.path;
        const childId = `tree-${fw}-${p.replace(/\//g, '-')}`;
        const childEl = document.getElementById(childId);
        if (!childEl) return;

        const isExpanded = childEl.style.display !== 'none';
        childEl.style.display = isExpanded ? 'none' : 'block';
        el.querySelector('.tree-toggle').innerHTML = isExpanded ? '&#9654;' : '&#9660;';

        if (!childEl.dataset.loaded) {
          childEl.innerHTML = '<div class="tree-loading">Loading...</div>';
          await this.loadTreeChildren(fw, p, childEl);
          childEl.dataset.loaded = 'true';
        }
      });
    });

    container.querySelectorAll('.tree-file').forEach(el => {
      el.addEventListener('click', () => {
        window.App.navigate(el.dataset.path);
      });
    });
  },

  highlightActive(path) {
    document.querySelectorAll('.tree-file').forEach(el => {
      el.classList.toggle('active', el.dataset.path === path);
    });
  },

  // --- Search tab ---

  renderSearch(container) {
    container.innerHTML = `
      <div class="search-panel">
        <input type="text" id="sidebar-search-input" placeholder="Search documentation..." autofocus>
        <div id="sidebar-search-stats" class="search-stats"></div>
        <div id="sidebar-search-results" class="search-results"></div>
      </div>
    `;

    const input = document.getElementById('sidebar-search-input');
    let timer;
    input.addEventListener('input', () => {
      clearTimeout(timer);
      timer = setTimeout(() => this._doSearch(input.value), 200);
    });

    // Load index in background
    Search.ensureLoaded().then(() => {
      const stats = document.getElementById('sidebar-search-stats');
      if (stats) stats.textContent = `${Search.getCount().toLocaleString()} pages indexed`;
    });
  },

  _doSearch(query) {
    const results = Search.query(query);
    const container = document.getElementById('sidebar-search-results');
    const stats = document.getElementById('sidebar-search-stats');

    if (!query.trim()) {
      container.innerHTML = '';
      stats.textContent = `${Search.getCount().toLocaleString()} pages indexed`;
      return;
    }

    stats.textContent = `${results.length}${results.length === 50 ? '+' : ''} results`;

    container.innerHTML = results.map(r => `
      <div class="search-result" data-path="${r.framework}/${r.path.replace(/\.html$/, '.md').replace(/^[^/]+\//, '')}">
        <div class="search-result-title">${this._escapeHtml(r.title)}</div>
        <span class="search-result-badge">${r.framework}</span>
        ${r.snippet ? `<div class="search-result-snippet">${this._escapeHtml(r.snippet.substring(0, 120))}</div>` : ''}
      </div>
    `).join('');

    container.querySelectorAll('.search-result').forEach(el => {
      el.addEventListener('click', () => window.App.navigate(el.dataset.path));
    });
  },

  focusSearch() {
    this.switchTab('search');
    setTimeout(() => {
      const input = document.getElementById('sidebar-search-input');
      if (input) input.focus();
    }, 50);
  },

  // --- Bookmarks tab ---

  async renderBookmarks(container) {
    const bookmarks = await Store.getBookmarks();

    if (bookmarks.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">&#9734;</div>
          <div>No bookmarks yet</div>
          <div class="empty-hint">Press Cmd+D to bookmark a page</div>
        </div>
      `;
      return;
    }

    // Group by framework
    const grouped = {};
    for (const b of bookmarks) {
      const fw = b.framework || 'other';
      if (!grouped[fw]) grouped[fw] = [];
      grouped[fw].push(b);
    }

    let html = `<div class="bookmark-header">
      <span>${bookmarks.length} bookmark${bookmarks.length !== 1 ? 's' : ''}</span>
      <button class="link-btn" id="clear-bookmarks">Clear All</button>
    </div>`;

    for (const [fw, items] of Object.entries(grouped).sort()) {
      html += `<div class="bookmark-group-title">${fw}</div>`;
      for (const item of items) {
        html += `
          <div class="bookmark-item" data-path="${item.path}">
            <span class="bookmark-title">${this._escapeHtml(item.title)}</span>
            <button class="bookmark-remove" data-path="${item.path}" title="Remove">&times;</button>
          </div>
        `;
      }
    }

    container.innerHTML = html;

    container.querySelectorAll('.bookmark-item').forEach(el => {
      el.addEventListener('click', (e) => {
        if (e.target.classList.contains('bookmark-remove')) return;
        window.App.navigate(el.dataset.path);
      });
    });

    container.querySelectorAll('.bookmark-remove').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        await Store.removeBookmark(btn.dataset.path);
        this.renderBookmarks(container);
        window.App.updateBookmarkButton();
      });
    });

    const clearBtn = document.getElementById('clear-bookmarks');
    if (clearBtn) {
      clearBtn.addEventListener('click', async () => {
        await Store.clearBookmarks();
        this.renderBookmarks(container);
        window.App.updateBookmarkButton();
      });
    }
  },

  // --- History tab ---

  async renderHistory(container) {
    const history = await Store.getHistory();

    if (history.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">&#128337;</div>
          <div>No history yet</div>
          <div class="empty-hint">Start browsing documentation</div>
        </div>
      `;
      return;
    }

    let html = `<div class="bookmark-header">
      <span>${history.length} page${history.length !== 1 ? 's' : ''}</span>
      <button class="link-btn" id="clear-history">Clear</button>
    </div>`;

    for (const item of history) {
      const timeAgo = this._timeAgo(item.viewedAt);
      html += `
        <div class="history-item" data-path="${item.path}">
          <span class="history-title">${this._escapeHtml(item.title)}</span>
          <span class="history-meta">${item.framework} &middot; ${timeAgo}</span>
        </div>
      `;
    }

    container.innerHTML = html;

    container.querySelectorAll('.history-item').forEach(el => {
      el.addEventListener('click', () => window.App.navigate(el.dataset.path));
    });

    const clearBtn = document.getElementById('clear-history');
    if (clearBtn) {
      clearBtn.addEventListener('click', async () => {
        await Store.clearHistory();
        this.renderHistory(container);
      });
    }
  },

  _timeAgo(iso) {
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    if (days < 30) return `${days}d ago`;
    return new Date(iso).toLocaleDateString();
  },

  _escapeHtml(str) {
    return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  },
};

window.Sidebar = Sidebar;
