#!/usr/bin/env python3
"""
Apple Documentation Discovery Crawler
Recursively discovers all documentation pages through Apple's JSON API
"""

import asyncio
import aiohttp
import json
import time
from pathlib import Path
from typing import Set, Dict, List
from tqdm import tqdm
import argparse


# Framework root URLs
FRAMEWORK_ROOTS = {
    'swift': 'https://developer.apple.com/tutorials/data/documentation/swift.json',
    'swiftui': 'https://developer.apple.com/tutorials/data/documentation/swiftui.json',
    'uikit': 'https://developer.apple.com/tutorials/data/documentation/uikit.json',
    'foundation': 'https://developer.apple.com/tutorials/data/documentation/foundation.json',
    'coredata': 'https://developer.apple.com/tutorials/data/documentation/coredata.json',
    'combine': 'https://developer.apple.com/tutorials/data/documentation/combine.json',
    'swiftdata': 'https://developer.apple.com/tutorials/data/documentation/swiftdata.json',
    'coreml': 'https://developer.apple.com/tutorials/data/documentation/coreml.json',
    'mapkit': 'https://developer.apple.com/tutorials/data/documentation/mapkit.json',
    'avfoundation': 'https://developer.apple.com/tutorials/data/documentation/avfoundation.json',
}


class RateLimiter:
    """Rate limiter to avoid overwhelming Apple's servers"""

    def __init__(self, requests_per_second: float = 5.0):
        self.delay = 1.0 / requests_per_second
        self.last_request = 0.0

    async def wait(self):
        now = time.time()
        time_since_last = now - self.last_request
        if time_since_last < self.delay:
            await asyncio.sleep(self.delay - time_since_last)
        self.last_request = time.time()


