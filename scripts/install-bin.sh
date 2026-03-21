#!/bin/bash
set -e

PLUGIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Add shell alias so `claude` always loads this plugin
ALIAS_LINE="alias claude='claude --plugin-dir \$HOME/.claude/plugins/duplo'"

add_alias_to() {
  local rc_file="$1"
  if [ -f "$rc_file" ]; then
    if grep -q "plugin-dir.*duplo" "$rc_file" 2>/dev/null; then
      echo "Plugin alias already present in $rc_file"
    else
      echo "" >> "$rc_file"
      echo "# DuploCloud plugin" >> "$rc_file"
      echo "$ALIAS_LINE" >> "$rc_file"
      echo "Added plugin alias to $rc_file"
    fi
  fi
}

add_alias_to "$HOME/.zshrc"
add_alias_to "$HOME/.bashrc"
add_alias_to "$HOME/.bash_profile"

echo ""
echo "Installation complete."
echo ""
echo "Next steps:"
echo "  1. Copy $PLUGIN_DIR/.env.example to $PLUGIN_DIR/.env"
echo "  2. Fill in DUPLO_TOKEN and DUPLO_HELPDESK_URL in .env"
echo "  3. Restart your shell (or run: source ~/.zshrc)"
echo "  4. Run: source $PLUGIN_DIR/.env && claude"
