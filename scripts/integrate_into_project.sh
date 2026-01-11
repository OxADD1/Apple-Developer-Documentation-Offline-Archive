#!/bin/bash

# integrate_into_project.sh
# 
# Usage: ./integrate_into_project.sh /path/to/your/swift/project
#
# This script creates a symbolic link to this documentation archive inside 
# your target project, allowing an AI agent to run the download scripts 
# and access the markdown files directly from that project's context.

set -e

# Get the absolute path of the archive repo (where this script is located's parent)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ARCHIVE_ROOT="$(dirname "$SCRIPT_DIR")"

TARGET_PROJECT="$1"

if [ -z "$TARGET_PROJECT" ]; then
    echo "Usage: ./scripts/integrate_into_project.sh <path-to-your-project>"
    echo "Example: ./scripts/integrate_into_project.sh ~/code/my-ios-app"
    exit 1
fi

# Ensure target exists
if [ ! -d "$TARGET_PROJECT" ]; then
    echo "Error: Target directory '$TARGET_PROJECT' does not exist."
    exit 1
fi

LINK_NAME="apple-docs"
TARGET_LINK="$TARGET_PROJECT/$LINK_NAME"

# 1. Create Symlink
echo "Creating symlink at $TARGET_LINK -> $ARCHIVE_ROOT"
if [ -e "$TARGET_LINK" ]; then
    echo "Warning: '$LINK_NAME' already exists in target project. Skipping symlink creation."
else
    ln -s "$ARCHIVE_ROOT" "$TARGET_LINK"
    echo "✅ Symlink created."
fi

# 2. Add to .gitignore
GITIGNORE="$TARGET_PROJECT/.gitignore"
if [ -f "$GITIGNORE" ]; then
    if grep -q "^$LINK_NAME/$" "$GITIGNORE"; then
        echo "ℹ️  '$LINK_NAME' is already ignored in $GITIGNORE"
    else
        echo "" >> "$GITIGNORE"
        echo "# Apple Documentation Archive (Local Symlink)" >> "$GITIGNORE"
        echo "$LINK_NAME/" >> "$GITIGNORE"
        echo "✅ Added '$LINK_NAME/' to .gitignore"
    fi
else
    echo "Warning: No .gitignore found in target project. Creating one."
    echo "# Apple Documentation Archive (Local Symlink)" > "$GITIGNORE"
    echo "$LINK_NAME/" >> "$GITIGNORE"
    echo "✅ Created .gitignore with '$LINK_NAME/'"
fi

echo ""
echo "Integration Complete! 🚀"
echo "---------------------------------------------------"
echo "Your AI agent can now access the full archive in your project at:"
echo "  ./$LINK_NAME"
echo ""
echo "Example usage for Agent:"
echo "  'Check ./apple-docs for SwiftData documentation'"
echo "  'Run ./apple-docs/scripts/01_discover_docs.py --framework coreml to download new docs'"
