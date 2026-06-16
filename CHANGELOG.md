# Changelog

All notable changes to the DuploCloud Claude Plugin are documented here.

---

## [Unreleased] — Phase 1: Foundation

### Added

- **`.mcp.json`** — Declares the `duplo-helpdesk` HTTP MCP server. Claude Code loads this
  automatically from the plugin directory and exposes all server tools in every session.
  Server URL and Bearer token are read from environment variables.

  ```json
  {
    "mcpServers": {
      "duplo-helpdesk": {
        "type": "http",
        "url": "${DUPLO_HELPDESK_URL}/mcp",
        "headers": { "Authorization": "Bearer ${DUPLO_TOKEN}" }
      }
    }
  }
  ```

  To discover available tool names in a live session, open Claude Code in this directory
  with both env vars exported. Tools appear as `mcp__duplo-helpdesk__<OperationId>`.

- **`.env.example`** — Template for required environment variables (`DUPLO_TOKEN`, `DUPLO_HELPDESK_URL`).
  Copy to `.env`, fill in values, and run `source .env` before launching Claude.

- **`.gitignore`** — Ensures `.env` (which contains the token) is never committed.

- **`skills/check_mcp`** — Health check skill. Run `/duplo:check_mcp` inside a Claude session
  to verify the MCP server is reachable. Uses MCP tools directly — no shell script needed.

### Changed

- **`CLAUDE.md`** — Removed all Python script references. Added MCP server section, local state
  schema (`.duplocloud/state.json`), and MCP connection error guidance.

- **`scripts/install-bin.sh`** — Removed Python symlink and allowedTools registration logic.
  Now only sets the shell alias and prints setup instructions.

### Removed

- **`bin/`** — All Python scripts deleted (`duplo_activate.py`, `duplo_ticket.py`,
  `duplo_common.py`, `duplo_mirror.py`, `mcp_proxy.py`). All API calls move to MCP tools.

- **`hooks/hooks.json`** — Removed. Hooks were tied to Python scripts that no longer exist.

---

## [1.0.0] — initial public release

- First public release with Python-based CLI tools making direct HTTP calls to the
  DuploCloud AI Helpdesk API
- Skills: `activate_project`, `activate_ticket`, `write_spec`, `write_plan`,
  `save_summary`, `deactivate`
- Async conversation mirroring via `UserPromptSubmit` / `Stop` hooks
- Per-session state isolation via `~/.duplocloud/sessions/<id>/state.json`
