#!/usr/bin/env python3
"""usage SessionStart hook — inject "where you left off" into a new Claude Code session.

This is the "Project Butler" feature. Claude Code runs this on SessionStart (matcher
``startup|clear``) and pipes the session JSON on stdin; the script locates the project's
*previous* session log, pulls the user's last request, the commits made, and any pending
todos, and emits a ready-to-act resume prompt via ``hookSpecificOutput.additionalContext``.

**Stdlib-only and 3.9-safe** — same constraint as ``usage_statusline.py``: it may run
under macOS's bundled ``/usr/bin/python3`` (3.9), so no third-party imports, no
``datetime.UTC``, no runtime ``X | Y`` types. The session-log parse is self-contained here
(no app imports), so the hook stays loadable under the bundled interpreter.

When there's no fresh progress to hand over (brand-new project, the previous session
did nothing extractable, or it's older than the cutoff) the butler still checks in with
a short greeting rather than going silent.

The prompt wording stays single-sourced: ``setup_hook`` writes ``report_rw_prompt`` /
``report_rw_none`` / ``report_rw_inject_lead`` / ``report_rw_empty`` from ``i18n.json`` to
a sidecar that this script reads. If the sidecar is missing it falls back to embedded
templates for the detected language. The script never raises into the session — any
failure exits 0 with no output.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Mapping
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

__version__ = "1.2"

PROMPT_SIDECAR = Path(os.path.expanduser("~/.claude/usage-resume-prompt.json"))

# Only a heredoc that feeds git's commit message — `-F -` / `--file -` or `-m "$(cat`.
# Anchoring on these keeps an unrelated heredoc in the same command (e.g. a python
# `<<PYEOF` script whose first line is `import ...`) from being mistaken for a title.
_COMMIT_HEREDOC = re.compile(
    r"""(?:-F\s*-?|--file[=\s]\s*-?|\$\(\s*cat)\s*<<-?\s*['"]?\w+['"]?\s*\n(.+?)\n""", re.S
)
_COMMIT_INLINE = re.compile(r"""-m\s+["']([^"'\n]{4,90})""")
_MAX_AGE_DAYS = 30
_MAX_COMMITS = 3
_MAX_TODOS = 5
_MAX_REQUEST_CHARS = 280
_MIN_SUBSTANTIVE_CHARS = 7
_IMAGE_MARKER = re.compile(r"\[Image(?:\s+#[0-9]+)?\]", re.I)

_DEFAULT_PROMPT = (
    'Last time I was working on the "{project}" project (last active {when}).\n'
    "• What I was trying to do: {last_request}\n"
    "• Done: {commits}\n• To do: {todos}\n\n"
    "Please reconstruct the context first, then give me the concrete next step to take."
)
_DEFAULT_NONE = "(none recorded)"
_DEFAULT_EMPTY = (
    "(At the very start of your first reply in this session, say one line: "
    '"🐾 Your project butler is on duty. No progress to report for this project yet.", '
    "then respond normally.)"
)
_DEFAULT_TEMPLATES = {
    "en": {
        "prompt": _DEFAULT_PROMPT,
        "none": _DEFAULT_NONE,
        "lead": (
            '(At the very start of your first reply in this session, lead with one line: '
            '"🐾 Your project butler is on duty and has loaded your last progress:", then '
            "surface the points below — what you were doing / done / to-do — as a short "
            "bullet list, then respond normally.)\n\n"
        ),
        "empty": _DEFAULT_EMPTY,
    },
    "zh-TW": {
        "prompt": (
            "我上次在「{project}」專案工作（最後活動 {when}）。\n"
            "• 上次想做的：{last_request}\n"
            "• 已完成：{commits}\n• 待辦：{todos}\n\n"
            "請先重建上次的脈絡，再直接給我接下來該做的具體下一步。"
        ),
        "none": "（未記錄）",
        "lead": (
            "（請在你這次對話的第一則回覆最前面，先說一行"
            "「🐾 專屬專案管家已上線，並已帶入上次進度：」，接著用簡短條列把下面的"
            "上次想做的／已完成／待辦攤給我看，再正常回應。）\n\n"
        ),
        "empty": (
            "（請在你這次對話的第一則回覆最前面，說一行「🐾 專屬專案管家已上線。"
            "此專案目前沒有需要報告的進度。」，再正常回應。）"
        ),
    },
    "zh-CN": {
        "prompt": (
            "我上次在「{project}」项目工作（最后活动 {when}）。\n"
            "• 上次想做的：{last_request}\n"
            "• 已完成：{commits}\n• 待办：{todos}\n\n"
            "请先重建上次的脉络，再直接给我接下来该做的具体下一步。"
        ),
        "none": "（未记录）",
        "lead": (
            "（请在你这次对话的第一则回复最前面，先说一行"
            "「🐾 专属项目管家已上线，并已带入上次进度：」，接着用简短条列把下面的"
            "上次想做的／已完成／待办摊给我看，再正常回应。）\n\n"
        ),
        "empty": (
            "（请在你这次对话的第一则回复最前面，说一行「🐾 专属项目管家已上线。"
            "此项目目前没有需要报告的进度。」，再正常回应。）"
        ),
    },
    "ja": {
        "prompt": (
            "前回は「{project}」プロジェクトで作業していました（最終アクティブ: {when}）。\n"
            "• やろうとしていたこと: {last_request}\n"
            "• 完了: {commits}\n• 未完了: {todos}\n\n"
            "まず前回の文脈を再構築し、次に取り組むべき具体的なステップを教えてください。"
        ),
        "none": "（記録なし）",
        "lead": (
            "（このセッションの最初の返信の冒頭に、まず一行「🐾 専属プロジェクト執事が待機中です。"
            "前回の進捗を引き継ぎました：」と述べ、続けて下記のやろうとしていたこと／完了／未完了を"
            "短い箇条書きで提示してから、通常どおり応答してください。）\n\n"
        ),
        "empty": (
            "（このセッションの最初の返信の冒頭に、一行「🐾 専属プロジェクト執事が待機中です。"
            "このプロジェクトに報告すべき進捗はまだありません。」と述べてから、通常どおり応答してください。）"
        ),
    },
    "ko": {
        "prompt": (
            '지난번에 "{project}" 프로젝트에서 작업했습니다 (마지막 활동: {when}).\n'
            "• 하려던 일: {last_request}\n"
            "• 완료: {commits}\n• 할 일: {todos}\n\n"
            "먼저 지난 맥락을 재구성한 뒤, 이어서 해야 할 구체적인 다음 단계를 알려주세요."
        ),
        "none": "(기록 없음)",
        "lead": (
            '(이 세션의 첫 답변 맨 앞에 먼저 한 줄 "🐾 전담 프로젝트 집사가 대기 '
            '중이며 지난 진행 상황을 불러왔습니다:"라고 말한 뒤, 아래의 하려던 일／완료／할 일을 '
            "짧은 목록으로 보여주고 평소대로 응답하세요.)\n\n"
        ),
        "empty": (
            '(이 세션의 첫 답변 맨 앞에 한 줄 "🐾 전담 프로젝트 집사가 대기 중입니다. '
            '이 프로젝트에 보고할 진행 상황이 아직 없습니다."라고 말한 뒤 평소대로 응답하세요.)'
        ),
    },
}


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(payload, dict):
        return 0
    try:
        prompt = _build_prompt(payload)
    except Exception:
        return 0
    if not prompt:
        return 0
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": prompt,
        }
    }
    print(json.dumps(output, ensure_ascii=False))
    return 0


