#!/usr/bin/env python3
"""
The Swift Programming Language Book Crawler
Discovers and downloads the Swift Book from docs.swift.org's DocC API.

The Swift Book uses the same DocC JSON format as Apple's documentation but is
hosted on a different domain with a different identifier prefix:
  - Apple docs: /tutorials/data/documentation/{framework}.json
  - Swift Book: docs.swift.org/swift-book/data/documentation/the-swift-programming-language.json

Usage:
    python scripts/07_discover_swift_book.py
    python scripts/07_discover_swift_book.py --download --convert
    python scripts/07_discover_swift_book.py --resume
"""

import asyncio
import aiohttp
import json
import hashlib
import time
import re
import yaml
from pathlib import Path
from typing import Set, Dict, Any
from tqdm import tqdm
import argparse
from datetime import datetime


SWIFT_BOOK_ROOT = 'https://docs.swift.org/swift-book/data/documentation/the-swift-programming-language.json'
BASE_URL = 'https://docs.swift.org/swift-book/data/documentation'


class RateLimiter:
    def __init__(self, requests_per_second: float = 5.0):
        self.delay = 1.0 / requests_per_second
        self.last_request = 0.0

    async def wait(self):
        now = time.time()
        time_since_last = now - self.last_request
        if time_since_last < self.delay:
            await asyncio.sleep(self.delay - time_since_last)
        self.last_request = time.time()


