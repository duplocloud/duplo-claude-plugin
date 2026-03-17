#!/bin/bash
INPUT=$(cat)
AUTH_FILE="$HOME/.duplocloud/.auth"

# No auth = normal Claude, no enforcement
[ ! -f "$AUTH_FILE" ] && exit 0

# Parse tool info
TOOL_NAME=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null)

# Allow writes/edits to ~/.duplocloud/ (credentials) AND local .duplocloud/ (state)
FILE_PATH=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null)
if [[ "$FILE_PATH" == "$HOME/.duplocloud/"* || "$FILE_PATH" == ".duplocloud/"* ]]; then
  exit 0
fi

# Allow read-only shell commands used by the activate flow
if [[ "$TOOL_NAME" == "Bash" ]]; then
  CMD=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null)
  if [[ "$CMD" == curl\ * || "$CMD" == mkdir\ * || "$CMD" == *duplo_activate.py* ]]; then
    exit 0
  fi
fi

# Auth present but no project state
STATE_FILE=".duplocloud/state.json"
if [ ! -f "$STATE_FILE" ]; then
  echo "DuploCloud is activated but no project context. Run /duplo:activate_project first." >&2
  exit 2
fi

PROJECT=$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('project_id',''))" 2>/dev/null)
if [ -z "$PROJECT" ]; then
  echo "DuploCloud state exists but has no project. Run /duplo:activate_project again." >&2
  exit 2
fi

exit 0
