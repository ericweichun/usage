# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

from typing import Any

from ui import html_report


def _diagnosis_payload() -> dict[str, Any]:
    return {
        "has_data": True,
        "total_waste_usd": 3.2,
        "monthly_savings_estimate_usd": 2.5,
        "total_waste_tokens": 250_000,
        "fixable_waste_tokens": 160_000,
        "total_corpus_tokens": 2_000_000,
        "waste_pct": 12.5,
        "fixable_pct": 8.0,
        "findings": [
            {
                "severity": "critical",
                "kind": "repeated_reads",
                "headline_plain": "diag_kind_repeated_reads",
                "headline_detail": "diag_kind_repeated_reads_d",
                "estimated_waste_usd": 1.2,
                "estimated_waste_tokens": 90_000,
                "items": [
                    {"label": "FinMind/SESSION.md", "n": 11, "size_bytes": 2_400_000},
                ],
            },
            {
                "severity": "critical",
                "kind": "polluter_dirs",
                "headline_plain": "diag_kind_polluter_dirs",
                "headline_detail": "diag_kind_polluter_dirs_d",
                "estimated_waste_usd": 1.6,
                "estimated_waste_tokens": 160_000,
                "items": [
                    {"label": "node_modules", "n": 7, "size_bytes": 900_000_000},
                ],
            },
            {
                "severity": "warning",
                "kind": "anomaly_session",
                "headline_plain": "diag_kind_anomaly_session",
                "headline_detail": "diag_kind_anomaly_session_d",
                "estimated_waste_usd": 0.3,
                "estimated_waste_tokens": 30_000,
                "items": [
                    {
                        "label": "abc12345",
                        "tokens": 500_000,
                        "ratio": 5.2,
                        "session_start_iso": "2026-06-08T14:00:00+08:00",
                        "project": "usage",
                    },
                ],
            },
            {
                "severity": "info",
                "kind": "noisy_bash",
                "headline_plain": "diag_kind_noisy_bash",
                "headline_detail": "diag_kind_noisy_bash_d",
                "estimated_waste_usd": 0.1,
                "estimated_waste_tokens": 11_000,
                "items": [
                    {"label": "uv run pytest -v", "n": 45_000, "size_bytes": 45_000},
                ],
            },
            {
                "severity": "info",
                "kind": "repeated_bash",
                "headline_plain": "diag_kind_repeated_bash",
                "headline_detail": "diag_kind_repeated_bash_d",
                "estimated_waste_usd": 0.1,
                "estimated_waste_tokens": 9_000,
                "items": [
                    {"label": "git status", "n": 18},
                ],
            },
        ],
        "suggested_claudeignore": "node_modules/\ndist/",
    }


def _render(diagnosis: object, lang: str = "zh-TW") -> str:
    return html_report._render_diagnosis_section({"diagnosis": diagnosis}, lang)


def test_renders_headline_cards_and_actions() -> None:
    out = _render(_diagnosis_payload())

    assert "diagnosis-section" in out
    assert "12.5%" in out
    # 五條規則各一張卡，severity 對應的左框顏色 class 都在。
    assert out.count("diag-card ") == 5
    assert out.count("diag-card diag-critical") == 2
    assert out.count("diag-card diag-warning") == 1
    assert out.count("diag-card diag-info") == 2
    # 行動列：.claudeignore 下載與「複製診斷」都要在。
    assert 'data-claudeignore="node_modules/&#10;dist/"' in out or "data-claudeignore=" in out
    assert "data-diag-copy=" in out
    # 非 polluter 的卡片要有「為什麼/可以試試」解釋；polluter 走一鍵修徽章。
    assert out.count("diag-card-explain") == 4
    assert "鬼打牆" in out


def test_copy_prompt_embeds_facts() -> None:
    out = _render(_diagnosis_payload())

    assert "FinMind/SESSION.md" in out
    assert "suggested .claudeignore:" in out
    assert "[repeated_bash]" in out


def test_empty_findings_show_positive_state() -> None:
    diagnosis = _diagnosis_payload()
    diagnosis["findings"] = []
    diagnosis["suggested_claudeignore"] = ""

    out = _render(diagnosis)

    assert "diagnosis-section" in out
    assert "用得很乾淨" in out
    assert "diag-card" not in out


def test_hidden_without_data() -> None:
    assert _render({"has_data": False}) == ""
    assert html_report._render_diagnosis_section({}, "zh-TW") == ""


def test_escapes_user_controlled_labels() -> None:
    diagnosis = _diagnosis_payload()
    diagnosis["findings"][0]["items"][0]["label"] = '<script>alert(1)</script>"x'
    diagnosis["suggested_claudeignore"] = '<img src=x onerror=alert(1)>"/'

    out = _render(diagnosis)

    assert "<script>alert(1)</script>" not in out
    assert "<img src=x" not in out
    assert "&lt;script&gt;" in out
