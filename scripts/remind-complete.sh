#!/bin/bash
STATE_FILE=".duplocloud/state.toon"
[ ! -f "$STATE_FILE" ] && exit 0

TICKET=$(grep '^active_ticket_name:' "$STATE_FILE" 2>/dev/null | sed 's/^active_ticket_name: *//')
[ -z "$TICKET" ] && exit 0

TITLE=$(grep '^project_name:' "$STATE_FILE" 2>/dev/null | sed 's/^project_name: *//')
echo "Active ticket: [$TITLE] ($TICKET). If this work is complete, call the DuploCloud MCP tool to mark the ticket done and update .duplocloud/state.toon active_ticket_name to the next ticket (or clear it if all done)."
exit 0
