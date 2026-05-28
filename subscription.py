"""Read the locally-stored subscription plan + start date for each agent.

Everything here is read-only and stays on disk — we only pull the plan name and
the subscription start date out of the OAuth account files that Claude Code and
Codex already keep. Tokens, emails and account IDs are never read or returned.
"""
from __future__ import annotations

import base64
import binascii
import json
from pathlib import Path
from typing import Any

CLAUDE_CONFIG = Path.home() / ".claude.json"
CODEX_AUTH = Path.home() / ".codex" / "auth.json"

_CLAUDE_PLAN_NAMES = {
    "claude_pro": "Claude Pro",
    "claude_max": "Claude Max",
    "claude_team": "Claude Team",
    "claude_enterprise": "Claude Enterprise",
}


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) < 2:
        return {}
    payload = parts[1]
    payload += "=" * (-len(payload) % 4)
    try:
        claims: dict[str, Any] = json.loads(base64.urlsafe_b64decode(payload))
        return claims
    except (binascii.Error, ValueError):
        return {}


def _load_claude_subscription() -> dict[str, str | None] | None:
    try:
        data = json.loads(CLAUDE_CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    account = data.get("oauthAccount") or {}
    org_type = account.get("organizationType")
    since = account.get("subscriptionCreatedAt")
    if not org_type and not since:
        return None
    plan = _CLAUDE_PLAN_NAMES.get(org_type or "")
    if not plan:
        plan = (org_type or "Claude").replace("claude_", "Claude ").replace("_", " ").title()
    return {"agent": "Claude Code", "plan": plan, "since": since[:10] if since else None}


def _load_codex_subscription() -> dict[str, str | None] | None:
    try:
        data = json.loads(CODEX_AUTH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if data.get("auth_mode") != "chatgpt":
        return None
    claims = _decode_jwt_payload(data.get("tokens", {}).get("id_token", ""))
    auth = claims.get("https://api.openai.com/auth", {})
    plan_type = auth.get("chatgpt_plan_type")
    since = auth.get("chatgpt_subscription_active_start")
    if not plan_type and not since:
        return None
    plan = f"ChatGPT {plan_type.title()}" if plan_type else "ChatGPT"
    return {"agent": "Codex", "plan": plan, "since": since[:10] if since else None}


def load_subscriptions() -> list[dict[str, str | None]]:
    """Return ``[{agent, plan, since}]`` for whichever agents we can detect."""
    subs: list[dict[str, str | None]] = []
    for loader in (_load_claude_subscription, _load_codex_subscription):
        sub = loader()
        if sub:
            subs.append(sub)
    return subs
