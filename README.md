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

