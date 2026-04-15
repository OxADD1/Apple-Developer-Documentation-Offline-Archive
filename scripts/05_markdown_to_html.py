#!/usr/bin/env python3
"""
Apple Documentation HTML Generator
Creates a browsable, searchable HTML documentation site
"""

import json
import re
from pathlib import Path
from typing import List, Dict
import argparse
import markdown
import shutil


class HTMLGenerator:
    """Generates browsable HTML documentation"""

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.markdown_dir = self.base_dir / 'markdown'
        self.html_dir = self.base_dir / 'html'

        # Create HTML directory
        self.html_dir.mkdir(parents=True, exist_ok=True)

    def get_all_frameworks(self) -> List[str]:
        """Get list of all frameworks"""
        if not self.markdown_dir.exists():
            return []

        frameworks = [d.name for d in self.markdown_dir.iterdir() if d.is_dir()]
        return sorted(frameworks)

    def get_framework_files(self, framework: str) -> List[Path]:
        """Get all markdown files for a framework"""
        framework_dir = self.markdown_dir / framework
        if not framework_dir.exists():
            return []

        return sorted(framework_dir.rglob('*.md'))

    def convert_markdown_to_html(self, md_file: Path, framework: str) -> str:
        """Convert markdown file to HTML"""
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Remove YAML frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                content = parts[2].strip()

        # Convert to HTML
        html_content = markdown.markdown(
            content,
            extensions=['fenced_code', 'tables', 'toc', 'codehilite']
        )

        # Get relative path for title
        framework_dir = self.markdown_dir / framework
        rel_path = md_file.relative_to(framework_dir)
        title = str(rel_path.with_suffix(''))

        # Wrap in template
        return self.html_template(title, html_content, framework)

    def html_template(self, title: str, content: str, framework: str) -> str:
        """HTML page template"""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - {framework}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f7;
        }}

        .container {{
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background: white;
            min-height: 100vh;
        }}

        header {{
            background: #000;
            color: white;
            padding: 20px;
            margin: -20px -20px 20px -20px;
        }}

        header h1 {{
            font-size: 24px;
            font-weight: 600;
        }}

        header .breadcrumb {{
            font-size: 14px;
            opacity: 0.8;
            margin-top: 5px;
        }}

        header .breadcrumb a {{
            color: #0071e3;
            text-decoration: none;
        }}

        header .breadcrumb a:hover {{
            text-decoration: underline;
        }}

        .content {{
            padding: 20px 0;
        }}

        h1, h2, h3, h4, h5, h6 {{
            margin: 1.5em 0 0.5em 0;
            font-weight: 600;
        }}

        h1 {{ font-size: 2em; border-bottom: 1px solid #e5e5e5; padding-bottom: 0.3em; }}
        h2 {{ font-size: 1.5em; }}
        h3 {{ font-size: 1.25em; }}

        code {{
            background: #f5f5f7;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 0.9em;
        }}

        pre {{
            background: #1d1f21;
            color: #c5c8c6;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
            margin: 1em 0;
        }}

        pre code {{
            background: transparent;
            padding: 0;
            color: inherit;
        }}

        a {{
            color: #0071e3;
            text-decoration: none;
        }}

        a:hover {{
            text-decoration: underline;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1em 0;
        }}

        th, td {{
            border: 1px solid #e5e5e5;
            padding: 8px 12px;
            text-align: left;
        }}

        th {{
            background: #f5f5f7;
            font-weight: 600;
        }}

        blockquote {{
            border-left: 4px solid #0071e3;
            padding-left: 1em;
            margin: 1em 0;
            color: #666;
        }}

        ul, ol {{
            margin-left: 2em;
            margin-bottom: 1em;
        }}

        li {{
            margin: 0.5em 0;
        }}

        .back-link {{
            display: inline-block;
            margin-bottom: 20px;
            color: #0071e3;
            text-decoration: none;
        }}

        .back-link:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="breadcrumb">
                <a href="../../index.html">Home</a> ›
                <a href="../index.html">{framework}</a> ›
                {title}
            </div>
            <h1>{title}</h1>
        </header>

        <div class="content">
            <a href="../index.html" class="back-link">← Back to {framework}</a>
            {content}
        </div>
    </div>
</body>
</html>
"""

    def generate_framework_index(self, framework: str, files: List[Path]) -> str:
        """Generate index page for a framework"""
        items = []
        framework_dir = self.markdown_dir / framework

        for md_file in files:
            rel_path = md_file.relative_to(framework_dir)
            html_path = rel_path.with_suffix('.html')
            title = rel_path.stem

            items.append(f'<li><a href="{html_path}">{title}</a></li>')

        items_html = '\n'.join(items)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{framework} Documentation</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 40px 20px;
            background: #f5f5f7;
        }}

        .container {{
            background: white;
            padding: 40px;
            border-radius: 12px;
        }}

        h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}

        .subtitle {{
            color: #666;
            margin-bottom: 30px;
        }}

        .search {{
            margin: 20px 0;
        }}

        .search input {{
            width: 100%;
            padding: 12px;
            font-size: 16px;
            border: 1px solid #ddd;
            border-radius: 6px;
        }}

        ul {{
            list-style: none;
            padding: 0;
        }}

        li {{
            margin: 8px 0;
        }}

        li a {{
            color: #0071e3;
            text-decoration: none;
            display: block;
            padding: 8px;
            border-radius: 4px;
        }}

        li a:hover {{
            background: #f5f5f7;
        }}

        .back-link {{
            display: inline-block;
            margin-bottom: 20px;
            color: #0071e3;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="../index.html" class="back-link">← Back to Home</a>
        <h1>{framework}</h1>
        <div class="subtitle">{len(files)} pages</div>

        <div class="search">
            <input type="text" id="search" placeholder="Search..." onkeyup="filterList()">
        </div>

        <ul id="fileList">
            {items_html}
        </ul>
    </div>

    <script>
        function filterList() {{
            const input = document.getElementById('search');
            const filter = input.value.toLowerCase();
            const ul = document.getElementById('fileList');
            const li = ul.getElementsByTagName('li');

            for (let i = 0; i < li.length; i++) {{
                const a = li[i].getElementsByTagName('a')[0];
                const txtValue = a.textContent || a.innerText;
                if (txtValue.toLowerCase().indexOf(filter) > -1) {{
                    li[i].style.display = '';
                }} else {{
                    li[i].style.display = 'none';
                }}
            }}
        }}
    </script>
</body>
</html>
"""

    def generate_main_index(self, frameworks: Dict[str, int]) -> str:
        """Generate main index page"""
        items = []
        for framework, count in sorted(frameworks.items()):
            items.append(f'<li><a href="{framework}/index.html">{framework} <span class="count">({count} pages)</span></a></li>')

        items_html = '\n'.join(items)
        total = sum(frameworks.values())

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Apple Developer Documentation - Offline Archive</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 40px 20px;
            background: #f5f5f7;
        }}

        .container {{
            background: white;
            padding: 60px 40px;
            border-radius: 12px;
            text-align: center;
        }}

        h1 {{
            font-size: 3em;
            margin-bottom: 10px;
        }}

        .subtitle {{
            color: #666;
            font-size: 1.2em;
            margin-bottom: 40px;
        }}

        .stats {{
            background: #f5f5f7;
            padding: 20px;
            border-radius: 8px;
            margin: 30px 0;
        }}

        ul {{
            list-style: none;
            padding: 0;
            text-align: left;
            margin-top: 40px;
        }}

        li {{
            margin: 12px 0;
        }}

        li a {{
            color: #0071e3;
            text-decoration: none;
            display: block;
            padding: 15px;
            border-radius: 6px;
            border: 1px solid #e5e5e5;
            font-size: 1.1em;
        }}

        li a:hover {{
            background: #f5f5f7;
            border-color: #0071e3;
        }}

        .count {{
            float: right;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🍎 Apple Developer Documentation</h1>
        <div class="subtitle">Complete Offline Archive</div>

        <div class="stats">
            <strong>{len(frameworks)}</strong> Frameworks •
            <strong>{total:,}</strong> Pages •
            <a href="search.html" style="color: #0071e3; text-decoration: none;">Search All</a>
        </div>

        <ul>
            {items_html}
        </ul>
    </div>
</body>
</html>
"""

    def strip_markdown(self, content: str) -> str:
        """Strip markdown syntax to get plain text for search indexing"""
        # Remove YAML frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                content = parts[2]

        # Remove code blocks
        content = re.sub(r'```[\s\S]*?```', '', content)
        content = re.sub(r'`[^`]+`', '', content)
        # Remove headings markers
        content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
        # Remove bold/italic
        content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)
        content = re.sub(r'\*([^*]+)\*', r'\1', content)
        # Remove links but keep text
        content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)
        # Remove images
        content = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', content)
        # Remove blockquote markers
        content = re.sub(r'^>\s+', '', content, flags=re.MULTILINE)
        # Remove list markers
        content = re.sub(r'^[-*+]\s+', '', content, flags=re.MULTILINE)
        content = re.sub(r'^\d+\.\s+', '', content, flags=re.MULTILINE)
        # Collapse whitespace
        content = re.sub(r'\n{2,}', '\n', content)
        content = re.sub(r'  +', ' ', content)

        return content.strip()

    def build_search_entry(self, md_file: Path, framework: str) -> dict:
        """Build a search index entry from a markdown file"""
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except IOError:
            return None

        # Extract title from YAML frontmatter or first heading
        title = md_file.stem
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                for line in parts[1].splitlines():
                    if line.strip().startswith('title:'):
                        extracted = line.split(':', 1)[1].strip().strip('"').strip("'")
                        if extracted:
                            title = extracted
                        break

        # Get plain text snippet
        plain = self.strip_markdown(content)
        snippet = plain[:200].replace('"', '\\"') if plain else ''

        # Get relative HTML path
        framework_dir = self.markdown_dir / framework
        rel_path = md_file.relative_to(framework_dir)
        html_path = f'{framework}/{rel_path.with_suffix(".html")}'

        return {
            'title': title,
            'path': html_path,
            'framework': framework,
            'snippet': snippet,
        }

    def build_search_indices(self, framework_stats: Dict[str, int]):
        """Build search index JSON files for all frameworks"""
        print("\nBuilding search indices...")

        all_entries = []

        for framework in sorted(framework_stats.keys()):
            files = self.get_framework_files(framework)
            framework_entries = []

            for md_file in files:
                entry = self.build_search_entry(md_file, framework)
                if entry:
                    framework_entries.append(entry)

            # Per-framework index
            fw_index_dir = self.html_dir / framework
            fw_index_dir.mkdir(parents=True, exist_ok=True)
            with open(fw_index_dir / 'search-index.json', 'w', encoding='utf-8') as f:
                json.dump(framework_entries, f)

            all_entries.extend(framework_entries)

        # Global index
        with open(self.html_dir / 'search-index.json', 'w', encoding='utf-8') as f:
            json.dump(all_entries, f)

        print(f"  Global index: {len(all_entries)} entries")
        print(f"  Per-framework indices: {len(framework_stats)} files")

    def generate_search_page(self, frameworks: Dict[str, int]) -> str:
        """Generate the global search.html page"""
        framework_options = '\n'.join(
            f'<option value="{fw}">{fw} ({count})</option>'
            for fw, count in sorted(frameworks.items())
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Search - Apple Developer Documentation</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f7;
            color: #333;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .header h1 {{ font-size: 2em; margin-bottom: 5px; }}
        .header .subtitle {{ color: #666; }}
        .back-link {{
            display: inline-block;
            margin-bottom: 20px;
            color: #0071e3;
            text-decoration: none;
        }}
        .back-link:hover {{ text-decoration: underline; }}
        .search-box {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }}
        .search-box input {{
            flex: 1;
            padding: 14px 16px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 8px;
            outline: none;
        }}
        .search-box input:focus {{ border-color: #0071e3; }}
        .search-box select {{
            padding: 14px 12px;
            font-size: 14px;
            border: 2px solid #ddd;
            border-radius: 8px;
            background: white;
            min-width: 150px;
        }}
        .stats {{
            color: #666;
            font-size: 14px;
            margin-bottom: 15px;
        }}
        .results {{ list-style: none; }}
        .result {{
            background: white;
            padding: 16px;
            margin-bottom: 8px;
            border-radius: 8px;
            border: 1px solid #e5e5e5;
        }}
        .result:hover {{ border-color: #0071e3; }}
        .result a {{
            color: #0071e3;
            text-decoration: none;
            font-size: 1.1em;
            font-weight: 500;
        }}
        .result a:hover {{ text-decoration: underline; }}
        .result .badge {{
            display: inline-block;
            background: #f0f0f0;
            color: #666;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            margin-left: 8px;
        }}
        .result .snippet {{
            color: #555;
            font-size: 14px;
            margin-top: 6px;
            line-height: 1.4;
        }}
        .result .snippet mark {{
            background: #fff3cd;
            padding: 0 2px;
            border-radius: 2px;
        }}
        .no-results {{
            text-align: center;
            padding: 40px;
            color: #666;
        }}
        .loading {{
            text-align: center;
            padding: 40px;
            color: #999;
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="index.html" class="back-link">&larr; Back to Home</a>
        <div class="header">
            <h1>Search Documentation</h1>
            <div class="subtitle">Search across all frameworks</div>
        </div>

        <div class="search-box">
            <input type="text" id="searchInput" placeholder="Search..." autofocus>
            <select id="frameworkFilter">
                <option value="">All Frameworks</option>
                {framework_options}
            </select>
        </div>

        <div id="stats" class="stats"></div>
        <ul id="results" class="results">
            <li class="loading">Loading search index...</li>
        </ul>
    </div>

    <script>
        let searchIndex = [];
        let debounceTimer = null;

        // Load search index
        fetch('search-index.json')
            .then(r => r.json())
            .then(data => {{
                searchIndex = data;
                document.getElementById('results').innerHTML = '';
                document.getElementById('stats').textContent =
                    searchIndex.length.toLocaleString() + ' pages indexed';
            }})
            .catch(() => {{
                document.getElementById('results').innerHTML =
                    '<li class="no-results">Failed to load search index.</li>';
            }});

        function scoreEntry(entry, tokens) {{
            let score = 0;
            const titleLower = entry.title.toLowerCase();
            const snippetLower = (entry.snippet || '').toLowerCase();
            for (const token of tokens) {{
                if (titleLower === token) score += 100;
                else if (titleLower.startsWith(token)) score += 60;
                else if (titleLower.includes(token)) score += 40;
                if (snippetLower.includes(token)) score += 10;
            }}
            return score;
        }}

        function highlightText(text, tokens) {{
            if (!text) return '';
            let result = text;
            for (const token of tokens) {{
                const regex = new RegExp('(' + token.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&') + ')', 'gi');
                result = result.replace(regex, '<mark>$1</mark>');
            }}
            return result;
        }}

        function doSearch() {{
            const query = document.getElementById('searchInput').value.trim().toLowerCase();
            const framework = document.getElementById('frameworkFilter').value;
            const resultsEl = document.getElementById('results');
            const statsEl = document.getElementById('stats');

            if (!query) {{
                resultsEl.innerHTML = '';
                statsEl.textContent = searchIndex.length.toLocaleString() + ' pages indexed';
                return;
            }}

            const tokens = query.split(/\\s+/).filter(t => t.length > 0);

            let filtered = searchIndex;
            if (framework) {{
                filtered = filtered.filter(e => e.framework === framework);
            }}

            const scored = filtered
                .map(entry => ({{ entry, score: scoreEntry(entry, tokens) }}))
                .filter(x => x.score > 0)
                .sort((a, b) => b.score - a.score)
                .slice(0, 50);

            if (scored.length === 0) {{
                resultsEl.innerHTML = '<li class="no-results">No results found.</li>';
                statsEl.textContent = '0 results';
                return;
            }}

            statsEl.textContent = scored.length + (scored.length === 50 ? '+' : '') + ' results';

            resultsEl.innerHTML = scored.map(x => {{
                const e = x.entry;
                const title = highlightText(e.title, tokens);
                const snippet = highlightText(e.snippet || '', tokens);
                return '<li class="result">' +
                    '<a href="' + e.path + '">' + title + '</a>' +
                    '<span class="badge">' + e.framework + '</span>' +
                    (snippet ? '<div class="snippet">' + snippet + '</div>' : '') +
                    '</li>';
            }}).join('');
        }}

        document.getElementById('searchInput').addEventListener('input', function() {{
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(doSearch, 200);
        }});

        document.getElementById('frameworkFilter').addEventListener('change', doSearch);

        // Handle URL params
        const params = new URLSearchParams(window.location.search);
        if (params.get('q')) {{
            document.getElementById('searchInput').value = params.get('q');
            setTimeout(doSearch, 500);
        }}
    </script>
</body>
</html>
"""

    def generate_html(self, frameworks: List[str] = None):
        """Generate HTML documentation"""
        if frameworks is None:
            frameworks = self.get_all_frameworks()

        if not frameworks:
            print("No frameworks found")
            return

        print(f"\nGenerating HTML documentation for {len(frameworks)} frameworks...")

        framework_stats = {}

        for framework in frameworks:
            print(f"\nProcessing {framework}...")

            files = self.get_framework_files(framework)
            if not files:
                print(f"  No files found for {framework}")
                continue

            framework_stats[framework] = len(files)
            print(f"  Found {len(files)} files")

            # Create framework directory
            framework_html_dir = self.html_dir / framework
            framework_html_dir.mkdir(parents=True, exist_ok=True)

            # Convert all markdown files
            for i, md_file in enumerate(files, 1):
                if i % 100 == 0:
                    print(f"  Converted {i}/{len(files)} files...")

                try:
                    html_content = self.convert_markdown_to_html(md_file, framework)

                    # Save HTML file
                    framework_dir = self.markdown_dir / framework
                    rel_path = md_file.relative_to(framework_dir)
                    html_file = framework_html_dir / rel_path.with_suffix('.html')
                    html_file.parent.mkdir(parents=True, exist_ok=True)

                    with open(html_file, 'w', encoding='utf-8') as f:
                        f.write(html_content)

                except Exception as e:
                    print(f"  Error converting {md_file}: {e}")

            # Generate framework index
            index_html = self.generate_framework_index(framework, files)
            index_file = framework_html_dir / 'index.html'
            with open(index_file, 'w', encoding='utf-8') as f:
                f.write(index_html)

        # Generate main index
        main_index = self.generate_main_index(framework_stats)
        main_index_file = self.html_dir / 'index.html'
        with open(main_index_file, 'w', encoding='utf-8') as f:
            f.write(main_index)

        # Build search indices
        self.build_search_indices(framework_stats)

        # Generate search page
        search_page = self.generate_search_page(framework_stats)
        with open(self.html_dir / 'search.html', 'w', encoding='utf-8') as f:
            f.write(search_page)

        print("\n" + "="*70)
        print("HTML Documentation Generated!")
        print("="*70)
        print(f"\nOpen: {main_index_file}")
        print(f"Search: {self.html_dir / 'search.html'}")
        print(f"\nTotal frameworks: {len(framework_stats)}")
        print(f"Total pages: {sum(framework_stats.values()):,}")


def main():
    parser = argparse.ArgumentParser(description='Generate HTML documentation')
    parser.add_argument('--frameworks', nargs='+', help='Frameworks to convert (default: all)')
    parser.add_argument('--base-dir', default='.', help='Base directory')

    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent / args.base_dir if args.base_dir == '.' else Path(args.base_dir)

    generator = HTMLGenerator(base_dir=base_dir)
    generator.generate_html(frameworks=args.frameworks)

    print("\nNext: Open html/index.html in your browser!")


if __name__ == '__main__':
    main()