def _build_prompt(payload: dict[str, Any]) -> str:
    transcript = payload.get("transcript_path")
    cwd = payload.get("cwd")
    if not isinstance(transcript, str) or not transcript:
        return ""
    project_dir = Path(transcript).parent
    if not project_dir.is_dir():
        return ""

    lead, template, none_label, empty = _load_template(_detect_lang())
    project = _project_from_cwd(cwd) if isinstance(cwd, str) and cwd else project_dir.name
    report = _build_report(project_dir, Path(transcript).name, project, lead, template, none_label)
    # The butler always checks in: when there's no fresh progress to hand over, it
    # greets instead of going silent.
    return report or empty


def _build_report(
    project_dir: Path,
    current_name: str,
    project: str,
    lead: str,
    template: str,
    none_label: str,
) -> str:
    """The "I loaded your last progress" prompt, or "" when there's nothing fresh to report."""
    parsed = None
    for candidate in _other_jsonls_by_mtime(project_dir, exclude=current_name):
        parsed = _parse_session(candidate)
        if parsed is not None:
            break
    if parsed is None:
        return ""
    last_active, last_request, commits, todos = parsed
    if last_active < _cutoff():
        return ""
    request_text = last_request or none_label
    commits_text = " · ".join(commits[:_MAX_COMMITS]) or none_label
    todos_text = " · ".join(todos[:_MAX_TODOS]) or none_label
    return lead + template.format(
        project=project,
        when=_format_time(last_active),
        last_request=request_text,
        commits=commits_text,
        todos=todos_text,
    )


