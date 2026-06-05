from __future__ import annotations

from math import sqrt
from typing import Any, cast

INSIGHT_PRIORITY_SUMMARY = "priority_summary"
INSIGHT_SUBSCRIPTION_VALUE = "subscription_value"
INSIGHT_SPIKE_EXPLAINER = "spike_explainer"
INSIGHT_NEXT_ACTIONS = "next_actions"

_SPIKE_MULTIPLIER_THRESHOLD = 1.5


def build_insights(data: dict[str, Any]) -> list[dict[str, Any]]:
    components: list[dict[str, Any]] = []
    spike = _find_spike(data.get("daily_trend"))
    subscription_value = _build_subscription_value(data)

    priority_summary = _build_priority_summary(data, spike)
    if priority_summary is not None:
        components.append(priority_summary)

    if subscription_value is not None:
        components.append(subscription_value)

    if spike is not None:
        components.append({"type": INSIGHT_SPIKE_EXPLAINER, **spike})

    next_actions = _build_next_actions(data, spike, subscription_value)
    if next_actions is not None:
        components.append(next_actions)

    return components


def _build_priority_summary(
    data: dict[str, Any],
    spike: dict[str, Any] | None,
) -> dict[str, Any] | None:
    items: list[dict[str, Any]] = []
    top_project = _first_mapping(data.get("by_project"))
    top_model = _first_mapping(data.get("by_model"))

    if top_project is not None:
        project_tokens = _int_value(top_project.get("tokens"))
        project_cost = _float_value(top_project.get("cost"))
        project_pct = _float_value(top_project.get("pct"))
        if project_tokens > 0 or project_cost > 0.0:
            items.append(
                {
                    "key": "insights_priority_top_project",
                    "project": _str_value(top_project.get("project"), "unknown"),
                    "tokens": project_tokens,
                    "cost_usd": _round_cost(project_cost),
                    "pct": _round_pct(project_pct),
                    "sessions": _int_value(top_project.get("sessions")),
                }
            )

    if spike is not None:
        items.append(
            {
                "key": "insights_priority_spike_day",
                "date": spike["date"],
                "tokens": spike["tokens"],
                "mean_tokens": spike["mean_tokens"],
                "mean_multiplier": spike["mean_multiplier"],
            }
        )

    if top_model is not None:
        model_tokens = _int_value(top_model.get("tokens"))
        model_pct = _float_value(top_model.get("pct"))
        if model_tokens > 0:
            items.append(
                {
                    "key": "insights_priority_top_model",
                    "model": _str_value(top_model.get("model"), "unknown"),
                    "tokens": model_tokens,
                    "pct": _round_pct(model_pct),
                    "cost_usd": _round_cost(_float_value(top_model.get("cost"))),
                }
            )

    summary = _mapping_value(data.get("summary"))
    if len(items) < 3 and summary is not None:
        total_cost = _float_value(summary.get("cost_usd"))
        total_tokens = _int_value(summary.get("total_tokens"))
        sessions = _int_value(summary.get("sessions"))
        if total_cost > 0.0 or total_tokens > 0:
            items.append(
                {
                    "key": "insights_priority_total_usage",
                    "cost_usd": _round_cost(total_cost),
                    "tokens": total_tokens,
                    "sessions": sessions,
                }
            )

    if not items:
        return None
    return {"type": INSIGHT_PRIORITY_SUMMARY, "items": items[:3]}


def _build_subscription_value(data: dict[str, Any]) -> dict[str, Any] | None:
    subscriptions = _list_value(data.get("subscriptions"))
    if not subscriptions:
        return None
    summary = _mapping_value(data.get("summary"))
    if summary is None:
        return None

    active_days = _int_value(summary.get("active_days"))
    total_days = _int_value(summary.get("total_days"))
    sessions = _int_value(summary.get("sessions"))
    if total_days <= 0:
        return None

    active_ratio = round(active_days / total_days, 3)
    if active_ratio >= 0.6 and sessions >= 12:
        tier_key = "insights_subscription_high"
    elif active_ratio >= 0.3 and sessions >= 5:
        tier_key = "insights_subscription_medium"
    else:
        tier_key = "insights_subscription_low"

    return {
        "type": INSIGHT_SUBSCRIPTION_VALUE,
        "key": tier_key,
        "active_days": active_days,
        "total_days": total_days,
        "active_ratio": active_ratio,
        "sessions": sessions,
        "subscription_count": len(subscriptions),
    }