class DocumentationCrawler:
    """Crawls Apple's documentation API to discover all pages"""

    def __init__(self, output_dir: Path, frameworks: List[str] = None):
        self.output_dir = Path(output_dir)
        self.frameworks = frameworks or list(FRAMEWORK_ROOTS.keys())

        # State tracking
        self.discovered_urls: Set[str] = set()
        self.processed_urls: Set[str] = set()
        self.url_metadata: Dict[str, dict] = {}

        # Progress tracking
        self.pbar = None

        # Rate limiting
        self.rate_limiter = RateLimiter(requests_per_second=5.0)

        # User agent
        self.user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'

    def save_state(self):
        """Save current discovery state"""
        state_file = self.output_dir / 'discovery_state.json'
        state = {
            'discovered_urls': list(self.discovered_urls),
            'processed_urls': list(self.processed_urls),
            'url_metadata': self.url_metadata,
        }
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def load_state(self):
        """Load previous discovery state for resume"""
        state_file = self.output_dir / 'discovery_state.json'
        if state_file.exists():
            with open(state_file, 'r') as f:
                state = json.load(f)
            self.discovered_urls = set(state['discovered_urls'])
            self.processed_urls = set(state['processed_urls'])
            self.url_metadata = state['url_metadata']
            print(f"Resumed: {len(self.processed_urls)} processed, {len(self.discovered_urls) - len(self.processed_urls)} remaining")

    def normalize_identifier(self, identifier: str) -> str:
        """Normalize Apple doc identifier to path format

        Converts:
        - doc://com.apple.foundation/documentation/Foundation/NSString -> foundation/NSString
        - /documentation/swift/string -> swift/string
        - swift/string -> swift/string
        """
        # Remove doc:// prefix if present
        if identifier.startswith('doc://'):
            # Format: doc://com.apple.FRAMEWORK/documentation/PATH
            identifier = identifier.replace('doc://', '')
            # Remove com.apple. prefix
            if identifier.startswith('com.apple.'):
                identifier = identifier.replace('com.apple.', '', 1)
            # Extract path after /documentation/
            if '/documentation/' in identifier:
                parts = identifier.split('/documentation/', 1)
                if len(parts) == 2:
                    framework = parts[0].lower()
                    path = parts[1]
                    # Return framework/path (e.g., foundation/NSString)
                    identifier = f"{framework}/{path}"

        # Remove leading /documentation/ if present
        if identifier.startswith('/documentation/'):
            identifier = identifier.replace('/documentation/', '', 1)

        return identifier

    def extract_references_from_json(self, data: dict, base_path: str) -> Set[str]:
        """Extract all documentation references from JSON data"""
        references = set()

        # Extract from topicSections
        if 'topicSections' in data:
            for section in data['topicSections']:
                if 'identifiers' in section:
                    for identifier in section['identifiers']:
                        normalized = self.normalize_identifier(identifier)
                        if normalized:
                            references.add(normalized)

        # Extract from references section
        if 'references' in data:
            for ref_id, ref_data in data['references'].items():
                if isinstance(ref_data, dict) and ref_data.get('type') in ['topic', 'method', 'property', 'class', 'structure', 'protocol', 'enum']:
                    if 'url' in ref_data:
                        # Convert relative URL to full path
                        url = ref_data['url']
                        normalized = self.normalize_identifier(url)
                        if normalized:
                            references.add(normalized)

        # Extract from relationships
        if 'relationshipsSections' in data:
            for section in data.get('relationshipsSections', []):
                if 'identifiers' in section:
                    for identifier in section['identifiers']:
                        normalized = self.normalize_identifier(identifier)
                        if normalized:
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
                    print(f"\nWarning: 404 Not Found: {url}")
                    return None
                elif response.status == 429:
                    # Rate limited - wait and retry
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
        """Crawl a single documentation page and extract references"""
        if doc_path in self.processed_urls:
            return set()

        url = f'https://developer.apple.com/tutorials/data/documentation/{doc_path}.json'

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

        # Extract new references
        references = self.extract_references_from_json(data, doc_path)

        # Mark as processed
        self.processed_urls.add(doc_path)

        # Update progress
        if self.pbar:
            self.pbar.update(1)

        return references

    async def crawl_framework(self, framework: str):
        """Crawl all documentation for a single framework"""
        print(f"\nCrawling {framework}...")

        # Initialize with framework root
        root_path = framework
        self.discovered_urls.add(root_path)

        async with aiohttp.ClientSession() as session:
            while True:
                # Find unprocessed URLs
                to_process = self.discovered_urls - self.processed_urls

                if not to_process:
                    break

                # Create progress bar
                if self.pbar:
                    self.pbar.close()
                self.pbar = tqdm(total=len(to_process), desc=f"{framework} pages")

                # Process pages in batches
                batch_size = 10
                to_process_list = list(to_process)

                for i in range(0, len(to_process_list), batch_size):
                    batch = to_process_list[i:i+batch_size]

                    # Fetch batch concurrently
                    tasks = [self.crawl_page(session, doc_path) for doc_path in batch]
                    results = await asyncio.gather(*tasks)

                    # Add new discovered URLs
                    for new_refs in results:
                        for ref in new_refs:
                            if ref not in self.discovered_urls:
                                self.discovered_urls.add(ref)

                    # Save state periodically
                    if i % 50 == 0:
                        self.save_state()

                if self.pbar:
                    self.pbar.close()

        # Final save
        self.save_state()

    async def crawl_all(self):
        """Crawl all specified frameworks"""
        for framework in self.frameworks:
            if framework not in FRAMEWORK_ROOTS:
                print(f"Warning: Unknown framework '{framework}', skipping")
                continue

            await self.crawl_framework(framework)

        # Save final index
        self.save_index()

    def save_index(self):
        """Save complete discovered index"""
        index_file = self.output_dir / 'index.json'

        # Organize by framework
        index = {
            'frameworks': {},
            'total_pages': len(self.discovered_urls),
            'processed_pages': len(self.processed_urls),
            'metadata': self.url_metadata,
        }

        # Group URLs by framework
        for url in self.discovered_urls:
            framework = url.split('/')[0]
            if framework not in index['frameworks']:
                index['frameworks'][framework] = []
            index['frameworks'][framework].append(url)

        with open(index_file, 'w') as f:
            json.dump(index, f, indent=2)

        print(f"\nIndex saved to {index_file}")
        print(f"Total pages discovered: {len(self.discovered_urls)}")
        print(f"Total processed: {len(self.processed_urls)}")

        # Print framework breakdown
        print("\nFramework breakdown:")
        for framework, urls in sorted(index['frameworks'].items()):
            print(f"  {framework}: {len(urls)} pages")


async def main():
    parser = argparse.ArgumentParser(description='Discover Apple documentation pages')
    parser.add_argument('--frameworks', nargs='+', help='Frameworks to crawl (default: all)')
    parser.add_argument('--output', default='..', help='Output directory (default: parent directory)')
    parser.add_argument('--resume', action='store_true', help='Resume from previous state')

    args = parser.parse_args()

    output_dir = Path(__file__).parent.parent / args.output if args.output == '..' else Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    crawler = DocumentationCrawler(
        output_dir=output_dir,
        frameworks=args.frameworks
    )

    if args.resume:
        crawler.load_state()

    await crawler.crawl_all()

    print("\nDiscovery complete!")


if __name__ == '__main__':
    asyncio.run(main())
