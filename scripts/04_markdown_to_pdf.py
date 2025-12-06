#!/usr/bin/env python3
"""
Apple Documentation Markdown to PDF Converter
Converts framework documentation to searchable PDF with table of contents
"""

import subprocess
import sys
from pathlib import Path
from typing import List
import argparse


class MarkdownToPDF:
    """Converts Markdown documentation to PDF"""

    # Framework-specific settings
    FRAMEWORK_CONFIG = {
        'swift': {
            'title': 'Swift Standard Library',
            'subtitle': 'Complete API Reference',
            'recommended_max': 500,  # Reasonable subset for PDF
        },
        'swiftui': {
            'title': 'SwiftUI Framework',
            'subtitle': 'Declarative UI Framework for Apple Platforms',
            'recommended_max': 300,
        },
        'uikit': {
            'title': 'UIKit Framework',
            'subtitle': 'iOS UI Framework',
            'recommended_max': 400,
        },
        'foundation': {
            'title': 'Foundation Framework',
            'subtitle': 'Essential Data Types and Collections',
            'recommended_max': 400,
        },
        'coredata': {
            'title': 'Core Data Framework',
            'subtitle': 'Object Graph and Persistence Framework',
            'recommended_max': 200,
        },
        'combine': {
            'title': 'Combine Framework',
            'subtitle': 'Declarative Swift API for Processing Values Over Time',
            'recommended_max': 150,
        },
        'swiftdata': {
            'title': 'SwiftData Framework',
            'subtitle': 'Modern Data Modeling and Management',
            'recommended_max': 100,
        },
        'coreml': {
            'title': 'Core ML Framework',
            'subtitle': 'Machine Learning on Apple Platforms',
            'recommended_max': 200,
        },
        'mapkit': {
            'title': 'MapKit Framework',
            'subtitle': 'Maps and Location Services',
            'recommended_max': 150,
        },
        'avfoundation': {
            'title': 'AVFoundation Framework',
            'subtitle': 'Audio and Video Processing',
            'recommended_max': 250,
        },
    }

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.markdown_dir = self.base_dir / 'markdown'
        self.pdf_dir = self.base_dir / 'pdf'

        # Create PDF directory
        self.pdf_dir.mkdir(parents=True, exist_ok=True)

    def check_pandoc(self) -> bool:
        """Check if pandoc is installed"""
        try:
            result = subprocess.run(['pandoc', '--version'],
                                   capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def get_framework_files(self, framework: str) -> List[Path]:
        """Get all markdown files for a framework, sorted"""
        framework_dir = self.markdown_dir / framework

        if not framework_dir.exists():
            print(f"Warning: Framework directory not found: {framework_dir}")
            return []

        # Get all .md files
        files = list(framework_dir.rglob('*.md'))

        # Sort: root files first, then by path
        def sort_key(path: Path):
            relative = path.relative_to(framework_dir)
            depth = len(relative.parts)
            return (depth, str(relative).lower())

        return sorted(files, key=sort_key)

    def create_title_page(self, framework: str) -> str:
        """Create a title page in Markdown"""
        config = self.FRAMEWORK_CONFIG.get(framework, {
            'title': framework.capitalize(),
            'subtitle': 'Documentation',
            'recommended_max': 100,
        })

        from datetime import datetime
        current_date = datetime.now().strftime('%Y-%m-%d')

        return f"""---
title: "{config['title']}"
subtitle: "{config['subtitle']}"
author: "Apple Inc."
date: "{current_date}"
toc: true
toc-depth: 2
---

\\begin{{center}}
\\Huge {config['title']}

\\vspace{{0.5cm}}

\\Large {config['subtitle']}

\\vspace{{1cm}}

\\normalsize Apple Developer Documentation

Offline Archive

{current_date}
\\end{{center}}

---

\\newpage

"""

    def process_markdown_file(self, file_path: Path, framework_dir: Path) -> str:
        """Process a single markdown file for inclusion in combined PDF"""

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Remove YAML frontmatter (between --- lines)
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                content = parts[2].strip()

        # Add relative path as context
        relative_path = file_path.relative_to(framework_dir)

        # Add page break and file reference
        header = f"\n\\newpage\n\n<!-- File: {relative_path} -->\n\n"

        return header + content + "\n\n"

    def convert_framework_to_pdf(self, framework: str, max_files: int = None):
        """Convert all markdown files for a framework to a single PDF"""

        config = self.FRAMEWORK_CONFIG.get(framework, {})
        recommended_max = config.get('recommended_max', 100)

        print(f"\nConverting {framework} to PDF...")
        print(f"Framework: {config.get('title', framework)}")

        # Get all files
        files = self.get_framework_files(framework)

        if not files:
            print(f"No files found for {framework}")
            return

        total_files = len(files)
        print(f"Found {total_files} markdown files")

        # Determine how many files to use
        if max_files is None:
            # No limit specified - use recommended or warn
            if total_files > recommended_max:
                print(f"\n⚠️  WARNING: {total_files} files is quite large!")
                print(f"   Recommended: {recommended_max} files for a manageable PDF")
                print(f"   Use --max-files {recommended_max} for recommended size")
                print(f"   or --max-files {total_files} to include all (may be very large!)")

                # Ask for confirmation
                response = input(f"\nProceed with ALL {total_files} files? (y/N): ")
                if response.lower() != 'y':
                    print("Cancelled. Rerun with --max-files to specify a limit.")
                    return
            files_to_use = files
        else:
            files_to_use = files[:max_files]
            print(f"Limiting to first {max_files} of {total_files} files")
            if max_files < recommended_max and total_files > recommended_max:
                print(f"💡 Tip: Recommended is {recommended_max} files for this framework")

        print(f"\nProcessing {len(files_to_use)} files...")

        # Create combined markdown
        combined_md = self.create_title_page(framework)

        framework_dir = self.markdown_dir / framework

        print("Processing files...")
        for i, file_path in enumerate(files_to_use, 1):
            if i % 100 == 0:
                print(f"  Processed {i}/{len(files_to_use)} files...")

            try:
                combined_md += self.process_markdown_file(file_path, framework_dir)
            except Exception as e:
                print(f"  Warning: Error processing {file_path}: {e}")

        # Save combined markdown
        combined_md_file = self.pdf_dir / f'{framework}_combined.md'
        with open(combined_md_file, 'w', encoding='utf-8') as f:
            f.write(combined_md)

        print(f"Combined markdown saved to: {combined_md_file}")

        # Convert to PDF using pandoc
        output_pdf = self.pdf_dir / f'{framework}_documentation.pdf'

        print(f"\nGenerating PDF: {output_pdf}")
        print("This may take several minutes...")

        pandoc_args = [
            'pandoc',
            str(combined_md_file),
            '-o', str(output_pdf),
            '--pdf-engine=xelatex',
            '--toc',
            '--toc-depth=2',
            '--highlight-style=tango',
            '--number-sections',
            '-V', 'geometry:margin=1in',
            '-V', 'fontsize=10pt',
            '-V', 'colorlinks=true',
            '-V', 'linkcolor=blue',
            '-V', 'urlcolor=blue',
        ]

        try:
            result = subprocess.run(pandoc_args,
                                   capture_output=True,
                                   text=True,
                                   timeout=600)  # 10 minute timeout

            if result.returncode == 0:
                print(f"\n✅ PDF created successfully: {output_pdf}")

                # Get file size
                size_mb = output_pdf.stat().st_size / (1024 * 1024)
                print(f"   Size: {size_mb:.1f} MB")

                # Clean up combined markdown
                combined_md_file.unlink()

            else:
                print(f"\n❌ Error creating PDF:")
                print(result.stderr)

        except subprocess.TimeoutExpired:
            print("\n❌ PDF generation timed out (>10 minutes)")
            print("   Try with --max-files to create a smaller PDF")
        except Exception as e:
            print(f"\n❌ Error running pandoc: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Convert Markdown documentation to PDF',
        epilog="""
Examples:
  # Convert Swift framework to PDF
  python scripts/04_markdown_to_pdf.py --framework swift

  # Convert first 100 files only (for testing)
  python scripts/04_markdown_to_pdf.py --framework swift --max-files 100

  # Convert multiple frameworks
  python scripts/04_markdown_to_pdf.py --framework swift swiftui
        """
    )

    parser.add_argument('--framework', nargs='+', required=True,
                       help='Framework(s) to convert (e.g., swift swiftui)')
    parser.add_argument('--base-dir', default='.',
                       help='Base directory (default: project directory)')
    parser.add_argument('--max-files', type=int,
                       help='Maximum number of files to include (for testing)')

    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent / args.base_dir if args.base_dir == '.' else Path(args.base_dir)

    converter = MarkdownToPDF(base_dir=base_dir)

    # Check if pandoc is installed
    if not converter.check_pandoc():
        print("❌ Error: pandoc is not installed")
        print("\nTo install pandoc:")
        print("  macOS:   brew install pandoc basictex")
        print("  Linux:   sudo apt-get install pandoc texlive-xetex")
        print("  Windows: choco install pandoc miktex")
        sys.exit(1)

    # Convert each framework
    for framework in args.framework:
        try:
            converter.convert_framework_to_pdf(framework, max_files=args.max_files)
        except Exception as e:
            print(f"\n❌ Error converting {framework}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*70)
    print("PDF Generation Complete!")
    print("="*70)
    print(f"\nPDFs saved to: {converter.pdf_dir}/")


if __name__ == '__main__':
    main()
