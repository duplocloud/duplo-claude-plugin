---
name: deactivate
description: Deactivate DuploCloud context and clear credentials
disable-model-invocation: true
---

Deactivate DuploCloud mode by clearing all credentials and project context.

## Steps

1. Confirm with the user: **"This will clear your DuploCloud credentials and project context. Continue? (yes/no)"**

2. If yes:
   - Delete `~/.duplocloud/.auth`
   - Delete `.duplocloud/state.json` if present in the current working directory

3. Confirm: **"DuploCloud deactivated. Claude is back to normal behavior."**

## Notes

- After deactivation, the enforcement hook will no longer block edits/writes/bash commands
- Re-activate at any time with `/duplo:activate_project`
- Project state (`.duplocloud/` directory and its contents) is not fully deleted — only the active `state.json` is removed
