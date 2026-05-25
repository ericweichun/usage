# CODEX.md

This fork is Codex-first. Keep Codex usage tracking working without Claude Code installed.

## Development Commands

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

python3 main.py
python3 main.py --mock
python3 main.py --tui
python3 main.py --setup      # configures Codex status_line; Claude hook only if present
python3 main.py --unsetup

python3 -m pytest
```

## Implementation Notes

- Codex data comes from `~/.codex/sessions/**/*.jsonl`; `setup_hook.py` configures `~/.codex/config.toml` `tui.status_line`.
- Claude Code support is optional and must not block app startup, CLI setup, or menu bar display when `~/.claude/` is missing.
- usage-owned state belongs under `~/.usage/`. Legacy `~/.claude/usage-preferences.json` and `~/.claude/pricing_cache.json` remain read-compatible only.
- Tests must monkeypatch path constants before exercising setup/unsetup logic. Do not touch real `~/.codex/` or `~/.claude/` files.
- Keep README and README.en.md in sync for user-facing behavior changes.
