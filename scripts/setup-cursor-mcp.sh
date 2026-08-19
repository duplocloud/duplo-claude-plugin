#!/usr/bin/env bash
# Generate .cursor/mcp.json from .env.
#
# Cursor does not read .mcp.json (that file is Claude Code's) and it does not
# expand ${VAR} from your shell, so the values are written out literally.
# The generated file is gitignored — re-run this whenever .env changes.
set -euo pipefail

cd "$(dirname "$0")/.."
[ -f .env ] || { echo ".env not found — copy .env.example to .env first" >&2; exit 1; }
set -a; . ./.env; set +a

: "${DUPLO_HELPDESK_URL:?DUPLO_HELPDESK_URL not set in .env}"
: "${DUPLO_TOKEN:?DUPLO_TOKEN not set in .env}"

mkdir -p .cursor
URL="${DUPLO_HELPDESK_URL%/}/mcp" TOKEN="$DUPLO_TOKEN" python3 - <<'PY' > .cursor/mcp.json
import json, os
print(json.dumps({"mcpServers": {"duplo-helpdesk": {
    "url": os.environ["URL"],
    "headers": {
        # Accept is deliberately NOT set here — the MCP client owns that header.
        "Authorization": "Bearer " + os.environ["TOKEN"],
        "X-Response-Format": "toon",
    },
}}}, indent=2))
PY
chmod 600 .cursor/mcp.json
cat <<MSG
wrote .cursor/mcp.json -> $DUPLO_HELPDESK_URL

Next: fully quit Cursor (Cmd-Q) and reopen this folder. "Reload Window" does not
re-scan a newly created .cursor/mcp.json. Then open Settings -> MCP and enable
"duplo-helpdesk" -- Cursor lands new servers disabled until you toggle them on.
MSG
