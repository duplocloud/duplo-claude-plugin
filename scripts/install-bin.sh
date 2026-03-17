#!/bin/bash
set -e

PLUGIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BIN_DIR="$HOME/.duplocloud/bin"
mkdir -p "$BIN_DIR"

# Symlink all Python CLI scripts into ~/.duplocloud/bin/
for script in "$PLUGIN_DIR/bin/"*.py; do
  fname=$(basename "$script")
  ln -sf "$script" "$BIN_DIR/$fname"
done
echo "Installed CLI scripts to $BIN_DIR"

# Register duplo bin commands as pre-approved Bash tools in Claude Code settings
python3 - "$PLUGIN_DIR" <<'PYEOF'
import json, os, pathlib, sys

plugin_dir = pathlib.Path(sys.argv[1])
settings_path = pathlib.Path(os.environ["HOME"]) / ".claude" / "settings.json"

if settings_path.exists():
    with open(settings_path) as f:
        data = json.load(f)
else:
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    data = {}

allowed = data.setdefault("allowedTools", [])

# One entry per script so every command is explicitly pre-approved
bin_dir = pathlib.Path(os.environ["HOME"]) / ".duplocloud" / "bin"
entries = [f"Bash(python3 {bin_dir}/{s.name})" for s in sorted(plugin_dir.glob("bin/*.py"))]

added = []
for entry in entries:
    if entry not in allowed:
        allowed.append(entry)
        added.append(entry)

if added:
    with open(settings_path, "w") as f:
        json.dump(data, f, indent=2)
    for e in added:
        print(f"Added {e!r} to allowedTools")
else:
    print("allowedTools already up to date")
PYEOF

# Add shell alias so `claude` always loads this plugin
ALIAS_LINE="alias claude='claude --plugin-dir $HOME/.claude/plugins/duplo'"

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
echo "Restart your shell (or run: source ~/.zshrc) then use 'claude' as normal."
