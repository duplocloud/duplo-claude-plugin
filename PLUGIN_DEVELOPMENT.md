# Claude Code Plugin Development Guide

Reference for building Claude Code plugins like the DuploCloud plugin.

---

## Plugin Structure

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json          # Plugin metadata (required)
├── .mcp.json                # MCP server config (optional)
├── CLAUDE.md                # Claude behavior rules for this plugin
├── bin/                     # CLI tools (Python/shell scripts)
├── hooks/
│   └── hooks.json           # Lifecycle hook configuration
├── scripts/                 # Scripts invoked by hooks
└── skills/                  # Claude Code skills (slash commands)
    └── my_skill/
        └── SKILL.md         # Skill prompt invoked via /plugin:my_skill
```

---

## plugin.json

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "Short description of what this plugin does"
}
```

The `name` field becomes the skill namespace prefix (e.g., `/my-plugin:skill_name`).

---

## CLAUDE.md

Controls which tools Claude can use within this plugin context.

```markdown
# My Plugin

## Allowed Tools
- Bash(*)
```

Use `Bash(*)` to allow all bash commands. You can restrict to specific patterns:
- `Bash(git *)` — only git commands
- `Read`, `Write`, `Edit` — specific tools by name

---

## Skills (SKILL.md)

Each subdirectory under `skills/` defines one slash command.

**Naming:** `skills/my_action/SKILL.md` → invoked as `/plugin-name:my_action`

**SKILL.md format:** Plain markdown that Claude reads and executes as instructions. Write it as a step-by-step workflow Claude should follow when the skill is invoked.

```markdown
# My Action

Brief description of what this skill does.

## Steps

### Step 1: Do something
Run this command and show the output to the user:
```bash
python3 ~/.my-plugin/bin/my_tool.py --list
```

### Step 2: Ask the user
Present the results and ask: "Which option would you like?"

### Step 3: Execute
Run the selected option:
```bash
python3 ~/.my-plugin/bin/my_tool.py --select <N>
```
```

**Best practices:**
- Number steps clearly
- Specify exact commands with expected output
- Mark conditional branches explicitly
- State what to show the user at each step

---

## Hooks (hooks.json)

Hooks let you run scripts automatically at key Claude Code lifecycle events.

```json
{
  "UserPromptSubmit": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "/path/to/script.sh"
        },
        {
          "type": "command",
          "command": "/path/to/async-script.sh",
          "async": true
        }
      ]
    }
  ],
  "PreToolUse": [
    {
      "matcher": "Edit|Write|Bash",
      "hooks": [
        {
          "type": "command",
          "command": "/path/to/guard.sh"
        }
      ]
    }
  ],
  "Stop": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "/path/to/cleanup.sh"
        }
      ]
    }
  ]
}
```

### Hook Types

| Type | When it fires | Common use |
|------|--------------|------------|
| `UserPromptSubmit` | Every user message | Setup, logging, mirroring |
| `PreToolUse` | Before a tool runs | Enforcement/gating |
| `Stop` | Session end | Cleanup, reminders, mirroring |

### PreToolUse matcher

The `matcher` field is a regex matched against tool names:
- `"Edit"` — only Edit tool
- `"Edit|Write|MultiEdit"` — multiple tools
- `"Bash"` — all bash commands

### Hook exit codes

| Exit code | Effect |
|-----------|--------|
| `0` | Allow — tool proceeds normally |
| `2` | Block — tool is cancelled, stderr shown to user |

### Hook stdin (PreToolUse)

For `PreToolUse` hooks, Claude passes JSON to stdin describing the tool call:
```json
{
  "tool_name": "Edit",
  "tool_input": {
    "file_path": "/path/to/file.py",
    "..."
  }
}
```

Parse with Python:
```bash
INPUT=$(cat)
TOOL=$(echo "$INPUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('tool_name',''))")
FILE=$(echo "$INPUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))")
```

### async: true

Adding `"async": true` runs the hook in the background without blocking Claude's response. Use for logging, mirroring, or any fire-and-forget side effect.

