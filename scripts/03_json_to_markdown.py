#!/usr/bin/env python3
"""
Apple Documentation JSON to Markdown Converter
Converts Apple's JSON documentation format to AI-readable Markdown
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Any
from tqdm import tqdm
import argparse



class AppleDocConverter:
    """Converts Apple's JSON documentation to Markdown"""

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.raw_json_dir = self.base_dir / 'raw-json'
        self.markdown_dir = self.base_dir / 'markdown'
        self.docsync_dir = self.base_dir / '.docsync'

        # Create markdown directory
        self.markdown_dir.mkdir(parents=True, exist_ok=True)

        # Stats
        self.stats = {
            'converted': 0,
            'failed': 0,
            'skipped': 0,
        }

    def load_manifest(self) -> Dict:
        """Load the manifest"""
        manifest_file = self.docsync_dir / 'manifest.json'
        with open(manifest_file, 'r') as f:
            return json.load(f)

    def convert_inline_content(self, content: Any) -> str:
        """Convert inline content to Markdown"""
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            result = []
            for item in content:
                if isinstance(item, str):
                    result.append(item)
                elif isinstance(item, dict):
                    if item.get('type') == 'codeVoice':
                        result.append(f"`{item.get('code', '')}`")
                    elif item.get('type') == 'emphasis':
                        inner = self.convert_inline_content(item.get('inlineContent', []))
                        result.append(f"*{inner}*")
                    elif item.get('type') == 'strong':
                        inner = self.convert_inline_content(item.get('inlineContent', []))
                        result.append(f"**{inner}**")
                    elif item.get('type') == 'reference':
                        # Internal reference
                        identifier = item.get('identifier', '')
                        result.append(f"[{identifier}]({identifier})")
                    elif item.get('type') == 'text':
                        result.append(item.get('text', ''))
                    else:
                        # Fallback
                        result.append(self.convert_inline_content(item.get('inlineContent', [])))
            return ''.join(result)

        return str(content)

    def convert_paragraph(self, para: Dict) -> str:
        """Convert a paragraph to Markdown"""
        inline_content = para.get('inlineContent', [])
        return self.convert_inline_content(inline_content) + '\n\n'

    def convert_heading(self, heading: Dict, level: int = 2) -> str:
        """Convert a heading to Markdown"""
        inline_content = heading.get('inlineContent', [])
        text = self.convert_inline_content(inline_content)
        return f"{'#' * level} {text}\n\n"

    def convert_code_listing(self, code: Dict) -> str:
        """Convert a code listing to Markdown"""
        syntax = code.get('syntax', '')
        code_lines = code.get('code', [])

        if isinstance(code_lines, list):
            code_text = '\n'.join(code_lines)
        else:
            code_text = str(code_lines)

        return f"```{syntax}\n{code_text}\n```\n\n"

    def convert_unordered_list(self, list_data: Dict) -> str:
        """Convert an unordered list to Markdown"""
        items = list_data.get('items', [])
        result = []

        for item in items:
            content = item.get('content', [])
            text = self.convert_content_sections(content, inline=True)
            result.append(f"- {text.strip()}\n")

        return ''.join(result) + '\n'

    def convert_ordered_list(self, list_data: Dict) -> str:
        """Convert an ordered list to Markdown"""
        items = list_data.get('items', [])
        result = []

        for i, item in enumerate(items, 1):
            content = item.get('content', [])
            text = self.convert_content_sections(content, inline=True)
            result.append(f"{i}. {text.strip()}\n")

        return ''.join(result) + '\n'

    def convert_aside(self, aside: Dict) -> str:
        """Convert an aside/note to Markdown"""
        style = aside.get('style', 'note')
        content = aside.get('content', [])
        text = self.convert_content_sections(content, inline=True)

        return f"> **{style.upper()}:** {text.strip()}\n\n"

    def convert_table(self, table: Dict) -> str:
        """Convert a table to Markdown"""
        # Simplified table conversion
        header = table.get('header', {})
        rows = table.get('rows', [])

        result = []

        # Header
        if header and isinstance(header, dict):
            cells = header.get('cells', [])
            header_row = ' | '.join([self.convert_inline_content(cell.get('content', [])) for cell in cells])
            result.append(f"| {header_row} |\n")
            result.append(f"| {' | '.join(['---'] * len(cells))} |\n")

        # Rows
        for row in rows:
            if not isinstance(row, dict):
                continue
            cells = row.get('cells', [])
            row_text = ' | '.join([self.convert_inline_content(cell.get('content', [])) for cell in cells])
            result.append(f"| {row_text} |\n")

        return ''.join(result) + '\n'

    def convert_content_sections(self, sections: List[Dict], inline: bool = False) -> str:
        """Convert content sections to Markdown"""
        result = []

        for section in sections:
            section_type = section.get('type')

            if section_type == 'paragraph':
                result.append(self.convert_paragraph(section))
            elif section_type == 'heading':
                level = section.get('level', 2)
                result.append(self.convert_heading(section, level))
            elif section_type == 'codeListing':
                result.append(self.convert_code_listing(section))
            elif section_type == 'unorderedList':
                result.append(self.convert_unordered_list(section))
            elif section_type == 'orderedList':
                result.append(self.convert_ordered_list(section))
            elif section_type == 'aside':
                result.append(self.convert_aside(section))
            elif section_type == 'table':
                result.append(self.convert_table(section))
            else:
                # Unknown type - try to extract text
                if 'inlineContent' in section:
                    result.append(self.convert_inline_content(section['inlineContent']) + '\n\n')

        text = ''.join(result)
        if inline:
            return text.replace('\n\n', ' ').strip()
        return text

    def convert_topics(self, topic_sections: List[Dict]) -> str:
        """Convert topic sections to Markdown"""
        if not topic_sections:
            return ''

        result = ['## Topics\n\n']

        for section in topic_sections:
            title = section.get('title', 'Related')
            identifiers = section.get('identifiers', [])

            if identifiers:
                result.append(f"### {title}\n\n")
                for identifier in identifiers:
                    # Create relative link
                    link = identifier.replace('doc://', '').replace('documentation/', '')
                    title_text = identifier.split('/')[-1]
                    result.append(f"- [{title_text}](../{link}.md)\n")
                result.append('\n')

        return ''.join(result)

    def generate_frontmatter(self, metadata: Dict) -> str:
        """Generate YAML frontmatter"""
        frontmatter = {
            'title': metadata.get('title', ''),
            'role': metadata.get('role', ''),
            'platforms': metadata.get('platforms', []),
            'modules': metadata.get('modules', []),
        }

        # Add optional fields
        if 'required' in metadata:
            frontmatter['required'] = metadata['required']
        if 'roleHeading' in metadata:
            frontmatter['roleHeading'] = metadata['roleHeading']

        yaml_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
        return f"---\n{yaml_str}---\n\n"

    def convert_json_to_markdown(self, json_path: Path) -> str:
        """Convert a JSON documentation file to Markdown"""
        with open(json_path, 'r') as f:
            data = json.load(f)

        # Generate frontmatter
        metadata = data.get('metadata', {})
        markdown = self.generate_frontmatter(metadata)

        # Add title
        title = metadata.get('title', '')
        if title:
            markdown += f"# {title}\n\n"

        # Add abstract
        abstract = data.get('abstract', [])
        if abstract:
            markdown += self.convert_content_sections(abstract)

        # Add primary content sections
        primary_sections = data.get('primaryContentSections', [])
        for section in primary_sections:
            kind = section.get('kind')

            if kind == 'content':
                content = section.get('content', [])
                markdown += self.convert_content_sections(content)

            elif kind == 'declarations':
                markdown += "## Declaration\n\n"
                declarations = section.get('declarations', [])
                for decl in declarations:
                    platforms = decl.get('platforms', [])
                    tokens = decl.get('tokens', [])

                    if platforms:
                        markdown += f"**Platforms:** {', '.join(platforms)}\n\n"

                    # Convert tokens to code
                    code = ''.join([t.get('text', '') for t in tokens])
                    markdown += f"```swift\n{code}\n```\n\n"

            elif kind == 'parameters':
                markdown += "## Parameters\n\n"
                parameters = section.get('parameters', [])
                for param in parameters:
                    name = param.get('name', '')
                    content = param.get('content', [])
                    param_text = self.convert_content_sections(content, inline=True)
                    markdown += f"- **{name}**: {param_text}\n"
                markdown += '\n'

            elif kind == 'returns':
                markdown += "## Return Value\n\n"
                content = section.get('content', [])
                markdown += self.convert_content_sections(content)

        # Add topics
        topic_sections = data.get('topicSections', [])
        if topic_sections:
            markdown += self.convert_topics(topic_sections)

        # Add see also
        see_also = data.get('seeAlsoSections', [])
        if see_also:
            markdown += "## See Also\n\n"
            for section in see_also:
                identifiers = section.get('identifiers', [])
                for identifier in identifiers:
                    link = identifier.replace('doc://', '').replace('documentation/', '')
                    title_text = identifier.split('/')[-1]
                    markdown += f"- [{title_text}](../{link}.md)\n"
            markdown += '\n'

        return markdown

    def convert_all(self, frameworks: List[str] = None):
        """Convert all JSON files to Markdown"""
        manifest = self.load_manifest()

        # Filter by frameworks if specified
        if frameworks:
            pages_to_convert = {
                k: v for k, v in manifest.items()
                if any(k.startswith(f'{fw}/') for fw in frameworks)
            }
        else:
            pages_to_convert = manifest

        print(f"\nConverting {len(pages_to_convert)} pages to Markdown...")

        with tqdm(total=len(pages_to_convert), desc="Converting") as pbar:
            for doc_path, metadata in pages_to_convert.items():
                try:
                    json_path = self.base_dir / metadata['local_path']

                    if not json_path.exists():
                        print(f"\nWarning: JSON file not found: {json_path}")
                        self.stats['skipped'] += 1
                        pbar.update(1)
                        continue

                    # Convert to Markdown
                    markdown = self.convert_json_to_markdown(json_path)

                    # Save Markdown file
                    md_path = self.markdown_dir / f'{doc_path}.md'
                    md_path.parent.mkdir(parents=True, exist_ok=True)

                    with open(md_path, 'w') as f:
                        f.write(markdown)

                    self.stats['converted'] += 1

                except Exception as e:
                    print(f"\nError converting {doc_path}: {e}")
                    self.stats['failed'] += 1

                pbar.update(1)

        # Print stats
        print("\n" + "="*60)
        print("Conversion Statistics:")
        print(f"  Successfully converted: {self.stats['converted']}")
        print(f"  Failed: {self.stats['failed']}")
        print(f"  Skipped: {self.stats['skipped']}")
        print("="*60)


def main():
    parser = argparse.ArgumentParser(description='Convert Apple documentation JSON to Markdown')
    parser.add_argument('--frameworks', nargs='+', help='Frameworks to convert (default: all)')
    parser.add_argument('--base-dir', default='.', help='Base directory (default: project directory)')

    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent / args.base_dir if args.base_dir == '.' else Path(args.base_dir)

    # Check if manifest exists
    manifest_file = base_dir / '.docsync' / 'manifest.json'
    if not manifest_file.exists():
        print(f"Error: Manifest file not found: {manifest_file}")
        print("Please run 02_download_json.py first to download the documentation")
        return

    converter = AppleDocConverter(base_dir=base_dir)
    converter.convert_all(frameworks=args.frameworks)

    print("\nConversion complete!")
    print(f"Markdown files saved to: {converter.markdown_dir}")
    print("\nNext steps:")
    print("  1. Browse the Markdown files in the 'markdown/' directory")
    print("  2. Optionally run 04_markdown_to_pdf.py to generate PDFs")
    print("  3. Use update_check.py to check for documentation updates")


if __name__ == '__main__':
    main()
