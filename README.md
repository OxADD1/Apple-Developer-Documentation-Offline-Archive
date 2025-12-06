# Apple Developer Documentation Offline Archive

Download and maintain a complete offline archive of Apple Developer Documentation in AI-optimized formats (Markdown + JSON), with git-like incremental updates.

## Features

- **Offline Access** - Complete documentation available without internet
- **AI-Optimized** - Clean Markdown format perfect for AI/LLM processing
- **Git-Like Updates** - Incremental updates with `check`, `pull`, and `status` commands
- **Multiple Formats** - Raw JSON + AI-friendly Markdown
- **Smart Caching** - Only downloads changed pages using ETags
- **Resume Support** - Continue interrupted downloads
- **Framework Selection** - Download only what you need

## Quick Start

```bash
# Clone or download this repository
git clone https://github.com/OxADD1/Apple-Developer-Documentation-Offline-Archive.git
cd Apple-Developer-Documentation-Offline-Archive

# Setup
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r scripts/requirements.txt

# Download Swift documentation (test with one framework)
python scripts/01_discover_docs.py --frameworks swift
python scripts/02_download_json.py --frameworks swift
python scripts/03_json_to_markdown.py --frameworks swift

# Later: Check for updates
python scripts/update_check.py
python scripts/update_pull.py
```

## Installation

### Prerequisites

- Python 3.8+
- 5-10 GB free disk space (depending on frameworks)
- Internet connection for initial download

### Setup

1. **Create Virtual Environment**

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install Dependencies**

```bash
pip install -r scripts/requirements.txt
```

3. **Optional: PDF Support** (not required for Markdown/JSON)

```bash
playwright install chromium
```

## Usage

### Initial Download

#### Step 1: Discover Documentation

Crawls Apple's API to discover all available documentation pages.

**Important:** The discovery process respects framework boundaries.
- If you run it without arguments, it will crawl all default frameworks.
- If you specify frameworks (e.g., `--frameworks swift`), it will **only** crawl those specific frameworks.
- Cross-framework references are intentionally ignored to allow selective downloads.

```bash
# Discover all default frameworks (swift, swiftui, uikit, foundation, etc.)
python scripts/01_discover_docs.py

# Discover specific frameworks only
python scripts/01_discover_docs.py --frameworks swift swiftui

# Resume interrupted discovery
python scripts/01_discover_docs.py --resume
```

**Duration:** 1-3 hours
**Output:** `index.json` with complete documentation hierarchy

#### Step 2: Download JSON

Downloads all discovered pages as JSON files:

```bash
# All frameworks
python scripts/02_download_json.py

# Specific frameworks
python scripts/02_download_json.py --frameworks swift swiftui
```

**Duration:** 4-12 hours (rate limited at 5 req/sec)
**Output:**
- `raw-json/` - Original Apple JSON
- `.docsync/manifest.json` - Metadata for update tracking

#### Step 3: Convert to Markdown

Converts JSON to clean, AI-readable Markdown:

```bash
# All frameworks
python scripts/03_json_to_markdown.py

# Specific frameworks
python scripts/03_json_to_markdown.py --frameworks swift swiftui
```

**Duration:** 1-3 hours
**Output:** `markdown/` - Markdown files with YAML frontmatter

### Update System (Git-Like)

#### Check for Updates (`git fetch`)

```bash
python scripts/update_check.py
```

**Output:**
```
✓ Checking for updates...

Updates available:
[CHANGED] SwiftUI/TabView - Navigation updates for iOS 18
[CHANGED] Swift/Array - Performance improvements documentation
...

Total: 12 modified pages
To download: python scripts/update_pull.py
```

#### Show Status (`git status`)

```bash
python scripts/update_status.py
```

Shows current documentation state, last update check, and available updates.

#### Pull Updates (`git pull`)

```bash
# Download all updates
python scripts/update_pull.py

# Specific framework only
python scripts/update_pull.py --frameworks swiftui

# Skip markdown conversion
python scripts/update_pull.py --no-convert
```

**Output:**
- Updated JSON and Markdown files
- Changelog in `.docsync/changelog/`
- Version snapshot

## Directory Structure