def _cutoff() -> datetime:
    return datetime.now().astimezone() - timedelta(days=_MAX_AGE_DAYS)


def _other_jsonls_by_mtime(project_dir: Path, exclude: str) -> list[Path]:
    """Other session logs in the project, newest first.

    Newest-first so the caller can skip a freshly-written but empty/corrupt log and
    still fall back to the previous session that actually has progress to report.
    """
    candidates: list[tuple[float, Path]] = []
    for jsonl in project_dir.glob("*.jsonl"):
        if jsonl.name == exclude:
            continue
        try:
            mtime = jsonl.stat().st_mtime
        except OSError:
            continue
        candidates.append((mtime, jsonl))
    candidates.sort(key=lambda item: item[0], reverse=True)
    return [path for _, path in candidates]


def _parse_session(path: Path) -> tuple[datetime, str, list[str], list[str]] | None:
    """Return (last_active, last_request, commits, todos) for the previous session.

    ``last_request`` is the first substantive user request in the session: the task that
    started the work is more useful than a trailing reaction, screenshot marker, or
    interruption note. ``todos`` are the pending items from the latest TodoWrite, if the
    session used one.
    """
    last_request = ""
    commits: list[str] = []
    todos: list[str] = []
    last_ts: datetime | None = None

    try:
        with path.open(encoding="utf-8") as file:
            for raw_line in file:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(data, dict):
                    continue

                timestamp = _parse_timestamp(data.get("timestamp"))
                if timestamp is not None and (last_ts is None or timestamp > last_ts):
                    last_ts = timestamp

                entry_type = data.get("type")
                if entry_type == "last-prompt":
                    text = _clean_request(data.get("lastPrompt"))
                    if text and not last_request:
                        last_request = text
                    continue
                if entry_type == "user":
                    text = _user_request_text(data.get("message"))
                    if text and not last_request:
                        last_request = text
                    continue
                if entry_type != "assistant":
                    continue
                message = data.get("message")
                if not isinstance(message, dict):
                    continue
                content = message.get("content")
                if not isinstance(content, list):
                    continue
                _collect_tools(content, commits, todos)
    except OSError:
        return None

    if last_ts is None or not (last_request or commits or todos):
        return None
    return last_ts, last_request, commits, todos


