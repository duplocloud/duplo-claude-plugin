# DuploCloud Plugin for Claude Code

Ticket-driven workflow enforcement for Claude Code. Integrates with DuploCloud AI Service Desk to ensure all code changes are tied to a ticket, spec, and plan.

## Prerequisites

- [Claude Code](https://claude.ai/code) installed
- Access to a DuploCloud instance with AI Service Desk enabled

## Installation

Clone this repo and run the install script:

```bash
git clone git@github.com:duplocloud/duplo-claude-plugin.git ~/.claude/plugins/duplo
~/.claude/plugins/duplo/scripts/install-bin.sh
```

The install script:
- Installs CLI tools to `~/.duplocloud/bin/`
- Adds them to Claude Code's pre-approved tools
- Adds a shell alias so `claude` always loads this plugin

Restart your shell (or `source ~/.zshrc`), then use `claude` as normal.

## Getting Started

1. **Activate your project** — run `/duplo:activate_project` in Claude Code. This logs you in and sets the project context.
2. **Activate a ticket** — run `/duplo:activate_ticket` to create or resume a ticket.
3. **Write a spec** — run `/duplo:write_spec` to draft and save a specification.
4. **Write a plan** — run `/duplo:write_plan` to draft and save an implementation plan.
5. **Deactivate** — run `/duplo:deactivate` to clear credentials and project context.

## Upgrading

Run the upgrade script to pull the latest version:

```bash
~/.claude/plugins/duplo/scripts/upgrade.sh
```

## Uninstall

```bash
rm -rf ~/.claude/plugins/duplo
rm -rf ~/.duplocloud
```

Also remove the plugin alias from your `~/.zshrc` / `~/.bashrc` (the line containing `plugin-dir.*duplo`).

## Environment Variables

Copy `.env.example` to `.env` and fill in your values. Run `source .env` before launching Claude.

| Variable | Required | Description |
|---|---|---|
| `DUPLO_TOKEN` | ✅ Always | Bearer token for the DuploCloud AI helpdesk API. |
| `DUPLO_HELPDESK_URL` | ✅ Always | Base URL of the duplo-helpdesk MCP server (e.g. `https://mcp-ai-studio.your-company.duplocloud.net`). |
| `DUPLO_AGENT_MODE` | Optional | Controls who responds to ticket messages. See below. |

### DUPLO_AGENT_MODE

| Value | Behaviour |
|---|---|
| `true` (default) | **Remote agent mode.** The DuploCloud backend AI agent handles all ticket responses via `Ticket_send_message_streaming`. The backend enriches every request with workspace credentials, scopes, personas, and secrets before the agent runs. Use this for production workflows. |
| `false` or unset | **Local agent mode.** Claude / Cursor itself acts as the agent. Messages are recorded to the ticket via `message_mode=1` (record-only — no backend AI invoked). Claude fetches workspace context (personas, scopes, project spec/plan) at activation and caches it locally with a 5-minute TTL. Credentials come from the developer's own machine (`~/.aws/credentials`, `~/.kube/config`, etc.). Use this when you want the AI coding assistant to drive the conversation directly. |

### Which mode should I use?

- **Most users**: leave `DUPLO_AGENT_MODE=true`. The remote agent has full scope credentials and runs in a managed environment.
- **Plugin developers / power users**: set `DUPLO_AGENT_MODE=false` to use Claude/Cursor as the agent with your own machine credentials.


## Cursor

Cursor does not read `.mcp.json` — that file is Claude Code's. Generate Cursor's own
config from `.env`:

```bash
source .env
./scripts/setup-cursor-mcp.sh
```

This writes `.cursor/mcp.json` with the values resolved literally (Cursor does not
expand `${VAR}` from your shell). The file is gitignored because it contains your
token — re-run the script whenever `.env` changes.

Then **fully quit Cursor (⌘Q) and reopen the folder** — *Developer: Reload Window* does
not re-scan a newly created `.cursor/mcp.json`. Open Settings → MCP and enable
`duplo-helpdesk`; Cursor lands newly discovered servers disabled until you toggle them
on. Once connected it lists ~1484 tools.

If it still does not show up, check whether Cursor even tried to connect:

```bash
tail -50 "$HOME/Library/Application Support/Cursor/logs/"*/window*/exthost/anysphere.cursor-mcp/"MCP Logs.log"
```

No mention of `duplo-helpdesk` means Cursor never read the config — either the file was
created after Cursor launched, or this repo is not the open workspace root.

## Debugging the MCP server

Use the helper rather than a hand-rolled `curl`:

```bash
source .env
./scripts/mcp-curl.sh tools/list
./scripts/mcp-curl.sh tools/call '{"name":"Workspaces_list","arguments":{}}'
```

A plain `curl` against `/mcp` fails for two reasons:

- **`Not Acceptable: Client must accept both application/json and text/event-stream`** —
  the Streamable HTTP transport requires `Accept: application/json, text/event-stream`
  on every POST.
- **`Bad Request: Missing session ID`** — the server is session-stateful. You must POST
  `initialize` first, read `Mcp-Session-Id` off the response headers, and send it on
  every subsequent request.

`scripts/mcp-curl.sh` does both and strips the SSE `data:` framing so the output pipes
into `jq`. Claude Code and Cursor handle all of this automatically.
