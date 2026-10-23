"""Shortcut labels for the current platform (Ctrl → ⌘ and Alt → ⌥ on macOS)."""

from vectra.config import IS_MAC


def acc(label):
    if not label or not IS_MAC:
        return label
    return (label.replace("Ctrl+", "⌘").replace("Alt+", "⌥").replace("Shift+", "⇧"))
