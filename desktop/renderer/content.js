// Content renderer — markdown to HTML with TOC generation

const Content = {
  _cache: new Map(), // LRU cache for rendered pages
  _cacheMax: 50,

  init() {
    // marked + highlight.js are configured in preload.js
    // and exposed via window.api.renderMarkdown()
  },

  async loadPage(filePath) {
    // Check cache
    if (this._cache.has(filePath)) {
      return this._cache.get(filePath);
    }

    const data = await window.api.readMarkdownFile(filePath);
    if (!data) return null;

    const html = window.api.renderMarkdown(data.content);
    const toc = this._extractToc(html);
    const framework = filePath.split('/')[0];

    const result = {
      html,
      toc,
      frontmatter: data.frontmatter,
      framework,
      path: filePath,
      title: data.frontmatter.title || filePath.split('/').pop().replace('.md', ''),
    };

    // Cache with LRU eviction
    if (this._cache.size >= this._cacheMax) {
      const oldest = this._cache.keys().next().value;
      this._cache.delete(oldest);
    }
    this._cache.set(filePath, result);

    return result;
  },

  _extractToc(html) {
    const toc = [];
    const regex = /<h([23])[^>]*(?:id="([^"]*)")?[^>]*>(.*?)<\/h[23]>/gi;
    let match;
    let counter = 0;

    while ((match = regex.exec(html)) !== null) {
      const level = parseInt(match[1]);
      const existingId = match[2];
      const text = match[3].replace(/<[^>]+>/g, '').trim();
      const id = existingId || `heading-${counter++}`;

      toc.push({ level, text, id });
    }

    return toc;
  },

  renderToc(toc) {
    if (!toc || toc.length === 0) return '';

    return toc.map(item => {
      const indent = item.level === 3 ? ' class="toc-sub"' : '';
      return `<a href="#${item.id}"${indent}>${this._escapeHtml(item.text)}</a>`;
    }).join('\n');
  },

  renderBreadcrumbs(filePath) {
    const parts = filePath.replace('.md', '').split('/');
    const crumbs = ['<a href="#" data-nav="home">Home</a>'];

    for (let i = 0; i < parts.length; i++) {
      const name = parts[i];
      if (i < parts.length - 1) {
        crumbs.push(`<span class="breadcrumb-sep">/</span><span class="breadcrumb-item">${this._escapeHtml(name)}</span>`);
      } else {
        crumbs.push(`<span class="breadcrumb-sep">/</span><span class="breadcrumb-current">${this._escapeHtml(name)}</span>`);
      }
    }

    return crumbs.join('');
  },

  renderPlatformBadges(frontmatter) {
    const platforms = frontmatter.platformsList || [];
    if (platforms.length === 0) {
      // Try parsing from the "platforms" string if present
      const pStr = frontmatter.platforms;
      if (pStr && pStr !== '[]') return '';
      return '';
    }

    return platforms.map(p =>
      `<span class="platform-badge">${this._escapeHtml(p)}</span>`
    ).join('');
  },

  renderRoleBadge(frontmatter) {
    const role = frontmatter.roleHeading || frontmatter.role;
    if (!role || role === 'symbol') return '';
    return `<span class="role-badge">${this._escapeHtml(role)}</span>`;
  },

  // Inject heading IDs into rendered HTML for TOC linking
  addHeadingIds(html) {
    let counter = 0;
    return html.replace(/<h([23])([^>]*)>/gi, (match, level, attrs) => {
      if (attrs.includes('id=')) return match;
      return `<h${level}${attrs} id="heading-${counter++}">`;
    });
  },

  _escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  },
};

window.Content = Content;
