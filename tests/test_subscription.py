from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

import subscription


def _make_id_token(auth_claims: dict[str, str]) -> str:
    payload = json.dumps({"https://api.openai.com/auth": auth_claims}).encode()
    body = base64.urlsafe_b64encode(payload).rstrip(b"=").decode()
    return f"header.{body}.signature"


def test_claude_subscription(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg = tmp_path / ".claude.json"
    cfg.write_text(json.dumps({
        "oauthAccount": {
            "organizationType": "claude_pro",
            "subscriptionCreatedAt": "2026-04-12T03:29:57.721002Z",
            "emailAddress": "secret@example.com",
        }
    }))
    monkeypatch.setattr(subscription, "CLAUDE_CONFIG", cfg)
    sub = subscription._load_claude_subscription()
    assert sub == {"agent": "Claude Code", "plan": "Claude Pro", "since": "2026-04-12"}
    # never leak private fields
    assert "secret@example.com" not in json.dumps(sub)


def test_claude_unknown_plan_is_humanised(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg = tmp_path / ".claude.json"
    cfg.write_text(json.dumps({"oauthAccount": {"organizationType": "claude_max_5x"}}))
    monkeypatch.setattr(subscription, "CLAUDE_CONFIG", cfg)
    sub = subscription._load_claude_subscription()
    assert sub is not None
    plan = sub["plan"]
    assert plan is not None and plan.startswith("Claude")
    assert sub["since"] is None


def test_codex_subscription(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    auth = tmp_path / "auth.json"
    auth.write_text(json.dumps({
        "auth_mode": "chatgpt",
        "tokens": {"id_token": _make_id_token({
            "chatgpt_plan_type": "plus",
            "chatgpt_subscription_active_start": "2026-03-23T13:23:07+00:00",
        })},
    }))
    monkeypatch.setattr(subscription, "CODEX_AUTH", auth)
    sub = subscription._load_codex_subscription()
    assert sub == {"agent": "Codex", "plan": "ChatGPT Plus", "since": "2026-03-23"}


def test_codex_api_key_mode_no_sub(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    auth = tmp_path / "auth.json"
    auth.write_text(json.dumps({"auth_mode": "apikey"}))
    monkeypatch.setattr(subscription, "CODEX_AUTH", auth)
    assert subscription._load_codex_subscription() is None


def test_missing_files_return_empty(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(subscription, "CLAUDE_CONFIG", tmp_path / "nope.json")
    monkeypatch.setattr(subscription, "CODEX_AUTH", tmp_path / "nope2.json")
    assert subscription.load_subscriptions() == []


def test_load_subscriptions_combines_both(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg = tmp_path / ".claude.json"
    cfg.write_text(json.dumps({"oauthAccount": {"organizationType": "claude_pro"}}))
    auth = tmp_path / "auth.json"
    auth.write_text(json.dumps({
        "auth_mode": "chatgpt",
        "tokens": {"id_token": _make_id_token({"chatgpt_plan_type": "pro"})},
    }))
    monkeypatch.setattr(subscription, "CLAUDE_CONFIG", cfg)
    monkeypatch.setattr(subscription, "CODEX_AUTH", auth)
    subs = subscription.load_subscriptions()
    assert [s["agent"] for s in subs] == ["Claude Code", "Codex"]
    assert subs[1]["plan"] == "ChatGPT Pro"
