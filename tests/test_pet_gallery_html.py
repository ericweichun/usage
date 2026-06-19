# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

import html
import json
from pathlib import Path

from pytest import MonkeyPatch

import pet_gallery_html

ROOT = Path(__file__).resolve().parent.parent


def _pets() -> list[dict[str, object]]:
    data = json.loads((ROOT / "pets.json").read_text(encoding="utf-8"))
    return list(data["pets"])


def test_render_html_uses_localized_title() -> None:
    rendered = pet_gallery_html.render_html("ja")

    assert "<title>ペット図鑑</title>" in rendered
    assert '<h1 class="title">ペット図鑑</h1>' in rendered


def test_render_html_preserves_ascii_art_from_json() -> None:
    pets = _pets()
    rendered = pet_gallery_html.render_html("zh-TW")

    assert rendered.count('class="pet-card"') == len(pets)
    for pet in pets:
        assert html.escape(str(pet["art"])) in rendered


def test_render_html_embeds_animation_frames_and_uses_textcontent(
    monkeypatch: MonkeyPatch,
) -> None:
    frames = ["( o.o )", "( -.- )", "( O.O )"]
    sample = [
        {
            "name": "Raccoon",
            "theme": "forest",
            "blurb": "night watch",
            "art": "unused fallback",
            "frames": frames,
        },
        {
            "name": "Scout",
            "theme": "lab",
            "blurb": "static",
            "art": " /\\_/\\\\\n( o.o )",
        },
    ]
    monkeypatch.setattr(pet_gallery_html, "_load_pets", lambda: sample)

    rendered = pet_gallery_html.render_html("en")

    assert 'data-pet-frames=' in rendered
    assert html.escape(json.dumps(frames)) in rendered
    assert 'const FRAME_INTERVAL_MS = 500;' in rendered
    assert 'document.querySelectorAll("[data-pet-frames]")' in rendered
    assert 'artEl.textContent = frames[frameIndex];' in rendered
    assert "innerHTML" not in rendered
    assert rendered.count('data-pet-frames=') == 1
    assert '<pre class="pet-art"> /\\_/\\\\\n( o.o )</pre>' in rendered


def test_render_html_handles_arbitrary_pet_counts(
    monkeypatch: MonkeyPatch,
) -> None:
    sample = [
        {
            "name": "<Scout>",
            "theme": "lab",
            "blurb": "debug & dodge",
            "art": " /\\_/\\\\\n( o.o )",
            "stats": {
                "debugging": 49,
                "patience": 50,
                "chaos": 81,
                "wisdom": 0,
                "snark": 100,
            },
        }
    ]
    monkeypatch.setattr(pet_gallery_html, "_load_pets", lambda: sample)

    rendered = pet_gallery_html.render_html("en")

    assert rendered.count('class="pet-card"') == 1
    assert "&lt;Scout&gt;" in rendered
    assert "lab" in rendered
    assert html.escape(" /\\_/\\\\\n( o.o )") in rendered
    assert "debug &amp; dodge" in rendered
    assert "DEBUGGING" not in rendered
    assert "PATIENCE" not in rendered
    assert 'class="pet-stats"' not in rendered
