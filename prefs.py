from __future__ import annotations

import json
import os
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any

PREFERENCES_FILE = Path(os.path.expanduser("~/.claude/usage-preferences.json"))


def _load_preferences() -> dict[str, Any]:
    if not PREFERENCES_FILE.exists():
        return {}
    try:
        data = json.loads(PREFERENCES_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_preferences(data: dict[str, Any]) -> None:
    PREFERENCES_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    tmp_path: str | None = None
    try:
        fd, tmp_path = tempfile.mkstemp(dir=PREFERENCES_FILE.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp_path, PREFERENCES_FILE)
        tmp_path = None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            with suppress(OSError):
                os.unlink(tmp_path)
