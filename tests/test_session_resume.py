from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

import usage_session_resume as mod


def _write_session(
    path: Path,
    *,
    when: datetime,
    request: str = "",
    commits: list[str] | None = None,
    todos: list[str] | None = None,
) -> None:
    lines: list[dict[str, object]] = []
    if request:
        lines.append(
            {"type": "user", "timestamp": when.isoformat(), "message": {"content": request}}
        )
    content: list[dict[str, object]] = []
    for title in commits or []:
        command = f'git commit -m "{title}"'
        content.append({"type": "tool_use", "name": "Bash", "input": {"command": command}})
    if todos:
        content.append(
            {
                "type": "tool_use",
                "name": "TodoWrite",
                "input": {"todos": [{"content": t, "status": "pending"} for t in todos]},
            }
        )
    lines.append(
        {"type": "assistant", "timestamp": when.isoformat(), "message": {"content": content}}
    )
    path.write_text("\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8")


def _project_dir(tmp_path: Path) -> Path:
    project = tmp_path / "projects" / "-Users-me-Developer-myproj"
    project.mkdir(parents=True)
    return project


def _sidecar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sidecar = tmp_path / "usage-resume-prompt.json"
    sidecar.write_text(
        json.dumps(
            {
                "en": {
                    "prompt": "proj={project} when={when} req={last_request} "
                    "commits={commits} todos={todos}",
                    "none": "(none)",
                    "lead": "LEAD:: ",
                },
                "zh-TW": {
                    "prompt": "專案={project} 請求={last_request}",
                    "none": "（無）",
                    "lead": "前情:: ",
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "PROMPT_SIDECAR", sidecar)


def test_build_prompt_reads_previous_session(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("USAGE_LANG", raising=False)
    monkeypatch.delenv("TT_LANG", raising=False)
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    _sidecar(tmp_path, monkeypatch)
    project = _project_dir(tmp_path)
    now = datetime.now().astimezone()
    _write_session(
        project / "prev.jsonl",
        when=now - timedelta(hours=2),
        request="add a dark mode toggle to the settings panel",
        commits=["fix: the thing"],
    )
    current = project / "current.jsonl"
    current.write_text("", encoding="utf-8")

    prompt = mod._build_prompt(
        {"transcript_path": str(current), "cwd": "/Users/me/Developer/myproj"}
    )

    assert prompt.startswith("LEAD:: ")  # injected lead so Claude visibly acknowledges
    assert "proj=myproj" in prompt
    assert "add a dark mode toggle to the settings panel" in prompt  # the last request
    assert "fix: the thing" in prompt


def test_build_prompt_includes_pending_todos(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    _sidecar(tmp_path, monkeypatch)
    project = _project_dir(tmp_path)
    _write_session(
        project / "prev.jsonl",
        when=datetime.now().astimezone() - timedelta(hours=1),
        request="ship the release",
        todos=["write changelog", "tag the version"],
    )
    current = project / "current.jsonl"
    current.write_text("", encoding="utf-8")

    prompt = mod._build_prompt(
        {"transcript_path": str(current), "cwd": "/Users/me/Developer/myproj"}
    )

    assert "write changelog" in prompt and "tag the version" in prompt


def test_build_prompt_reads_last_prompt_entry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    _sidecar(tmp_path, monkeypatch)
    project = _project_dir(tmp_path)
    when = datetime.now().astimezone() - timedelta(hours=1)
    # A `last-prompt` entry is the cleanest record of what the user asked.
    (project / "prev.jsonl").write_text(
        "\n".join(
            json.dumps(line)
            for line in [
                {
                    "type": "last-prompt",
                    "timestamp": when.isoformat(),
                    "lastPrompt": "refactor the parser",
                },
                {"type": "assistant", "timestamp": when.isoformat(), "message": {"content": []}},
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    current = project / "current.jsonl"
    current.write_text("", encoding="utf-8")

    prompt = mod._build_prompt(
        {"transcript_path": str(current), "cwd": "/Users/me/Developer/myproj"}
    )

    assert "refactor the parser" in prompt


def test_build_prompt_excludes_current_transcript(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    _sidecar(tmp_path, monkeypatch)
    project = _project_dir(tmp_path)
    current = project / "current.jsonl"
    # Only the current transcript exists → no "previous" session to summarise.
    _write_session(current, when=datetime.now().astimezone(), request="do a thing")

    prompt = mod._build_prompt(
        {"transcript_path": str(current), "cwd": "/Users/me/Developer/myproj"}
    )

    assert prompt == ""


def test_build_prompt_skips_sessions_older_than_cutoff(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    _sidecar(tmp_path, monkeypatch)
    project = _project_dir(tmp_path)
    _write_session(
        project / "prev.jsonl",
        when=datetime.now().astimezone() - timedelta(days=mod._MAX_AGE_DAYS + 1),
        request="something old",
    )
    current = project / "current.jsonl"
    current.write_text("", encoding="utf-8")

    prompt = mod._build_prompt(
        {"transcript_path": str(current), "cwd": "/Users/me/Developer/myproj"}
    )

    assert prompt == ""


def test_build_prompt_skips_sessions_without_signal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    _sidecar(tmp_path, monkeypatch)
    project = _project_dir(tmp_path)
    # No user request, no commits, no todos → nothing worth injecting.
    _write_session(
        project / "prev.jsonl",
        when=datetime.now().astimezone() - timedelta(hours=1),
    )
    current = project / "current.jsonl"
    current.write_text("", encoding="utf-8")

    prompt = mod._build_prompt(
        {"transcript_path": str(current), "cwd": "/Users/me/Developer/myproj"}
    )

    assert prompt == ""


def test_build_prompt_falls_back_to_default_when_sidecar_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    monkeypatch.setattr(mod, "PROMPT_SIDECAR", tmp_path / "does-not-exist.json")
    project = _project_dir(tmp_path)
    _write_session(
        project / "prev.jsonl",
        when=datetime.now().astimezone() - timedelta(hours=1),
        request="implement feature x",
        commits=["feat: x"],
    )
    current = project / "current.jsonl"
    current.write_text("", encoding="utf-8")

    prompt = mod._build_prompt(
        {"transcript_path": str(current), "cwd": "/Users/me/Developer/myproj"}
    )

    assert "Last time I was working" in prompt
    assert "myproj" in prompt


def test_build_prompt_uses_detected_language(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("USAGE_LANG", "zh-TW")
    _sidecar(tmp_path, monkeypatch)
    project = _project_dir(tmp_path)
    _write_session(
        project / "prev.jsonl",
        when=datetime.now().astimezone() - timedelta(hours=1),
        request="加一個深色模式",
    )
    current = project / "current.jsonl"
    current.write_text("", encoding="utf-8")

    prompt = mod._build_prompt(
        {"transcript_path": str(current), "cwd": "/Users/me/Developer/myproj"}
    )

    assert prompt.startswith("前情:: ")
    assert "專案=myproj" in prompt
    assert "加一個深色模式" in prompt


def test_main_emits_additional_context(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    _sidecar(tmp_path, monkeypatch)
    project = _project_dir(tmp_path)
    _write_session(
        project / "prev.jsonl",
        when=datetime.now().astimezone() - timedelta(hours=1),
        request="wire up the new endpoint",
        commits=["fix: y"],
    )
    current = project / "current.jsonl"
    current.write_text("", encoding="utf-8")
    payload = json.dumps({"transcript_path": str(current), "cwd": "/Users/me/Developer/myproj"})
    monkeypatch.setattr("sys.stdin", _FakeStdin(payload))

    assert mod.main() == 0
    out = json.loads(capsys.readouterr().out)
    assert out["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert "wire up the new endpoint" in out["hookSpecificOutput"]["additionalContext"]


def test_main_with_empty_stdin_is_silent(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.stdin", _FakeStdin(""))
    assert mod.main() == 0
    assert capsys.readouterr().out == ""


class _FakeStdin:
    def __init__(self, data: str) -> None:
        self._data = data

    def read(self) -> str:
        return self._data
