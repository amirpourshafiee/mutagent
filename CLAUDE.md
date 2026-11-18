# CLAUDE.md: working rules for mutagent

- Public data and public code only. Never reference anything from any employer.
- Before any change, create a branch `feature-<brief-description>`. Never commit to `main`.
- Write tests first or alongside. Run `pytest -m "not slow"` before every commit. No commit on red.
- Commit messages: short subject, then a body saying what changed, why, and what was rejected.
- Never commit API keys, `.env`, or files over 1 MB. Raw results JSON stays small and is committed.
- The agent may write only under `tests/`. It never edits source modules and never grades itself.
- Do not `git push` without asking the owner.
- Update `NEXT.md` (5 lines: done, next, open questions) at the end of every session.
