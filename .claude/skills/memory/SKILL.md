---
name: memory
description: Write a short summary of the current session into memory.md (dated entry). Only touch CLAUDE.md if something from this session must be remembered every time the project is opened.
---

# /memory

Trigger: the user says "memory" (or `/memory`), typically at the end of a work session.

## Always do this

1. Look back over the conversation and write a **short** summary (a handful of bullets, not a transcript) of what mattered: decisions made and why, bugs found/fixed, things explicitly left alone, anything the user asked to remember.
2. Open `memory.md` at the project root (create it with a `# Memory` heading + one-line explanation if missing).
3. Add a new entry at the **top** of the file (most recent first):
   ```
   ### YYYY-MM-DD
   - bullet
   - bullet
   ```
   Use today's date.

## Only if it's truly "remember this every time"

4. Separately ask yourself: is there anything from this session that future-you needs to know **every single time** this project is opened, not just as historical record? Examples: a new standing convention, a hardcoded value that must never come back, a gotcha that would cause a real mistake if forgotten (like a test-only setting that must be reverted before a real run).
   - If yes: add it to the relevant section of `CLAUDE.md` (e.g. "Conventions établies", "À surveiller" — create a section if none fits).
   - If no: don't touch `CLAUDE.md` at all. Most sessions won't need this step — a plain summary in `memory.md` is the default and often the only thing needed.

## Notes

- `memory.md` = the journal (one entry per session, append-only, read on demand).
- `CLAUDE.md` = the small set of standing facts/conventions that should shape behavior every time — keep it lean, don't let it grow into a second changelog.
- Reply to the user in French with the same short summary you wrote to `memory.md`, and mention explicitly if you also updated `CLAUDE.md` (and why).
