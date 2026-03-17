#!/bin/bash
# use-local.sh — Point the plugin at the current working directory.
#
# Use this when developing the plugin locally instead of running from a
# git clone at ~/.claude/plugins/duplo.
#
# What it does:
#   1. Replaces ~/.claude/plugins/duplo with a symlink to this directory
#   2. Re-runs install-bin.sh so ~/.duplocloud/bin/ symlinks are refreshed

set -e

PLUGIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLUGIN_LINK="$HOME/.claude/plugins/duplo"

echo "Linking plugin directory..."
mkdir -p "$(dirname "$PLUGIN_LINK")"

# Remove existing dir or symlink
if [ -L "$PLUGIN_LINK" ]; then
  rm "$PLUGIN_LINK"
elif [ -d "$PLUGIN_LINK" ]; then
  echo "Warning: $PLUGIN_LINK is a real directory (not a symlink)."
  echo "Remove it manually first if you want to replace it:"
  echo "  rm -rf $PLUGIN_LINK"
  exit 1
fi

ln -s "$PLUGIN_DIR" "$PLUGIN_LINK"
echo "  $PLUGIN_LINK -> $PLUGIN_DIR"

echo ""
echo "Refreshing bin symlinks..."
bash "$PLUGIN_DIR/scripts/install-bin.sh"
