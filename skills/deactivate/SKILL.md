---
name: deactivate
description: Clear the active DuploCloud project context (state.json)
disable-model-invocation: true
---

Deactivate DuploCloud mode by clearing the current project and ticket context.

## Steps

1. Confirm with the user: **"This will clear your active project and ticket context. Continue? (y/n)"**

2. If yes:
   - Delete `.duplocloud/state.json` if it exists in the current working directory

3. Confirm: **"DuploCloud context cleared. Run `/duplo:activate_project` to start a new session."**

## Notes

- This only removes local session state — no data is deleted from the platform
- Re-activate at any time with `/duplo:activate_project`
