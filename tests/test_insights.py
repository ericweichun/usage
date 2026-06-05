from __future__ import annotations

from typing import Any

from analyzer.insights import build_insights


def _payload() -> dict[str, Any]:
    return {
        "date_from": "2026-05-01",
        "date_to": "2026-05-04",
        "summary": {
            "total_tokens": 700,
            "cost_usd": 3.5,
            "sessions": 6,
            "messages": 24,
            "active_days": 3,
            "total_days": 4,
        },
        "by_agent": [
            {
                "id": "codex",
                "name": "Codex",
                "tokens": 700,
                "cost": 3.5,
                "sessions": 6,
                "messages": 24,
                "pct": 100.0,
            }
        ],
        "by_project": [
            {"project": "usage", "tokens": 490, "cost": 2.75, "sessions": 4, "pct": 70.0},
            {"project": "other", "tokens": 210, "cost": 0.75, "sessions": 2, "pct": 30.0},
        ],
        "by_model": [
            {"model": "gpt-5-codex", "tokens": 560, "cost": 2.8, "pct": 80.0},
            {"model": "gpt-5-mini", "tokens": 140, "cost": 0.7, "pct": 20.0},
        ],
        "daily_trend": [
            {"date": "2026-05-01", "tokens": 100, "cost": 0.5},
            {"date": "2026-05-02", "tokens": 100, "cost": 0.5},
            {"date": "2026-05-03", "tokens": 100, "cost": 0.5},
            {"date": "2026-05-04", "tokens": 400, "cost": 2.0},
        ],
        "top_sessions": [
            {
                "start_time": "2026-05-04 10:00",
                "project": "usage",
                "model": "gpt-5-codex",
                "duration_min": 42.0,
                "tokens": 400,
                "cost": 2.0,
            }
        ],
        "subscriptions": [{"agent": "Codex", "plan": "ChatGPT Plus", "since": "2026-03-23"}],
        "persona": None,
    }


def test_build_insights_emits_all_component_types() -> None:
    insights = build_insights(_payload())

    assert [component["type"] for component in insights] == [
        "priority_summary",
        "subscription_value",
        "spike_explainer",
        "next_actions",
    ]


def test_build_insights_golden_output_is_deterministic() -> None:
    assert build_insights(_payload()) == [
        {
            "type": "priority_summary",
            "items": [
                {
                    "key": "insights_priority_top_project",
                    "project": "usage",
                    "tokens": 490,
                    "cost_usd": 2.75,
                    "pct": 70.0,
                    "sessions": 4,
                },
                {
                    "key": "insights_priority_spike_day",
                    "date": "2026-05-04",
                    "tokens": 400,
                    "mean_tokens": 175.0,
                    "mean_multiplier": 2.29,
                },
                {
                    "key": "insights_priority_top_model",
                    "model": "gpt-5-codex",
                    "tokens": 560,
                    "pct": 80.0,
                    "cost_usd": 2.8,
                },
            ],
        },
        {
            "type": "subscription_value",
            "key": "insights_subscription_medium",
            "active_days": 3,
            "total_days": 4,
            "active_ratio": 0.75,
            "sessions": 6,
            "subscription_count": 1,
        },
        {
            "type": "spike_explainer",
            "date": "2026-05-04",
            "tokens": 400,
            "cost_usd": 2.0,
            "mean_tokens": 175.0,
            "stdev_tokens": 129.9,
            "mean_multiplier": 2.29,
        },
        {
            "type": "next_actions",
            "actions": [
                {
                    "key": "insights_action_smooth_spikes",
                    "date": "2026-05-04",
                    "tokens": 400,
                    "mean_multiplier": 2.29,
                },
                {
                    "key": "insights_action_split_heavy_project",
                    "project": "usage",
                    "pct": 70.0,
                    "tokens": 490,
                },
                {
                    "key": "insights_action_review_model_mix",
                    "model": "gpt-5-codex",
                    "pct": 80.0,
                    "tokens": 560,
                },
            ],
        },
    ]


def test_priority_summary_skips_when_usage_data_is_missing() -> None:
    payload = _payload()
    payload["summary"] = {
        "total_tokens": 0,
        "cost_usd": 0.0,
        "sessions": 0,
        "messages": 0,
        "active_days": 0,
        "total_days": 4,
    }
    payload["by_project"] = []
    payload["by_model"] = []
    payload["daily_trend"] = []

    assert not any(component["type"] == "priority_summary" for component in build_insights(payload))


def test_subscription_value_skips_without_subscriptions() -> None:
    payload = _payload()
    payload["subscriptions"] = []

    assert not any(
        component["type"] == "subscription_value" for component in build_insights(payload)
    )


def test_spike_explainer_skips_without_clear_spike() -> None:
    payload = _payload()
    payload["daily_trend"] = [
        {"date": "2026-05-01", "tokens": 100, "cost": 0.5},
        {"date": "2026-05-02", "tokens": 110, "cost": 0.5},
        {"date": "2026-05-03", "tokens": 105, "cost": 0.5},
        {"date": "2026-05-04", "tokens": 100, "cost": 0.5},
    ]

    assert not any(component["type"] == "spike_explainer" for component in build_insights(payload))


def test_next_actions_skips_without_actionable_signals() -> None:
    payload = _payload()
    payload["by_project"] = [
        {"project": "usage", "tokens": 350, "cost": 1.75, "sessions": 3, "pct": 50.0},
        {"project": "other", "tokens": 350, "cost": 1.75, "sessions": 3, "pct": 50.0},
    ]
    payload["by_model"] = [
        {"model": "gpt-5-codex", "tokens": 350, "cost": 1.75, "pct": 50.0},
        {"model": "gpt-5-mini", "tokens": 350, "cost": 1.75, "pct": 50.0},
    ]
    payload["daily_trend"] = [
        {"date": "2026-05-01", "tokens": 100, "cost": 0.5},
        {"date": "2026-05-02", "tokens": 110, "cost": 0.5},
        {"date": "2026-05-03", "tokens": 105, "cost": 0.5},
        {"date": "2026-05-04", "tokens": 100, "cost": 0.5},
    ]

    assert not any(component["type"] == "next_actions" for component in build_insights(payload))
