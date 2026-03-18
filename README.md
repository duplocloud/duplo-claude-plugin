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
