from __future__ import annotations

import json
from pathlib import Path
from types import TracebackType
from typing import Any, Self

import pytest

from analyzer import cost


def test_load_pricing_reads_utf8_cache(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cache_path = tmp_path / "pricing_cache.json"
    cache_path.write_text(
        json.dumps({"模型¬": {"input_cost_per_token": 1.0}}, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(cost, "CACHE_PATH", cache_path)
    monkeypatch.setattr(cost, "LEGACY_CACHE_PATH", tmp_path / "missing.json")

    assert cost._load_pricing() == {"模型¬": {"input_cost_per_token": 1.0}}


def test_fetch_and_cache_writes_utf8(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cache_path = tmp_path / ".usage" / "pricing_cache.json"
    monkeypatch.setattr(cost, "CACHE_PATH", cache_path)

    class FakeResponse:
        def __enter__(self) -> Self:
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            traceback: TracebackType | None,
        ) -> None:
            _ = exc_type, exc, traceback
            return None

        def read(self) -> bytes:
            return json.dumps({"模型¬": {"input_cost_per_token": 1.0}}).encode("utf-8")

    def fake_urlopen(*args: Any, **kwargs: Any) -> FakeResponse:
        _ = args, kwargs
        return FakeResponse()

    monkeypatch.setattr(cost.urllib.request, "urlopen", fake_urlopen)

    assert cost._fetch_and_cache() == {"模型¬": {"input_cost_per_token": 1.0}}
    assert "模型¬" in cache_path.read_text(encoding="utf-8")
