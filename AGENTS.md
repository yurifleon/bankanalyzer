# AGENTS.md

Agent guidance for this repository lives in [CLAUDE.md](CLAUDE.md) — commands, architecture, CSV profiles, and container notes. Keep that file as the single source of truth; update it (and [USER_MANUAL.md](USER_MANUAL.md) where user-facing) when behavior changes.

Quick reminders:

- Run tests before and after edits: `python -m unittest discover -s tests`
- `web_app.py` imports the analyzer's public functions directly — keep their signatures stable (see CLAUDE.md "Architecture").