def _find_spike(raw_daily: object) -> dict[str, Any] | None:
    daily = _daily_points(raw_daily)
    if len(daily) < 2:
        return None

    token_values = [point["tokens"] for point in daily]
    mean = sum(token_values) / len(token_values)
    if mean <= 0.0:
        return None

    variance = sum((tokens - mean) ** 2 for tokens in token_values) / len(token_values)
    stdev = sqrt(variance)
    threshold = mean + stdev

    candidates = [
        point
        for point in daily
        if point["tokens"] > threshold
        and point["tokens"] >= mean * _SPIKE_MULTIPLIER_THRESHOLD
    ]
    if not candidates:
        return None

    spike = sorted(candidates, key=lambda point: (-point["tokens"], point["date"]))[0]
    return {
        "date": spike["date"],
        "tokens": spike["tokens"],
        "cost_usd": _round_cost(spike["cost"]),
        "mean_tokens": round(mean, 1),
        "stdev_tokens": round(stdev, 1),
        "mean_multiplier": round(spike["tokens"] / mean, 2),
    }


def _build_next_actions(
    data: dict[str, Any],
    spike: dict[str, Any] | None,
    subscription_value: dict[str, Any] | None,
) -> dict[str, Any] | None:
    actions: list[dict[str, Any]] = []

    if spike is not None:
        actions.append(
            {
                "key": "insights_action_smooth_spikes",
                "date": spike["date"],
                "tokens": spike["tokens"],
                "mean_multiplier": spike["mean_multiplier"],
            }
        )

    top_project = _first_mapping(data.get("by_project"))
    if top_project is not None:
        project_pct = _float_value(top_project.get("pct"))
        if project_pct >= 60.0:
            actions.append(
                {
                    "key": "insights_action_split_heavy_project",
                    "project": _str_value(top_project.get("project"), "unknown"),
                    "pct": _round_pct(project_pct),
                    "tokens": _int_value(top_project.get("tokens")),
                }
            )

    top_model = _first_mapping(data.get("by_model"))
    if top_model is not None:
        model_pct = _float_value(top_model.get("pct"))
        if model_pct >= 70.0:
            actions.append(
                {
                    "key": "insights_action_review_model_mix",
                    "model": _str_value(top_model.get("model"), "unknown"),
                    "pct": _round_pct(model_pct),
                    "tokens": _int_value(top_model.get("tokens")),
                }
            )

    if subscription_value is not None and subscription_value["key"] == "insights_subscription_low":
        actions.append(
            {
                "key": "insights_action_batch_sessions",
                "active_ratio": subscription_value["active_ratio"],
                "sessions": subscription_value["sessions"],
            }
        )

    if not actions:
        return None
    return {"type": INSIGHT_NEXT_ACTIONS, "actions": actions[:3]}


def _daily_points(raw_daily: object) -> list[dict[str, Any]]:
    daily = _list_value(raw_daily)
    points: list[dict[str, Any]] = []
    for raw_point in daily:
        point = _mapping_value(raw_point)
        if point is None:
            continue
        date = _str_value(point.get("date"), "")
        tokens = _int_value(point.get("tokens"))
        if not date or tokens < 0:
            continue
        points.append(
            {
                "date": date,
                "tokens": tokens,
                "cost": _float_value(point.get("cost")),
            }
        )
    return points


def _first_mapping(value: object) -> dict[str, Any] | None:
    items = _list_value(value)
    if not items:
        return None
    return _mapping_value(items[0])


def _mapping_value(value: object) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return cast(dict[str, Any], value)
    return None


def _list_value(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    return []


def _str_value(value: object, default: str) -> str:
    if isinstance(value, str):
        return value
    return default


def _int_value(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def _float_value(value: object) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, int | float):
        return float(value)
    return 0.0


def _round_cost(value: float) -> float:
    return round(value, 4)


def _round_pct(value: float) -> float:
    return round(value, 1)
