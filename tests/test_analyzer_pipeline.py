from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import menubar
from adapters.types import AgentInfo, UsageEntry

ROOT = Path(__file__).resolve().parents[1]


def test_all_languages_have_analyze_label() -> None:
    bundle = json.loads((ROOT / "i18n.json").read_text(encoding="utf-8"))

    assert bundle["zh-TW"]["analyze_usage"] == "報告"
    assert bundle["zh-CN"]["analyze_usage"] == "报告"
    assert bundle["en"]["analyze_usage"] == "Report"
    assert bundle["ja"]["analyze_usage"] == "レポート"
    assert bundle["ko"]["analyze_usage"] == "리포트"


def test_all_languages_have_cli_statusline_labels() -> None:
    bundle = json.loads((ROOT / "i18n.json").read_text(encoding="utf-8"))

    expected = {
        "zh-TW": ("終端", "終端", "終端 ✓"),
        "zh-CN": ("终端", "终端", "终端 ✓"),
        "en": ("Terminal", "Terminal", "Terminal ✓"),
        "ja": ("ターミナル", "ターミナル", "ターミナル ✓"),
        "ko": ("터미널", "터미널", "터미널 ✓"),
    }
    for lang, (label, disabled, enabled) in expected.items():
        table = bundle[lang]
        assert table["cli"] == label
        assert table["cli_disabled"] == disabled
        assert table["cli_enabled"] == enabled
        removed_statusline_message_keys = {
            "statusline_" + suffix for suffix in ("installed", "uninstalled")
        }
        assert removed_statusline_message_keys.isdisjoint(table)
        assert not any(key.startswith("cli_five_hour") for key in table)


def test_html_panels_expose_analyze_action() -> None:
    panels_dir = ROOT / "assets" / "panels"

    for path in panels_dir.glob("*.html"):
        html = path.read_text(encoding="utf-8")
        assert 'data-action="analyze"' in html, path.name
        assert 'data-i18n="analyze_usage"' in html, path.name
        assert 'data-action="toggle-statusline"' in html, path.name


def test_generate_analysis_report_uses_analyzer_pipeline(
    monkeypatch: Any,
) -> None:
    agents = [AgentInfo("codex", "Codex", "~/.codex", True)]
    report_data: dict[str, object] = {"summary": {"total_tokens": 123}}
    calls: dict[str, object] = {}

    def fake_build_report_data(received_agents: list[AgentInfo], period: str) -> dict[str, object]:
        calls["agents"] = received_agents
        calls["period"] = period
        return report_data

    def fake_save_and_open(received_data: dict[str, object]) -> str:
        calls["data"] = received_data
        return "~/.usage-reports/usage-report-test.html"

    monkeypatch.setattr("adapters.registry.detect_agents", lambda: agents)
    monkeypatch.setattr("analyzer.reporter.build_report_data", fake_build_report_data)
    monkeypatch.setattr("ui.html_report.save_and_open", fake_save_and_open)

    assert menubar._generate_analysis_report() == "~/.usage-reports/usage-report-test.html"
    assert calls == {"agents": agents, "period": "last30", "data": report_data}


def test_app_analyze_uses_all_time_report(monkeypatch: Any) -> None:
    calls: list[str] = []

    class InlineThread:
        def __init__(
            self,
            *,
            target: Any,
            args: tuple[Any, ...] = (),
            daemon: bool = False,
        ) -> None:
            self.target = target
            self.args = args

        def start(self) -> None:
            self.target(*self.args)

    delegate = menubar.AppDelegate.alloc().initWithMock_interval_(False, 60)
    monkeypatch.setattr("menubar.threading.Thread", InlineThread)

    def fake_generate_analysis_report(
        period: str = "last30",
        language: str | None = None,
    ) -> str:
        calls.append(period)
        return "~/.usage-reports/all.html"

    monkeypatch.setattr(
        menubar,
        "_generate_analysis_report",
        fake_generate_analysis_report,
    )
    monkeypatch.setattr(
        delegate,
        "performSelectorOnMainThread_withObject_waitUntilDone_",
        lambda *args: None,
    )

    delegate.analyzeUsage_(None)

    assert calls == ["all"]


def test_last30_report_uses_rolling_720_hours(monkeypatch: Any) -> None:
    from analyzer import reporter

    now = datetime.now(UTC)
    agent = AgentInfo("codex", "Codex", "~/.codex", True)
    inside = UsageEntry(
        timestamp=now - timedelta(hours=719),
        session_id="inside",
        message_id="inside-msg",
        request_id="",
        model="gpt",
        input_tokens=100,
        output_tokens=50,
        cache_creation_tokens=0,
        cache_read_tokens=0,
        cost_usd=None,
        project="inside",
        agent_id="codex",
    )
    outside = UsageEntry(
        timestamp=now - timedelta(hours=721),
        session_id="outside",
        message_id="outside-msg",
        request_id="",
        model="gpt",
        input_tokens=1_000,
        output_tokens=500,
        cache_creation_tokens=0,
        cache_read_tokens=0,
        cost_usd=None,
        project="outside",
        agent_id="codex",
    )

    monkeypatch.setattr(
        reporter,
        "_load_agent_entries",
        lambda received_agent, hours_back=0: [inside, outside],
    )

    data = reporter.build_report_data([agent], "last30")

    assert data["summary"]["total_tokens"] == 150
    assert data["by_project"][0]["project"] == "inside"