class SwiftBookCrawler:
    """Crawls The Swift Programming Language book from docs.swift.org"""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.raw_json_dir = self.output_dir / 'raw-json'
        self.markdown_dir = self.output_dir / 'markdown'
        self.docsync_dir = self.output_dir / '.docsync'

        # State tracking
        self.discovered_urls: Set[str] = set()
        self.processed_urls: Set[str] = set()
        self.url_metadata: Dict[str, dict] = {}
        self.manifest: Dict[str, dict] = {}

        # Progress
        self.pbar = None

        # Rate limiting
        self.rate_limiter = RateLimiter(requests_per_second=5.0)
        self.user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'

    def normalize_identifier(self, identifier: str) -> str:
        """Normalize Swift Book doc identifier to path format

        Converts:
        - doc://org.swift.tspl/documentation/The-Swift-Programming-Language/TheBasics
            -> the-swift-programming-language/thebasics
        - doc://Swift.TSPL/documentation/The-Swift-Programming-Language/TheBasics
            -> the-swift-programming-language/thebasics
        - /documentation/the-swift-programming-language/thebasics
            -> the-swift-programming-language/thebasics
        """
        if identifier.startswith('doc://'):
            identifier = identifier.replace('doc://', '')
            # Remove org.swift.tspl/ or Swift.TSPL/ prefix
            if '/documentation/' in identifier:
                parts = identifier.split('/documentation/', 1)
                if len(parts) == 2:
                    identifier = parts[1]

        # Remove leading /documentation/
        if identifier.startswith('/documentation/'):
            identifier = identifier[len('/documentation/'):]

        # Lowercase the path
        identifier = identifier.lower()

        return identifier

    def is_swift_book_ref(self, identifier: str) -> bool:
        """Check if a reference belongs to the Swift Book"""
        id_lower = identifier.lower()
        return (
            'org.swift.tspl' in id_lower
            or 'swift.tspl' in id_lower
            or 'the-swift-programming-language' in id_lower
        )

    def extract_references(self, data: dict) -> Set[str]:
        """Extract all Swift Book page references from JSON data"""
        references = set()

        # Extract from topicSections
        if 'topicSections' in data:
            for section in data['topicSections']:
                for identifier in section.get('identifiers', []):
                    if self.is_swift_book_ref(identifier):
                        normalized = self.normalize_identifier(identifier)
                        if normalized and normalized.startswith('the-swift-programming-language'):
                            references.add(normalized)

        # Extract from references section
        if 'references' in data:
            for ref_id, ref_data in data['references'].items():
                if not isinstance(ref_data, dict):
                    continue
                if ref_data.get('type') in ['topic', 'link', 'article']:
                    url = ref_data.get('url', '')
                    if self.is_swift_book_ref(ref_id) or 'the-swift-programming-language' in url.lower():
                        normalized = self.normalize_identifier(url or ref_id)
                        if normalized and normalized.startswith('the-swift-programming-language'):
                            references.add(normalized)

        # Extract from seeAlso sections
        if 'seeAlsoSections' in data:
            for section in data['seeAlsoSections']:
                for identifier in section.get('identifiers', []):
                    if self.is_swift_book_ref(identifier):
                        normalized = self.normalize_identifier(identifier)
                        if normalized and normalized.startswith('the-swift-programming-language'):
                            references.add(normalized)

        return references

    async def fetch_json(self, session: aiohttp.ClientSession, url: str) -> dict:
        """Fetch JSON data from URL with rate limiting"""
        await self.rate_limiter.wait()
        headers = {'User-Agent': self.user_agent}

        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    return None
                elif response.status == 429:
                    print(f"\nRate limited. Waiting 10 seconds...")
                    await asyncio.sleep(10)
                    return await self.fetch_json(session, url)
                else:
                    print(f"\nError {response.status} fetching {url}")
                    return None
        except Exception as e:
            print(f"\nException fetching {url}: {e}")
            return None

    async def crawl_page(self, session: aiohttp.ClientSession, doc_path: str) -> Set[str]:
        """Crawl a single page and extract references"""
        if doc_path in self.processed_urls:
            return set()

        url = f'{BASE_URL}/{doc_path}.json'
        data = await self.fetch_json(session, url)

        if not data:
            self.processed_urls.add(doc_path)
            return set()

        # Store metadata
        self.url_metadata[doc_path] = {
            'url': url,
            'title': data.get('metadata', {}).get('title', ''),
            'role': data.get('metadata', {}).get('role', ''),
        }

        references = self.extract_references(data)
        self.processed_urls.add(doc_path)

        if self.pbar:
            self.pbar.update(1)

        return references

    async def crawl_all(self):
        """Crawl all Swift Book pages"""
        root_path = 'the-swift-programming-language'
        self.discovered_urls.add(root_path)

        async with aiohttp.ClientSession() as session:
            # Fetch root page first
            root_data = await self.fetch_json(session, SWIFT_BOOK_ROOT)

            if root_data:
                self.url_metadata[root_path] = {
                    'url': SWIFT_BOOK_ROOT,
                    'title': root_data.get('metadata', {}).get('title', ''),
                    'role': root_data.get('metadata', {}).get('role', ''),
                }
                self.processed_urls.add(root_path)

                refs = self.extract_references(root_data)
                for ref in refs:
                    self.discovered_urls.add(ref)

                print(f"Root page discovered {len(refs)} chapter references")
            else:
                print("Warning: Could not fetch Swift Book root page")
                print(f"URL attempted: {SWIFT_BOOK_ROOT}")
                return

            # Recursive crawl for sub-pages
            while True:
                to_process = self.discovered_urls - self.processed_urls

                if not to_process:
                    break

                if self.pbar:
                    self.pbar.close()
                self.pbar = tqdm(total=len(to_process), desc="Swift Book pages")

                batch_size = 10
                to_process_list = list(to_process)

                for i in range(0, len(to_process_list), batch_size):
                    batch = to_process_list[i:i + batch_size]
                    tasks = [self.crawl_page(session, doc_path) for doc_path in batch]
                    results = await asyncio.gather(*tasks)

                    for new_refs in results:
                        for ref in new_refs:
                            if ref.startswith('the-swift-programming-language'):
                                if ref not in self.discovered_urls:
                                    self.discovered_urls.add(ref)

                    if i % 50 == 0:
                        self.save_state()

            if self.pbar:
                self.pbar.close()

        self.save_state()
        self.save_index()

    def save_state(self):
        state_file = self.output_dir / 'swift_book_discovery_state.json'
        state = {
            'discovered_urls': list(self.discovered_urls),
            'processed_urls': list(self.processed_urls),
            'url_metadata': self.url_metadata,
        }
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def load_state(self):
        state_file = self.output_dir / 'swift_book_discovery_state.json'
        if state_file.exists():
            with open(state_file, 'r') as f:
                state = json.load(f)
            self.discovered_urls = set(state['discovered_urls'])
            self.processed_urls = set(state['processed_urls'])
            self.url_metadata = state['url_metadata']
            print(f"Resumed: {len(self.processed_urls)} processed")

    def save_index(self):
        """Save Swift Book index"""
        index_file = self.output_dir / 'swift_book_index.json'

        # Group by chapter
        chapters = {}
        for url in self.discovered_urls:
            parts = url.split('/')
            chapter = parts[1] if len(parts) > 1 else 'root'
            if chapter not in chapters:
                chapters[chapter] = []
            chapters[chapter].append(url)

        index = {
            'chapters': chapters,
            'total_pages': len(self.discovered_urls),
            'metadata': self.url_metadata,
        }

        with open(index_file, 'w') as f:
            json.dump(index, f, indent=2)

        print(f"\nSwift Book index saved to {index_file}")
        print(f"Total pages discovered: {len(self.discovered_urls)}")
        print(f"\nChapter breakdown:")
        for chapter, urls in sorted(chapters.items()):
            title = ''
            for u in urls:
                if u in self.url_metadata:
                    title = self.url_metadata[u].get('title', '')
                    break
            suffix = f' - {title}' if title else ''
            print(f"  {chapter}{suffix}: {len(urls)} page(s)")

    async def download_all(self):
        """Download all discovered Swift Book pages as JSON"""
        self.raw_json_dir.mkdir(parents=True, exist_ok=True)
        self.docsync_dir.mkdir(parents=True, exist_ok=True)

        # Load existing manifest for resume
        manifest_file = self.docsync_dir / 'swift_book_manifest.json'
        if manifest_file.exists():
            with open(manifest_file, 'r') as f:
                self.manifest = json.load(f)

        pages = list(self.discovered_urls)
        pages_to_download = [p for p in pages if p not in self.manifest]

        print(f"\nDownloading {len(pages_to_download)} Swift Book pages...")
        if len(self.manifest) > 0:
            print(f"Skipping {len(self.manifest)} already downloaded")

        batch_size = 10
        stats = {'downloaded': 0, 'failed': 0}

        async with aiohttp.ClientSession() as session:
            with tqdm(total=len(pages_to_download), desc="Downloading") as pbar:
                for i in range(0, len(pages_to_download), batch_size):
                    batch = pages_to_download[i:i + batch_size]

                    tasks = [self._download_page(session, p, stats) for p in batch]
                    await asyncio.gather(*tasks)

                    pbar.update(len(batch))

                    if i % 100 == 0:
                        with open(manifest_file, 'w') as f:
                            json.dump(self.manifest, f, indent=2)

        with open(manifest_file, 'w') as f:
            json.dump(self.manifest, f, indent=2)

        print(f"\nDownloaded: {stats['downloaded']}, Failed: {stats['failed']}")

    async def _download_page(self, session, doc_path, stats):
        """Download a single Swift Book page JSON"""
        await self.rate_limiter.wait()
        url = f'{BASE_URL}/{doc_path}.json'
        headers = {'User-Agent': self.user_agent}

        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    content = await response.text()
                    data = json.loads(content)

                    # Save under raw-json/swift-book/
                    output_file = self.raw_json_dir / 'swift-book' / f'{doc_path}.json'
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_file, 'w') as f:
                        json.dump(data, f, indent=2)

                    self.manifest[doc_path] = {
                        'url': url,
                        'local_path': str(output_file.relative_to(self.output_dir)),
                        'sha256': hashlib.sha256(content.encode()).hexdigest(),
                        'downloaded_at': datetime.now().isoformat(),
                        'title': data.get('metadata', {}).get('title', ''),
                    }
                    stats['downloaded'] += 1
                elif response.status == 429:
                    await asyncio.sleep(30)
                    await self._download_page(session, doc_path, stats)
                else:
                    stats['failed'] += 1
        except Exception as e:
            print(f"\nError downloading {doc_path}: {e}")
            stats['failed'] += 1

    def convert_all_to_markdown(self):
        """Convert all downloaded Swift Book JSON to Markdown"""
        book_json_dir = self.raw_json_dir / 'swift-book'
        book_md_dir = self.markdown_dir / 'swift-book'
        book_md_dir.mkdir(parents=True, exist_ok=True)

        json_files = list(book_json_dir.rglob('*.json'))
        print(f"\nConverting {len(json_files)} Swift Book pages to Markdown...")

        stats = {'converted': 0, 'failed': 0}

        for json_file in tqdm(json_files, desc="Converting"):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)

                markdown = self._json_to_markdown(data)

                rel_path = json_file.relative_to(book_json_dir)
                md_file = book_md_dir / rel_path.with_suffix('.md')
                md_file.parent.mkdir(parents=True, exist_ok=True)

                with open(md_file, 'w') as f:
                    f.write(markdown)

                stats['converted'] += 1
            except Exception as e:
                print(f"\nError converting {json_file.name}: {e}")
                stats['failed'] += 1

        print(f"\nConverted: {stats['converted']}, Failed: {stats['failed']}")
        print(f"Markdown saved to: {book_md_dir}")

    def _json_to_markdown(self, data: dict) -> str:
        """Convert Apple's DocC JSON format to Markdown"""
        parts = []

        # YAML frontmatter
        metadata = data.get('metadata', {})
        frontmatter = {
            'title': metadata.get('title', ''),
            'role': metadata.get('role', ''),
            'source': 'The Swift Programming Language',
        }

        parts.append('---')
        parts.append(yaml.dump(frontmatter, default_flow_style=False).strip())
        parts.append('---')
        parts.append('')

        # Title
        title = metadata.get('title', '')
        if title:
            parts.append(f'# {title}')
            parts.append('')

        # Abstract
        abstract = data.get('abstract', [])
        if abstract:
            parts.append(self._convert_inline_content(abstract))
            parts.append('')

        # Primary content sections
        for section in data.get('primaryContentSections', []):
            kind = section.get('kind', '')

            if kind in ('content', 'fullWidth'):
                for item in section.get('content', []):
                    converted = self._convert_content_item(item)
                    if converted:
                        parts.append(converted)
                        parts.append('')

            elif kind == 'declarations':
                for decl in section.get('declarations', []):
                    tokens = decl.get('tokens', [])
                    code = ''.join(t.get('text', '') for t in tokens)
                    if code:
                        parts.append(f'```swift\n{code}\n```')
                        parts.append('')

            elif kind == 'parameters':
                parts.append('## Parameters')
                parts.append('')
                for param in section.get('parameters', []):
                    name = param.get('name', '')
                    content = param.get('content', [])
                    desc = ''
                    for block in content:
                        desc += self._convert_content_item(block)
                    parts.append(f'- **{name}**: {desc}')
                parts.append('')

        # Topic sections
        for topic_section in data.get('topicSections', []):
            section_title = topic_section.get('title', '')
            if section_title:
                parts.append(f'## {section_title}')
                parts.append('')

            for identifier in topic_section.get('identifiers', []):
                ref = data.get('references', {}).get(identifier, {})
                if isinstance(ref, dict):
                    ref_title = ref.get('title', identifier)
                    ref_abstract = ref.get('abstract', [])
                    abstract_text = self._convert_inline_content(ref_abstract) if ref_abstract else ''
                    if abstract_text:
                        parts.append(f'- **{ref_title}**: {abstract_text}')
                    else:
                        parts.append(f'- **{ref_title}**')
            parts.append('')

        # See also
        for section in data.get('seeAlsoSections', []):
            parts.append('## See Also')
            parts.append('')
            for identifier in section.get('identifiers', []):
                ref = data.get('references', {}).get(identifier, {})
                if isinstance(ref, dict):
                    parts.append(f'- {ref.get("title", identifier)}')
            parts.append('')

        return '\n'.join(parts)

    def _convert_content_item(self, item: dict) -> str:
        """Convert a content item to Markdown"""
        item_type = item.get('type', '')

        if item_type == 'paragraph':
            return self._convert_inline_content(item.get('inlineContent', []))

        elif item_type == 'heading':
            level = item.get('level', 2)
            text = item.get('text', '')
            return f'{"#" * level} {text}'

        elif item_type == 'codeListing':
            code = '\n'.join(item.get('code', []))
            lang = item.get('syntax', '')
            return f'```{lang}\n{code}\n```'

        elif item_type == 'unorderedList':
            lines = []
            for li in item.get('items', []):
                content = li.get('content', [])
                for block in content:
                    lines.append(f'- {self._convert_content_item(block)}')
            return '\n'.join(lines)

        elif item_type == 'orderedList':
            lines = []
            for i, li in enumerate(item.get('items', []), 1):
                content = li.get('content', [])
                for block in content:
                    lines.append(f'{i}. {self._convert_content_item(block)}')
            return '\n'.join(lines)

        elif item_type == 'aside':
            style = item.get('style', 'note')
            content = '\n'.join(self._convert_content_item(c) for c in item.get('content', []))
            return f'> **{style.capitalize()}:** {content}'

        elif item_type == 'table':
            return self._convert_table(item)

        elif item_type == 'image':
            return f'[Image: {item.get("alt", "")}]'

        elif item_type in ('row', 'tabNavigator'):
            lines = []
            for child in item.get('content', item.get('tabs', [])):
                if isinstance(child, dict):
                    lines.append(self._convert_content_item(child))
            return '\n'.join(lines)

        elif item_type == 'tab':
            title = item.get('title', '')
            lines = [f'### {title}'] if title else []
            for child in item.get('content', []):
                lines.append(self._convert_content_item(child))
            return '\n'.join(lines)

        elif item_type == 'links':
            return ''

        elif item_type == 'step':
            content_parts = []
            for child in item.get('content', []):
                content_parts.append(self._convert_content_item(child))
            return '\n'.join(content_parts)

        return ''

    def _convert_table(self, item: dict) -> str:
        """Convert table to Markdown"""
        rows = item.get('rows', [])
        if not rows:
            return ''

        header_style = item.get('header', 'row')
        lines = []

        for i, row in enumerate(rows):
            cells = []
            if isinstance(row, list):
                cell_list = row
            elif isinstance(row, dict):
                cell_list = row.get('cells', [])
            else:
                continue

            for cell in cell_list:
                if isinstance(cell, list):
                    cell_text = ' '.join(
                        self._convert_content_item(c) if isinstance(c, dict) else str(c)
                        for c in cell
                    )
                elif isinstance(cell, dict):
                    cell_text = self._convert_content_item(cell)
                else:
                    cell_text = str(cell)
                cells.append(cell_text.replace('|', '\\|').replace('\n', ' '))

            if cells:
                lines.append('| ' + ' | '.join(cells) + ' |')

                if i == 0 and header_style == 'row':
                    lines.append('| ' + ' | '.join(['---'] * len(cells)) + ' |')

        return '\n'.join(lines)

    def _convert_inline_content(self, content: Any) -> str:
        """Convert inline content to Markdown text"""
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            result = []
            for item in content:
                if isinstance(item, str):
                    result.append(item)
                elif isinstance(item, dict):
                    t = item.get('type', '')
                    if t == 'text':
                        result.append(item.get('text', ''))
                    elif t == 'codeVoice':
                        result.append(f"`{item.get('code', '')}`")
                    elif t == 'emphasis':
                        inner = self._convert_inline_content(item.get('inlineContent', []))
                        result.append(f'*{inner}*')
                    elif t == 'strong':
                        inner = self._convert_inline_content(item.get('inlineContent', []))
                        result.append(f'**{inner}**')
                    elif t == 'reference':
                        result.append(item.get('identifier', ''))
                    elif t == 'image':
                        result.append('[Image]')
                    elif t == 'inlineHead':
                        inner = self._convert_inline_content(item.get('inlineContent', []))
                        result.append(f'**{inner}**')
                    elif t == 'newTerm':
                        inner = self._convert_inline_content(item.get('inlineContent', []))
                        result.append(f'*{inner}*')
                    else:
                        inner = self._convert_inline_content(
                            item.get('inlineContent', item.get('content', []))
                        )
                        result.append(inner)
            return ''.join(result)

        if isinstance(content, dict):
            return self._convert_inline_content(content.get('inlineContent', content.get('content', '')))

        return str(content)


