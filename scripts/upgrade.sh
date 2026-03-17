#!/bin/bash
set -e

PLUGIN_DIR="$HOME/.claude/plugins/duplo"

echo "Upgrading DuploCloud plugin..."
git -C "$PLUGIN_DIR" pull --ff-only

echo "Upgrade complete."
