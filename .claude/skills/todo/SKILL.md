---
name: todo
description: Record a to-do list dictated by the user into ToDo.md (with today's date), and check that file at the start of every session so the user sees right away what's left to do.
---

# /todo

Use this when the user types `/todo` followed by the things they want done next time (e.g. `/todo corriger le bug X, ajouter Y`).

## Adding items (`/todo <items>`)

1. Open `ToDo.md` at the project root (create it if missing, with a top-level `# ToDo` heading).
2. Add a new section for today using the creation date:
   ```
   ## YYYY-MM-DD
   - [ ] item 1
   - [ ] item 2
   ```
   Add the new dated section at the **top** of the file (most recent first), right under the `# ToDo` heading.
3. Split whatever the user dictated into separate checklist items (`- [ ] ...`), one per task. Keep their wording, just clean it up into clear, actionable bullets — don't invent extra scope they didn't ask for.
4. Confirm back to the user in French what was added.

## Reading it back (start of session / whenever asked)

- Read `ToDo.md` whenever the user opens this project or asks what's left to do.
- Report unchecked (`- [ ]`) items grouped by date, oldest first, so nothing gets silently dropped.
- When the user says an item is done, mark it `- [x]` in `ToDo.md` directly rather than just acknowledging it in chat — the file should stay the source of truth.
- Don't delete past dated sections automatically; only remove a section if the user explicitly says to clear it out.
