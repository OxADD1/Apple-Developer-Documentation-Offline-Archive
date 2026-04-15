// Search engine — loads index once, queries in memory

const Search = {
  _index: null,
  _loading: false,

  async ensureLoaded() {
    if (this._index) return;
    if (this._loading) {
      // Wait for loading to finish
      while (this._loading) await new Promise(r => setTimeout(r, 50));
      return;
    }
    this._loading = true;
    try {
      this._index = await window.api.getSearchIndex();
    } catch (e) {
      this._index = [];
    }
    this._loading = false;
  },

  query(text, framework = null, limit = 50) {
    if (!this._index || !text.trim()) return [];

    const tokens = text.toLowerCase().split(/\s+/).filter(t => t.length > 0);

    let entries = this._index;
    if (framework) {
      entries = entries.filter(e => e.framework === framework);
    }

    const scored = [];
    for (const entry of entries) {
      let score = 0;
      const titleLower = entry.title.toLowerCase();
      const snippetLower = (entry.snippet || '').toLowerCase();

      for (const token of tokens) {
        if (titleLower === token) score += 100;
        else if (titleLower.startsWith(token)) score += 60;
        else if (titleLower.includes(token)) score += 40;
        if (snippetLower.includes(token)) score += 10;
      }

      if (score > 0) {
        scored.push({ ...entry, score });
      }
    }

    scored.sort((a, b) => b.score - a.score);
    return scored.slice(0, limit);
  },

  getCount() {
    return this._index ? this._index.length : 0;
  },
};

window.Search = Search;
