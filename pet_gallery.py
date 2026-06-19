# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

from rich.console import Console, Group
from rich.text import Text

from i18n import packaged_resource_path

TEXT = "#faf9f5"
DIM = "#b0aea5"
ACCENT = "#d97757"


def _load_pets() -> list[dict[str, Any]]:
    path = packaged_resource_path("pets.json", Path(__file__).with_name("pets.json"))
    data = json.loads(path.read_text(encoding="utf-8"))
    pets = data.get("pets")
    if not isinstance(pets, list):
        raise ValueError("pets.json missing pets array")
    return [pet for pet in pets if isinstance(pet, dict)]


def _display_art(pet: dict[str, Any]) -> str:
    frames = pet.get("frames")
    if isinstance(frames, list):
        for frame in frames:
            if isinstance(frame, str):
                return frame
    return str(pet.get("art", ""))


def _pet_block(pet: dict[str, Any]) -> Group:
    name = str(pet.get("name", ""))
    theme = str(pet.get("theme", ""))
    blurb = str(pet.get("blurb", ""))
    art = _display_art(pet)
    lines: list[Text] = [
        Text.assemble(
            (name, f"bold {ACCENT}"),
            ("  ", ""),
            (theme, DIM),
        ),
        Text(art, style=TEXT),
        Text(blurb, style=DIM),
    ]
    return Group(*lines)


def _console_width(pets: list[dict[str, Any]]) -> int:
    art_width = 0
    title_width = 0
    blurb_width = 0
    for pet in pets:
        art = _display_art(pet)
        art_width = max(art_width, max((len(line) for line in art.splitlines()), default=0))
        title_width = max(
            title_width,
            len(str(pet.get("name", ""))) + 2 + len(str(pet.get("theme", ""))),
        )
        blurb_width = max(blurb_width, len(str(pet.get("blurb", ""))))
    return max(48, art_width, title_width, blurb_width) + 2


def render() -> str:
    pets = _load_pets()
    buffer = io.StringIO()
    console = Console(
        file=buffer,
        record=True,
        force_terminal=True,
        color_system="truecolor",
        width=_console_width(pets),
    )
    if not pets:
        console.print(Text("No pets found.", style=DIM))
        return console.export_text(styles=True)

    for index, pet in enumerate(pets):
        console.print(_pet_block(pet))
        if index < len(pets) - 1:
            console.print()
    return console.export_text(styles=True)


def main() -> None:
    print(render(), end="")


if __name__ == "__main__":
    main()