```
apple-docs-offline/
├── scripts/
│   ├── 01_discover_docs.py    # Recursive documentation crawler
│   ├── 02_download_json.py    # JSON downloader with manifest
│   ├── 03_json_to_markdown.py # JSON → Markdown converter
│   ├── 04_markdown_to_pdf.py  # Generate PDFs from Markdown
│   ├── 05_markdown_to_html.py # Generate browsable HTML site
│   ├── update_check.py        # Check for updates (git fetch)
│   ├── update_pull.py         # Download updates (git pull)
│   ├── update_status.py       # Show status (git status)
│   └── requirements.txt       # Python dependencies
│
├── markdown/                  # AI-optimized Markdown
│   ├── swift/
│   │   ├── Array.md
│   │   ├── String.md
│   │   └── ... (~30,000 files)
│   ├── swiftui/
│   │   ├── View.md
│   │   └── ... (~5,000 files)
│   └── ... (8 more frameworks)
│
├── pdf/                       # Human-readable PDFs
│   ├── swift_documentation.pdf
│   ├── swiftui_documentation.pdf
│   └── ... (one per framework)
│
├── html/                      # Browsable HTML documentation
│   ├── index.html
│   ├── swift/
│   │   ├── index.html
│   │   └── ...
│   └── ...
│
├── raw-json/                  # Original Apple JSON (backup)
│   ├── swift/
│   ├── swiftui/
│   └── ...
│
├── .docsync/                  # Update tracking metadata
│   ├── manifest.json          # All pages with ETags/hashes
│   ├── versions/              # Version snapshots
│   ├── changelog/             # Update changelogs
│   └── cache/                 # Update check cache
│
├── index.json                 # Discovery index
├── README.md                  # This file
└── venv/                      # Python virtual environment
```

## Supported Frameworks

The following frameworks are supported by default:

| Framework | Description |
|-----------|-------------|
| **swift** | Swift Language Documentation |
| **swiftui** | SwiftUI Framework |
| **uikit** | UIKit Framework |
| **foundation** | Foundation Framework |
| **coredata** | Core Data Framework |
| **combine** | Combine Framework |
| **swiftdata** | SwiftData Framework |
| **coreml** | Core ML Framework |
| **mapkit** | MapKit Framework |
| **avfoundation** | AVFoundation Framework |

You can add more frameworks by editing `FRAMEWORK_ROOTS` in `scripts/01_discover_docs.py`.

## AI/LLM Integration

The Markdown output is optimized for AI processing:

- **YAML Frontmatter** - Structured metadata (title, role, platforms)
- **Clean Hierarchy** - Proper heading levels, lists, code blocks
- **Code Highlighting** - Syntax information preserved
- **Cross-References** - Relative links to related documentation
- **No HTML** - Pure Markdown for easy parsing

### Example: Using with AI

```
Read the SwiftUI View documentation:
markdown/swiftui/view.md

Explain the main protocol requirements.
```

### Example: Vector Database Indexing

```python
import os
from pathlib import Path

# Load all markdown files
docs_dir = Path("markdown")
for md_file in docs_dir.rglob("*.md"):
    with open(md_file) as f:
        content = f.read()
        # Add to your vector database
        # vector_db.add(content, metadata={"source": str(md_file)})
```

## Storage Requirements

| Component | Size |
|-----------|------|
| JSON (`raw-json/`) | ~2-3 GB |
| Markdown (`markdown/`) | ~1-2 GB |
| **Total** | **~3-5 GB** |

## Rate Limiting & Performance

All scripts implement respectful rate limiting:

- **Discovery:** 5 requests/second
- **Download:** 5 requests/second with exponential backoff
- **Update Check:** 10 requests/second (HEAD requests only)

## Troubleshooting

### "Manifest file not found"

The manifest is created during the first download:

```bash
python scripts/02_download_json.py
```

### "No update check found"

Run an update check first:

```bash
python scripts/update_check.py
```

### Rate Limiting (429 errors)

Scripts automatically retry with backoff. If issues persist:
- Wait 10-15 minutes
- Resume with `--resume` flag (for discovery)

### Missing Dependencies

```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r scripts/requirements.txt
```

## Advanced Usage

### Test with Single Framework

For faster testing, download only one framework:

