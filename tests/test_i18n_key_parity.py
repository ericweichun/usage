"""Key-parity test for ``i18n.json``.

The project rule is that every user-visible string lives in ``i18n.json``
under all five language sections (``zh-TW``, ``zh-CN``, ``en``, ``ja``,
``ko``). ``_t`` degrades gracefully for a missing key (English fallback,
then the raw key), so a forgotten translation never crashes — it just
silently ships English. This test makes that omission fail loudly in CI
instead.
"""

from __future__ import annotations

import json
from pathlib import Path

EXPECTED_LANGS = {"zh-TW", "zh-CN", "en", "ja", "ko"}
I18N_PATH = Path(__file__).resolve().parent.parent / "i18n.json"


def _bundle() -> dict[str, dict[str, str]]:
    data: dict[str, dict[str, str]] = json.loads(I18N_PATH.read_text(encoding="utf-8"))
    return data


def test_all_expected_languages_present() -> None:
    assert set(_bundle().keys()) == EXPECTED_LANGS


def test_every_language_has_the_same_keys() -> None:
    bundle = _bundle()
    reference = set(bundle["en"])
    mismatches = {
        lang: {
            "missing": sorted(reference - set(keys)),
            "extra": sorted(set(keys) - reference),
        }
        for lang, keys in bundle.items()
        if set(keys) != reference
    }
    assert not mismatches, f"i18n key mismatch vs en: {mismatches}"
