"""Tiny persisted user preferences (~/.vectra/settings.json).

Failures are silent: preferences are a convenience, never a reason to crash.
"""

import json
import os

_PATH = os.path.join(os.path.expanduser("~"), ".vectra", "settings.json")
_cache = None


def _load():
    global _cache
    if _cache is None:
        try:
            with open(_PATH, encoding="utf-8") as fh:
                data = json.load(fh)
            _cache = data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            _cache = {}
    return _cache


def get(key, default=None):
    return _load().get(key, default)


def set(key, value):  # noqa: A001 - mirrors dict API
    data = _load()
    data[key] = value
    try:
        os.makedirs(os.path.dirname(_PATH), exist_ok=True)
        with open(_PATH, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1)
    except OSError:
        pass