```bash
python scripts/01_discover_docs.py --frameworks swift
python scripts/02_download_json.py --frameworks swift
python scripts/03_json_to_markdown.py --frameworks swift
```

### Resume Interrupted Downloads

Discovery supports resume:

```bash
python scripts/01_discover_docs.py --resume
```

Download automatically skips existing files.

### Framework-Specific Updates

```bash
python scripts/update_check.py --frameworks swiftui
python scripts/update_pull.py --frameworks swiftui
```

### Command Help

All scripts support `--help`:

```bash
python scripts/01_discover_docs.py --help
python scripts/02_download_json.py --help
python scripts/03_json_to_markdown.py --help
python scripts/04_markdown_to_pdf.py --help
python scripts/05_markdown_to_html.py --help
python scripts/update_check.py --help
python scripts/update_pull.py --help
python scripts/update_status.py --help
```

## Complete Documentation Archive

### Download All Frameworks (Overnight)

To download the complete Apple Developer Documentation for all frameworks:

```bash
# Full download sequence (runs for 12-24 hours)
python scripts/01_discover_docs.py
python scripts/02_download_json.py
python scripts/03_json_to_markdown.py
```

**Expected Results:**
- **~68,500 pages** across all frameworks
- **~3-5 GB** total storage
- **12-24 hours** download time (due to rate limiting)

**Run in background:**

```bash
# macOS/Linux - run overnight
nohup bash -c '
  python scripts/01_discover_docs.py && \
  python scripts/02_download_json.py && \
  python scripts/03_json_to_markdown.py
' > download.log 2>&1 &

# Keep Mac awake during download
caffeinate -i -t 86400 &

# Monitor progress
tail -f download.log
```

### Generate PDF Documentation

After downloading markdown files, generate searchable PDFs:

```bash
# Install pandoc (required for PDF generation)
brew install pandoc basictex  # macOS
# sudo apt-get install pandoc texlive-xetex  # Linux

# Install Python dependency
pip install markdown

# Generate PDFs (one per framework, recommended sizes)
python scripts/04_markdown_to_pdf.py --framework swift --max-files 500
python scripts/04_markdown_to_pdf.py --framework swiftui --max-files 300
python scripts/04_markdown_to_pdf.py --framework foundation --max-files 400
```

**PDF Features:**
- ✅ Auto-generated table of contents
- ✅ Syntax highlighting for code blocks
- ✅ Numbered sections
- ✅ Working hyperlinks
- ✅ Professional layout (1-inch margins, 10pt font)

**Output:** `pdf/<framework>_documentation.pdf` (~20-50 MB each)

**Framework-Specific Recommendations:**

| Framework | Recommended Files | Expected PDF Size | Coverage |
|-----------|------------------|-------------------|----------|
| swift | 500 | ~50 MB | Core language features |
| swiftui | 300 | ~30 MB | Essential UI components |
| uikit | 400 | ~40 MB | Major view controllers & views |
| foundation | 400 | ~40 MB | Core data types & APIs |
| coredata | 200 | ~20 MB | Full framework |
| combine | 150 | ~15 MB | Full framework |
| swiftdata | 100 | ~10 MB | Full framework |
| coreml | 200 | ~20 MB | ML essentials |
| mapkit | 150 | ~15 MB | Map & location APIs |
| avfoundation | 250 | ~25 MB | A/V processing APIs |

**Test with smaller subset first:**

```bash
# Generate a small test PDF (50 pages)
python scripts/04_markdown_to_pdf.py --framework swift --max-files 50
open pdf/swift_documentation.pdf
```

### Generate HTML Documentation

Create a browsable, searchable static HTML website:

```bash
# Install dependency
pip install markdown

# Generate HTML for all frameworks
python scripts/05_markdown_to_html.py

# Or specific frameworks only
python scripts/05_markdown_to_html.py --frameworks swift swiftui

# Open in browser
open html/index.html
```

**HTML Features:**
- ✅ Complete offline browsing
- ✅ Search functionality per framework
- ✅ Apple-style dark code highlighting
- ✅ Responsive design
- ✅ Fast navigation
- ✅ No server required

**Output:** `html/` directory with complete static website

### Complete Archive Structure

After downloading all frameworks and generating documentation:

```
Apple-Developer-Documentation-Offline-Archive/
├── markdown/                  # AI-optimized Markdown (for LLMs, RAG systems)
│   ├── swift/                # ~30,000 files (~500 MB)
│   ├── swiftui/              # ~5,000 files (~80 MB)
│   ├── uikit/                # ~8,000 files (~130 MB)
│   ├── foundation/           # ~12,000 files (~200 MB)
│   └── ...                   # 6 more frameworks
│
├── pdf/                      # Human-readable PDFs
│   ├── swift_documentation.pdf
│   ├── swiftui_documentation.pdf
│   ├── foundation_documentation.pdf
│   └── ...
│
├── html/                     # Browsable HTML documentation
│   ├── index.html
│   ├── swift/
│   │   ├── index.html
│   │   └── ...
│   └── ...
│
├── raw-json/                 # Original Apple JSON (backup)
│   ├── swift/                # ~1.2 GB
│   ├── swiftui/              # ~200 MB
│   └── ...
│
├── .docsync/                 # Update tracking
│   ├── manifest.json         # ETags & hashes
│   ├── versions/             # Version snapshots
│   └── changelog/            # Update history
│
└── scripts/                  # Python tools
    ├── 01_discover_docs.py
    ├── 02_download_json.py
    ├── 03_json_to_markdown.py
    ├── 04_markdown_to_pdf.py
    ├── 05_markdown_to_html.py
    ├── update_check.py
    ├── update_pull.py
    └── update_status.py
```

## How It Works

### Documentation Discovery

1. Starts with framework root URLs (e.g., `swift.json`)
2. Recursively extracts references from `topicSections` and `references`
3. Builds complete documentation hierarchy
4. Saves to `index.json`

### JSON Download

1. Reads index from discovery step
2. Downloads each page with rate limiting
3. Stores ETag and content hash in manifest
4. Creates `.docsync/manifest.json` for update tracking

### Markdown Conversion

Converts Apple's JSON schema to Markdown:

```
JSON Structure          →  Markdown Output
═══════════════════════════════════════════
metadata                →  YAML frontmatter
primaryContentSections  →  Main content
├─ heading             →  ## Headers
├─ paragraph           →  Text paragraphs
├─ codeListing         →  ```swift code blocks
├─ unorderedList       →  - Bullet lists
└─ orderedList         →  1. Numbered lists
topicSections          →  ## Topics section
references             →  Internal links
```

### Update Detection

1. Checks ETags via HTTP HEAD requests
2. Compares with stored ETags in manifest
3. Only downloads changed pages
4. Generates changelog

## Maintenance

### Weekly/Monthly Updates

```bash
# Activate environment
source venv/bin/activate

# Check status
python scripts/update_status.py

# Check for updates
python scripts/update_check.py

# Download if available
python scripts/update_pull.py

# Review changes
cat .docsync/changelog/*.md
```

## Future Features

- [x] PDF generation (`04_markdown_to_pdf.py`) ✅
- [x] HTML documentation website (`05_markdown_to_html.py`) ✅
- [ ] Update history viewer (`update_history.py`)
- [ ] Version rollback (`update_rollback.py`)
- [ ] Swift Book integration
- [ ] Full-text search index for HTML
- [ ] Desktop app wrapper (Electron/Tauri)

## License & Disclaimer

This tool downloads publicly available Apple Developer Documentation for offline use.

**Important:**
- Documentation content © Apple Inc.
- For personal, non-commercial use only
- Respects Apple's servers via rate limiting
- Not affiliated with or endorsed by Apple

## Contributing

Contributions welcome! Areas for improvement:

- Additional framework support
- PDF generation templates
- Search functionality
- Performance optimizations
- Bug fixes

## Support

1. Check this README
2. Review script output for error messages
3. Use `--help` flag for script-specific documentation
4. Check existing issues

## Credits

Built with:
- [aiohttp](https://github.com/aio-libs/aiohttp) - Async HTTP
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) - HTML parsing
- [tqdm](https://github.com/tqdm/tqdm) - Progress bars
- [PyYAML](https://pyyaml.org/) - YAML processing

---

**Made for the developer community** 🚀
_Download once, reference forever_
