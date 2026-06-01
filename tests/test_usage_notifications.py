from __future__ import annotations

from usage_notifications import QuotaNotifier


def test_threshold_warn_only_triggers_once_until_reset() -> None:
    notifier = QuotaNotifier()

    assert notifier.update({"claude_session": (89.0, True)}) == []
    events = notifier.update({"claude_session": (90.0, True)})
    assert [(event.kind, event.channel, event.threshold) for event in events] == [
        ("warn", "claude_session", 90.0)
    ]

    assert notifier.update({"claude_session": (95.0, True)}) == []
    assert notifier.update({"claude_session": (91.0, True)}) == []


def test_reset_unlocks_threshold_latch() -> None:
    notifier = QuotaNotifier()

    notifier.update({"codex_weekly": (89.0, True)})
    notifier.update({"codex_weekly": (91.0, True)})
    assert notifier.update({"codex_weekly": (20.0, True)}) == []
    events = notifier.update({"codex_weekly": (92.0, True)})

    assert [(event.kind, event.channel, event.threshold) for event in events] == [
        ("warn", "codex_weekly", 90.0)
    ]


def test_depleted_triggers_once_for_percent_or_unavailable() -> None:
    notifier = QuotaNotifier()

    events = notifier.update({"claude_weekly": (100.0, True)})
    assert [(event.kind, event.channel, event.threshold) for event in events] == [
        ("depleted", "claude_weekly", None)
    ]
    assert notifier.update({"claude_weekly": (100.0, True)}) == []

    events = notifier.update({"codex_session": (None, False)})
    assert [(event.kind, event.channel, event.threshold) for event in events] == [
        ("depleted", "codex_session", None)
    ]
    assert notifier.update({"codex_session": (None, False)}) == []


def test_restored_triggers_after_depleted_reset() -> None:
    notifier = QuotaNotifier()

    notifier.update({"claude_session": (99.0, True)})
    notifier.update({"claude_session": (100.0, True)})
    events = notifier.update({"claude_session": (5.0, True)})

    assert [(event.kind, event.channel, event.threshold) for event in events] == [
        ("restored", "claude_session", None)
    ]


def test_restored_does_not_trigger_for_non_depleted_reset() -> None:
    notifier = QuotaNotifier()

    notifier.update({"codex_session": (80.0, True)})

    assert notifier.update({"codex_session": (10.0, True)}) == []