async def main():
    parser = argparse.ArgumentParser(
        description='Discover and download The Swift Programming Language book'
    )
    parser.add_argument('--download', action='store_true', help='Also download JSON files')
    parser.add_argument('--convert', action='store_true', help='Also convert to Markdown')
    parser.add_argument('--resume', action='store_true', help='Resume from previous state')
    parser.add_argument('--output', default='.', help='Output directory')

    args = parser.parse_args()

    output_dir = Path(__file__).parent.parent / args.output if args.output == '.' else Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    crawler = SwiftBookCrawler(output_dir=output_dir)

    if args.resume:
        crawler.load_state()

    # Step 1: Discover
    print("=" * 60)
    print("Step 1: Discovering Swift Book pages...")
    print("=" * 60)
    await crawler.crawl_all()

    # Step 2: Download
    if args.download or args.convert:
        print("\n" + "=" * 60)
        print("Step 2: Downloading Swift Book JSON files...")
        print("=" * 60)
        await crawler.download_all()

    # Step 3: Convert
    if args.convert:
        print("\n" + "=" * 60)
        print("Step 3: Converting to Markdown...")
        print("=" * 60)
        crawler.convert_all_to_markdown()

    print("\nDone!")
    if not args.download:
        print("\nTo download and convert, run:")
        print("  python scripts/07_discover_swift_book.py --download --convert")


if __name__ == '__main__':
    asyncio.run(main())