---

## MCP Integration (.mcp.json)

Connect Claude to external APIs via the Model Context Protocol.

```json
{
  "mcpServers": {
    "my-server": {
      "type": "stdio",
      "command": "python3",
      "args": ["${HOME}/.my-plugin/mcp_proxy.py"]
    }
  }
}
```

### Writing an MCP stdio proxy

The proxy bridges Claude's JSON-RPC 2.0 (stdin/stdout) to an HTTP MCP server:

```python
import sys, json, requests

def handle_request(req):
    # Forward to HTTP MCP server
    resp = requests.post(MCP_URL, json=req, headers={"Authorization": f"Bearer {token}"})
    return resp.json()

for line in sys.stdin:
    req = json.loads(line)
    result = handle_request(req)
    print(json.dumps(result), flush=True)
```

**Key patterns:**
- Re-read auth on every request (supports token refresh without restart)
- Maintain session ID across requests (`Mcp-Session-Id` header)
- Handle both JSON and SSE responses from the server

---

## State Management Pattern

Use two files to separate global credentials from per-project state:

| File | Location | Purpose |
|------|----------|---------|
| Auth/credentials | `~/.my-plugin/.auth` | Global, persists across projects |
| Project state | `.my-plugin/state.json` (CWD) | Per-project, tracks active context |

This pattern means:
- Credentials survive `deactivate`/re-`activate`
- Project state is scoped to the working directory
- Multiple projects can have independent state

---

## CLI Tool Pattern (bin/)

Write Python CLI tools that skills call via bash. Use a consistent exit code convention:

| Exit code | Meaning |
|-----------|---------|
| `0` | Success |
| `1` | Recoverable error (display to user, let them retry) |
| `2` | State/context error (used by hooks to block tool use) |
| `3` | Auth missing or invalid (prompt user to log in) |

Deploy tools to a user-home location so they're available system-wide:

```bash
# install-bin.sh — run on UserPromptSubmit to auto-deploy
BIN_DIR="$HOME/.my-plugin/bin"
mkdir -p "$BIN_DIR"
for script in "$CLAUDE_PLUGIN_ROOT/bin/"*.py; do
  cp "$script" "$BIN_DIR/$(basename "$script")"
done
```

`$CLAUDE_PLUGIN_ROOT` is set by Claude Code to the plugin's root directory.

---

## Enforcement Pattern

To require context before allowing code edits, use a `PreToolUse` hook:

```bash
#!/bin/bash
# require-context.sh

INPUT=$(cat)
STATE_FILE=".my-plugin/state.json"

# No auth = normal Claude, skip enforcement
[ ! -f "$HOME/.my-plugin/.auth" ] && exit 0

# Allow writes to internal state files
FILE=$(echo "$INPUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)
[[ "$FILE" == "$HOME/.my-plugin/"* ]] && exit 0

# Check required context
if [ ! -f "$STATE_FILE" ]; then
  echo "No project context found. Run /my-plugin:activate first." >&2
  exit 2
fi

exit 0
```

---

## Conversation Mirroring Pattern

To mirror Claude conversations to an external system, use async hooks on `UserPromptSubmit` and `Stop`. The hook receives the conversation transcript via stdin (Stop hook) or the user prompt (UserPromptSubmit hook).

```python
# mirror.py — called async by hooks
import sys, json, requests

hook_data = json.load(sys.stdin)

# UserPromptSubmit: hook_data contains the user prompt
# Stop: hook_data contains the full transcript

state = json.load(open(".my-plugin/state.json"))
ticket_id = state.get("active_ticket_id")
if not ticket_id:
    sys.exit(0)

# Post to external system
requests.post(f"{BASE_URL}/tickets/{ticket_id}/message", json={"content": message})
```

---

## settings.local.json

Enable MCP servers for your plugin:

```json
{
  "enabledMcpjsonServers": ["my-server"],
  "enableAllProjectMcpServers": true
}
```

Place at `.claude/settings.local.json` in the plugin root.
