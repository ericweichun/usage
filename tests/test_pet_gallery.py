# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

from pytest import MonkeyPatch

import pet_gallery


def test_render_omits_stat_bars_and_keeps_pet_content(
    monkeypatch: MonkeyPatch,
) -> None:
    sample = [
        {
            "name": "Scout",
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
    monkeypatch.setattr(pet_gallery, "_load_pets", lambda: sample)

    rendered = pet_gallery.render()

    assert "Scout" in rendered
    assert "lab" in rendered
    assert " /\\_/\\\\" in rendered
    assert "( o.o )" in rendered
    assert "debug & dodge" in rendered
    assert "DEBUGGING" not in rendered
    assert "PATIENCE" not in rendered
    assert "CHAOS" not in rendered


def test_render_uses_first_frame_when_animation_frames_exist(
    monkeypatch: MonkeyPatch,
) -> None:
    sample = [
        {
            "name": "Raccoon",
            "theme": "forest",
            "blurb": "night watch",
            "art": "fallback art",
            "frames": ["( o.o )", "( -.- )"],
        }
    ]
    monkeypatch.setattr(pet_gallery, "_load_pets", lambda: sample)

    rendered = pet_gallery.render()

    assert "( o.o )" in rendered
    assert "fallback art" not in rendered