def _user_request_text(message: object) -> str:
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return _clean_request(content)
    if isinstance(content, list):
        parts = [
            part.get("text")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        return _clean_request(" ".join(p for p in parts if isinstance(p, str) and p.strip()))
    return ""


def _clean_request(value: object) -> str:
    if not isinstance(value, str):
        return ""
    text = " ".join(value.split())
    # Skip the interruption marker Claude Code writes as a user turn — it is noise,
    # not a request.
    if not text or text.startswith("[Request interrupted"):
        return ""
    starts_with_image = text.startswith("[Image")
    text = _IMAGE_MARKER.sub("", text).strip()
    if not text:
        return ""
    if starts_with_image and _substantive_len(text) < _MIN_SUBSTANTIVE_CHARS:
        return ""
    if _substantive_len(text) < _MIN_SUBSTANTIVE_CHARS and not _has_structural_signal(text):
        return ""
    if len(text) > _MAX_REQUEST_CHARS:
        text = text[: _MAX_REQUEST_CHARS - 1].rstrip() + "…"
    return text


def _substantive_len(text: str) -> int:
    return sum(1 for char in text if char.isalnum())


def _has_structural_signal(text: str) -> bool:
    return any(marker in text for marker in ("/", "\\", ".", "_", "-", "#", ":", "`", "(", ")"))


def _pending_todos(items: list[Any]) -> list[str]:
    result: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("status") not in ("pending", "in_progress"):
            continue
        text = item.get("content")
        if isinstance(text, str) and text.strip():
            result.append(_clean_request(text))
    return [t for t in result if t]


def _collect_tools(content: list[Any], commits: list[str], todos: list[str]) -> None:
    for part in content:
        if not isinstance(part, dict) or part.get("type") != "tool_use":
            continue
        name = part.get("name")
        raw_input = part.get("input")
        if not isinstance(raw_input, dict):
            continue
        if name == "TodoWrite":
            items = raw_input.get("todos")
            if isinstance(items, list):
                pending = _pending_todos(items)
                if pending:
                    todos[:] = pending  # latest TodoWrite wins — it is the current state
        elif name == "Bash":
            command = raw_input.get("command")
            if isinstance(command, str) and "git commit" in command:
                title = _extract_commit_title(command)
                if title and title not in commits:
                    commits.append(title)


def _extract_commit_title(command: str) -> str:
    heredoc = _COMMIT_HEREDOC.search(command)
    if heredoc:
        return heredoc.group(1).strip()
    inline = _COMMIT_INLINE.search(command)
    if inline:
        return inline.group(1).strip()
    return ""


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    # A naive timestamp (no offset) can't be compared against the aware _cutoff();
    # assume local time so the comparison stays type-safe.
    return parsed if parsed.tzinfo is not None else parsed.astimezone()


def _format_time(parsed: datetime) -> str:
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone()
    return f"{parsed.month}/{parsed.day} {parsed.hour:02d}:{parsed.minute:02d}"


def _project_from_cwd(cwd: str) -> str:
    home = os.path.expanduser("~")
    rel = cwd[len(home):].strip(os.sep) if cwd.startswith(home) else cwd.strip(os.sep)
    parts = rel.split(os.sep)
    return parts[-1] if parts and parts[-1] else (rel or "unknown")


def _detect_lang() -> str:
    for key in ("USAGE_LANG", "TT_LANG", "LANG"):
        value = os.environ.get(key, "").strip()
        if value:
            return _normalize_lang(value)
    return "en"


def _normalize_lang(code: str) -> str:
    normalized = code.split(".")[0].strip().lower().replace("_", "-")
    if normalized in {"zh-tw", "zh-hk", "zh-hant"} or normalized.startswith(("zh-tw-", "zh-hant")):
        return "zh-TW"
    if normalized in {"zh-cn", "zh-sg", "zh-hans", "zh"} or normalized.startswith(
        ("zh-cn-", "zh-hans")
    ):
        return "zh-CN"
    if normalized.startswith("ja"):
        return "ja"
    if normalized.startswith("ko"):
        return "ko"
    return "en"


def _load_template(lang: str) -> tuple[str, str, str, str]:
    """Return (lead, prompt, none, empty). ``lead`` is a short instruction prepended to
    the injected context so Claude's first reply visibly acknowledges it loaded the
    progress — the only way a SessionStart hook can surface itself to the user.
    ``empty`` is the standalone greeting shown when there's no fresh progress to report."""
    fallback = _template_from_entry(_DEFAULT_TEMPLATES.get(lang) or _DEFAULT_TEMPLATES["en"])
    try:
        bundle = json.loads(PROMPT_SIDECAR.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return fallback
    if not isinstance(bundle, dict):
        return fallback
    entry = bundle.get(lang) or bundle.get("en")
    if not isinstance(entry, dict):
        return fallback
    return _template_from_entry(entry, fallback)


def _template_from_entry(
    entry: Mapping[str, object],
    fallback: tuple[str, str, str, str] | None = None,
) -> tuple[str, str, str, str]:
    if fallback is None:
        fallback = ("", _DEFAULT_PROMPT, _DEFAULT_NONE, _DEFAULT_EMPTY)
    lead = entry.get("lead")
    prompt = entry.get("prompt")
    none_label = entry.get("none")
    empty = entry.get("empty")
    return (
        lead if isinstance(lead, str) else fallback[0],
        prompt if isinstance(prompt, str) and prompt else fallback[1],
        none_label if isinstance(none_label, str) and none_label else fallback[2],
        empty if isinstance(empty, str) and empty else fallback[3],
    )


if __name__ == "__main__":
    sys.exit(main())
