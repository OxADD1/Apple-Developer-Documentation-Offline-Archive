#!/usr/bin/env python3
"""
Apple Documentation Version Rollback
Restores documentation to a previous version from backup (like git revert)
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
import argparse


class UpdateRollback:
    """Rolls back documentation to a previous backed-up version"""

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.docsync_dir = self.base_dir / '.docsync'
        self.backup_dir = self.docsync_dir / 'backup'
        self.raw_json_dir = self.base_dir / 'raw-json'
        self.markdown_dir = self.base_dir / 'markdown'
        self.manifest_file = self.docsync_dir / 'manifest.json'

    def load_manifest(self):
        """Load current manifest"""
        if not self.manifest_file.exists():
            print("Error: Manifest not found.")
            exit(1)

        with open(self.manifest_file, 'r') as f:
            return json.load(f)

    def save_manifest(self, manifest):
        """Save updated manifest"""
        with open(self.manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)

    def list_backups(self):
        """List all available backups"""
        print("\n" + "=" * 70)
        print("Available Backups")
        print("=" * 70)

        if not self.backup_dir.exists():
            print("\nNo backups found.")
            print("Backups are created automatically when running update_pull.py")
            print("=" * 70)
            return []

        backups = []
        for backup_path in sorted(self.backup_dir.iterdir(), reverse=True):
            if not backup_path.is_dir():
                continue

            info_file = backup_path / 'backup_info.json'
            if not info_file.exists():
                continue

            try:
                with open(info_file, 'r') as f:
                    info = json.load(f)
                info['backup_id'] = backup_path.name
                backups.append(info)
            except (json.JSONDecodeError, IOError):
                continue

        if not backups:
            print("\nNo backups found.")
            print("Backups are created automatically when running update_pull.py")
            print("=" * 70)
            return []

        for i, backup in enumerate(backups):
            timestamp = backup.get('timestamp', '')
            pages = backup.get('pages_backed_up', 0)
            frameworks = backup.get('frameworks_affected', {})
            backup_id = backup['backup_id']

            try:
                dt = datetime.fromisoformat(timestamp)
                time_str = dt.strftime('%Y-%m-%d %H:%M')
            except (ValueError, TypeError):
                time_str = backup_id

            print(f"\n  [{backup_id}]")
            print(f"    Date: {time_str}")
            print(f"    Pages: {pages}")
            if frameworks:
                fw_summary = ', '.join(f"{k} ({v})" for k, v in sorted(frameworks.items()))
                print(f"    Frameworks: {fw_summary}")

        print(f"\nTotal: {len(backups)} backup(s)")
        print(f"\nTo restore a backup:")
        print(f"  python scripts/update_rollback.py --rollback <backup_id>")
        print(f"\nTo preview changes first:")
        print(f"  python scripts/update_rollback.py --rollback <backup_id> --dry-run")
        print("=" * 70)

        return backups

    def validate_backup(self, backup_id):
        """Validate that a backup is complete and restorable"""
        backup_path = self.backup_dir / backup_id

        if not backup_path.exists():
            print(f"Error: Backup '{backup_id}' not found.")
            return False

        # Check backup info
        info_file = backup_path / 'backup_info.json'
        if not info_file.exists():
            print(f"Error: Backup '{backup_id}' is missing backup_info.json")
            return False

        # Check manifest entries
        entries_file = backup_path / 'manifest_entries.json'
        if not entries_file.exists():
            print(f"Error: Backup '{backup_id}' is missing manifest_entries.json")
            return False

        # Check backed-up files exist
        with open(entries_file, 'r') as f:
            entries = json.load(f)

        missing_files = []
        for doc_path in entries:
            json_backup = backup_path / 'raw-json' / f'{doc_path}.json'
            if not json_backup.exists():
                missing_files.append(f'raw-json/{doc_path}.json')

        if missing_files:
            print(f"Warning: {len(missing_files)} backed-up file(s) missing from backup:")
            for f in missing_files[:10]:
                print(f"  - {f}")
            if len(missing_files) > 10:
                print(f"  ... and {len(missing_files) - 10} more")

        return True

    def rollback(self, backup_id, dry_run=False):
        """Restore documentation from a backup"""
        print(f"\n{'[DRY RUN] ' if dry_run else ''}Rolling back to backup: {backup_id}")
        print("-" * 50)

        if not self.validate_backup(backup_id):
            return False

        backup_path = self.backup_dir / backup_id

        # Load backup data
        with open(backup_path / 'manifest_entries.json', 'r') as f:
            backed_up_entries = json.load(f)

        with open(backup_path / 'backup_info.json', 'r') as f:
            backup_info = json.load(f)

        # Stats
        restored_json = 0
        restored_md = 0
        restored_manifest = 0
        skipped = 0

        # Load current manifest
        manifest = self.load_manifest() if not dry_run else {}

        for doc_path, old_manifest_entry in backed_up_entries.items():
            # Restore JSON file
            json_backup = backup_path / 'raw-json' / f'{doc_path}.json'
            json_dest = self.raw_json_dir / f'{doc_path}.json'

            if json_backup.exists():
                if dry_run:
                    print(f"  Would restore: raw-json/{doc_path}.json")
                else:
                    json_dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(json_backup, json_dest)
                restored_json += 1
            else:
                skipped += 1

            # Restore Markdown file
            md_backup = backup_path / 'markdown' / f'{doc_path}.md'
            md_dest = self.markdown_dir / f'{doc_path}.md'

            if md_backup.exists():
                if dry_run:
                    print(f"  Would restore: markdown/{doc_path}.md")
                else:
                    md_dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(md_backup, md_dest)
                restored_md += 1

            # Restore manifest entry
            if not dry_run:
                manifest[doc_path] = old_manifest_entry
            restored_manifest += 1

        # Save restored manifest
        if not dry_run:
            self.save_manifest(manifest)

        # Create version snapshot for rollback
        if not dry_run:
            self.create_rollback_snapshot(backup_id, backup_info, restored_json)

        # Summary
        prefix = "[DRY RUN] " if dry_run else ""
        print(f"\n{prefix}Rollback Summary:")
        print(f"  JSON files restored: {restored_json}")
        print(f"  Markdown files restored: {restored_md}")
        print(f"  Manifest entries restored: {restored_manifest}")
        if skipped:
            print(f"  Skipped (missing from backup): {skipped}")

        if dry_run:
            print(f"\nRun without --dry-run to apply these changes.")
        else:
            print(f"\nRollback complete!")

        return True

    def create_rollback_snapshot(self, backup_id, backup_info, pages_restored):
        """Create a version snapshot recording this rollback"""
        versions_dir = self.docsync_dir / 'versions'
        versions_dir.mkdir(parents=True, exist_ok=True)

        version_file = versions_dir / f'{datetime.now().strftime("%Y-%m-%d_%H-%M")}.json'

        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'type': 'rollback',
            'rolled_back_to': backup_id,
            'stats': {
                'restored': pages_restored,
                'failed': 0,
            },
            'frameworks_affected': backup_info.get('frameworks_affected', {}),
        }

        with open(version_file, 'w') as f:
            json.dump(snapshot, f, indent=2)

        print(f"  Version snapshot saved to: {version_file}")


def main():
    parser = argparse.ArgumentParser(description='Rollback Apple documentation to a previous version')
    parser.add_argument('--list', action='store_true', help='List available backups')
    parser.add_argument('--rollback', type=str, help='Restore from specified backup (use backup ID from --list)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be restored without making changes')
    parser.add_argument('--base-dir', default='.', help='Base directory (default: project directory)')

    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent / args.base_dir if args.base_dir == '.' else Path(args.base_dir)

    rollback = UpdateRollback(base_dir=base_dir)

    if args.rollback:
        rollback.rollback(args.rollback, dry_run=args.dry_run)
    elif args.list or not args.rollback:
        rollback.list_backups()


if __name__ == '__main__':
    main()
