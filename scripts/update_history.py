#!/usr/bin/env python3
"""
Apple Documentation Update History Viewer
Shows chronological history of all documentation updates (like git log)
"""

import json
from pathlib import Path
from datetime import datetime
import argparse


class UpdateHistory:
    """Displays update history from version snapshots and changelogs"""

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.docsync_dir = self.base_dir / '.docsync'
        self.versions_dir = self.docsync_dir / 'versions'
        self.changelog_dir = self.docsync_dir / 'changelog'

    def load_versions(self):
        """Load all version snapshots, sorted newest first"""
        if not self.versions_dir.exists():
            return []

        versions = []
        for version_file in sorted(self.versions_dir.glob('*.json'), reverse=True):
            try:
                with open(version_file, 'r') as f:
                    data = json.load(f)
                data['version_id'] = version_file.stem
                versions.append(data)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not read {version_file}: {e}")

        return versions

    def load_changelogs(self):
        """Load all changelogs, keyed by filename stem"""
        changelogs = {}

        if not self.changelog_dir.exists():
            return changelogs

        for changelog_file in self.changelog_dir.glob('*.md'):
            try:
                with open(changelog_file, 'r', encoding='utf-8') as f:
                    changelogs[changelog_file.stem] = f.read()
            except IOError:
                pass

        return changelogs

    def get_frameworks(self, version):
        """Get frameworks dict from version, handling both key names"""
        return version.get('frameworks', version.get('frameworks_affected', {}))

    def filter_by_framework(self, versions, framework):
        """Filter versions to only those affecting a specific framework"""
        filtered = []
        for v in versions:
            frameworks = self.get_frameworks(v)
            if framework in frameworks:
                filtered.append(v)
        return filtered

    def format_timestamp(self, iso_timestamp):
        """Format ISO timestamp to readable string"""
        try:
            dt = datetime.fromisoformat(iso_timestamp)
            return dt.strftime('%Y-%m-%d %H:%M')
        except (ValueError, TypeError):
            return str(iso_timestamp)

    def format_time_ago(self, iso_timestamp):
        """Format ISO timestamp as relative time"""
        try:
            dt = datetime.fromisoformat(iso_timestamp)
            now = datetime.now()
            diff = now - dt

            if diff.days > 365:
                return f"{diff.days // 365} year(s) ago"
            elif diff.days > 30:
                return f"{diff.days // 30} month(s) ago"
            elif diff.days > 0:
                return f"{diff.days} day(s) ago"
            elif diff.seconds > 3600:
                return f"{diff.seconds // 3600} hour(s) ago"
            elif diff.seconds > 60:
                return f"{diff.seconds // 60} minute(s) ago"
            else:
                return "just now"
        except (ValueError, TypeError):
            return ""

    def format_frameworks_summary(self, frameworks):
        """Format frameworks dict as compact summary"""
        if not frameworks:
            return "none"

        items = sorted(frameworks.items(), key=lambda x: x[1], reverse=True)
        parts = [f"{name} ({count:,})" for name, count in items[:5]]
        if len(items) > 5:
            parts.append(f"... +{len(items) - 5} more")
        return ', '.join(parts)

    def print_timeline(self, versions, changelogs, detailed=False):
        """Print formatted timeline"""
        print("\n" + "=" * 70)
        print("Apple Documentation Update History")
        print("=" * 70)

        if not versions:
            print("\nNo version history found.")
            print("Run 02_download_json.py to create the initial download.")
            print("=" * 70)
            return

        for i, version in enumerate(versions):
            timestamp = version.get('timestamp', '')
            version_type = version.get('type', 'unknown')
            version_id = version.get('version_id', '')
            stats = version.get('stats', {})
            frameworks = self.get_frameworks(version)
            total_pages = version.get('total_pages', version.get('pages_updated', 0))

            # Header line
            time_str = self.format_timestamp(timestamp)
            time_ago = self.format_time_ago(timestamp)
            print(f"\n[{time_str}] {version_type}" + (f"  ({time_ago})" if time_ago else ""))

            # Stats line
            if total_pages:
                print(f"  Pages: {total_pages:,}", end="")
            if frameworks:
                print(f" | Frameworks: {len(frameworks)}", end="")
            print()

            # Download stats
            downloaded = stats.get('downloaded', 0)
            failed = stats.get('failed', 0)
            skipped = stats.get('skipped', 0)
            if downloaded or failed:
                parts = []
                if downloaded:
                    parts.append(f"Downloaded: {downloaded:,}")
                if failed:
                    parts.append(f"Failed: {failed}")
                if skipped:
                    parts.append(f"Skipped: {skipped:,}")
                print(f"  {' | '.join(parts)}")

            # Frameworks summary
            if frameworks:
                print(f"  Frameworks: {self.format_frameworks_summary(frameworks)}")

            # Detailed: show changelog if available
            if detailed and version_id in changelogs:
                print(f"\n  --- Changelog ---")
                for line in changelogs[version_id].splitlines():
                    print(f"  {line}")
                print(f"  -----------------")

            # Separator between entries
            if i < len(versions) - 1:
                print("  " + "-" * 40)

        print(f"\nShowing {len(versions)} snapshot(s)")
        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description='View Apple documentation update history')
    parser.add_argument('--limit', type=int, default=0, help='Show only the last N entries (default: all)')
    parser.add_argument('--framework', type=str, help='Filter to entries affecting this framework')
    parser.add_argument('--detailed', action='store_true', help='Show full changelog content')
    parser.add_argument('--base-dir', default='.', help='Base directory (default: project directory)')

    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent / args.base_dir if args.base_dir == '.' else Path(args.base_dir)

    history = UpdateHistory(base_dir=base_dir)

    # Load data
    versions = history.load_versions()
    changelogs = history.load_changelogs()

    # Apply filters
    if args.framework:
        versions = history.filter_by_framework(versions, args.framework.lower())

    if args.limit and args.limit > 0:
        versions = versions[:args.limit]

    # Display
    history.print_timeline(versions, changelogs, detailed=args.detailed)


if __name__ == '__main__':
    main()
