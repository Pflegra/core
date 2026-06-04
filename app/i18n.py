"""
Pflegra – i18n Modul
Einfaches JSON-basiertes Übersetzungssystem.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

SUPPORTED_LANGS = ["de", "en"]
DEFAULT_LANG    = "de"
TRANSLATIONS    = {}


def _load() -> None:
    """Lädt alle Übersetzungsdateien beim Start."""
    trans_dir = Path(__file__).parent / "translations"
    for lang in SUPPORTED_LANGS:
        path = trans_dir / f"{lang}.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                TRANSLATIONS[lang] = json.load(f)
            log.info("i18n: Sprache '%s' geladen", lang)
        else:
            log.warning("i18n: Übersetzungsdatei nicht gefunden: %s", path)


def get_lang(request) -> str:
    """Ermittelt die aktive Sprache aus Cookie oder User-Settings."""
    lang = request.cookies.get("pflegra_lang", DEFAULT_LANG)
    return lang if lang in SUPPORTED_LANGS else DEFAULT_LANG


def t(key: str, lang: str = DEFAULT_LANG, **kwargs) -> str:
    """
    Übersetzt einen Schlüssel (z.B. 'common.speichern') in die Zielsprache.
    Fallback auf Deutsch, dann auf den Key selbst.
    """
    parts = key.split(".")
    trans = TRANSLATIONS.get(lang, {})
    fallback = TRANSLATIONS.get(DEFAULT_LANG, {})

    def _get(d: dict, keys: list) -> Any:
        for k in keys:
            if not isinstance(d, dict):
                return None
            d = d.get(k)
        return d

    value = _get(trans, parts) or _get(fallback, parts) or key

    if kwargs and isinstance(value, str):
        try:
            value = value.format(**kwargs)
        except (KeyError, ValueError):
            pass

    return value


def make_t(lang: str):
    """Gibt eine t()-Funktion für eine bestimmte Sprache zurück."""
    def _t(key: str, **kwargs) -> str:
        return t(key, lang, **kwargs)
    return _t


# Beim Import laden
_load()
