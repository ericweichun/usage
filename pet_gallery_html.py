# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 lollapalooza <https://github.com/aqua5230>
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from i18n import _t, packaged_resource_path

BG = "#0d0f12"
CARD = "#161b22"
BORDER = "#30363d"
TEXT = "#f0f6fc"
ACCENT = "#d97757"
DIM = "#b0aea5"
FRAME_INTERVAL_MS = 500


def _load_pets() -> list[dict[str, Any]]:
    path = packaged_resource_path("pets.json", Path(__file__).with_name("pets.json"))
    data = json.loads(path.read_text(encoding="utf-8"))
    pets = data.get("pets")
    if not isinstance(pets, list):
        raise ValueError("pets.json missing pets array")
    return [pet for pet in pets if isinstance(pet, dict)]


def _pet_frames(pet: dict[str, Any]) -> list[str]:
    frames = pet.get("frames")
    if not isinstance(frames, list):
        return []
    return [frame for frame in frames if isinstance(frame, str)]


def _display_art(pet: dict[str, Any]) -> str:
    frames = _pet_frames(pet)
    if frames:
        return frames[0]
    return str(pet.get("art", ""))


def _pet_card(pet: dict[str, Any]) -> str:
    name = html.escape(str(pet.get("name", "")))
    theme = html.escape(str(pet.get("theme", "")))
    blurb = html.escape(str(pet.get("blurb", "")))
    art = html.escape(_display_art(pet))
    frames = _pet_frames(pet)
    art_attrs = ' class="pet-art"'
    if len(frames) > 1:
        art_attrs += f" data-pet-frames='{html.escape(json.dumps(frames))}'"
    return f"""
    <article class="pet-card">
      <header class="pet-head">
        <div class="pet-name">{name}</div>
        <div class="pet-theme">{theme}</div>
      </header>
      <pre{art_attrs}>{art}</pre>
      <p class="pet-blurb">{blurb}</p>
    </article>"""


def render_html(language: str) -> str:
    title = html.escape(_t(language, "pet_gallery_title"))
    cards = "".join(_pet_card(pet) for pet in _load_pets())
    return f"""<!doctype html>
<html lang="{html.escape(language)}">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{title}</title>
    <style>
      :root {{
        color-scheme: dark;
        --bg: {BG};
        --card: {CARD};
        --border: {BORDER};
        --text: {TEXT};
        --accent: {ACCENT};
        --dim: {DIM};
      }}
      * {{
        box-sizing: border-box;
      }}
      html, body {{
        margin: 0;
        min-height: 100%;
        background: var(--bg);
        color: var(--text);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }}
      body {{
        padding: 18px;
      }}
      .shell {{
        display: flex;
        flex-direction: column;
        gap: 14px;
      }}
      .title {{
        margin: 0;
        font-size: 22px;
        font-weight: 700;
        letter-spacing: 0.02em;
      }}
      .cards {{
        display: flex;
        flex-direction: column;
        gap: 14px;
      }}
      .pet-card {{
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 16px;
        box-shadow: 0 14px 30px rgba(0, 0, 0, 0.26);
      }}
      .pet-head {{
        display: flex;
        flex-direction: column;
        gap: 4px;
        margin-bottom: 12px;
      }}
      .pet-name {{
        color: var(--accent);
        font-size: 18px;
        font-weight: 700;
      }}
      .pet-theme {{
        color: var(--dim);
        font-size: 12px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }}
      .pet-art {{
        margin: 0 0 12px;
        padding: 12px;
        overflow-x: auto;
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.04);
        border-radius: 12px;
        color: var(--text);
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 13px;
        line-height: 1.22;
        white-space: pre;
      }}
      .pet-blurb {{
        margin: 0;
        color: var(--dim);
        font-size: 13px;
        line-height: 1.5;
      }}
    </style>
  </head>
  <body>
    <main class="shell">
      <h1 class="title">{title}</h1>
      <section class="cards">{cards}</section>
    </main>
    <script>
      const FRAME_INTERVAL_MS = {FRAME_INTERVAL_MS};
      for (const artEl of document.querySelectorAll("[data-pet-frames]")) {{
        const frames = JSON.parse(artEl.dataset.petFrames || "[]");
        if (frames.length <= 1) {{
          continue;
        }}
        let frameIndex = 0;
        artEl.textContent = frames[frameIndex];
        window.setInterval(() => {{
          frameIndex = (frameIndex + 1) % frames.length;
          artEl.textContent = frames[frameIndex];
        }}, FRAME_INTERVAL_MS);
      }}
    </script>
  </body>
</html>
"""
