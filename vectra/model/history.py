"""Undo / redo stacks of document snapshots.

Repeated edits with the same ``key`` inside a short window (e.g. nudging with
arrow keys or dragging a slider) collapse into a single undo step.
"""

import time

from vectra.config import UNDO_COALESCE_SECONDS, UNDO_LIMIT


class History:
    def __init__(self, limit=UNDO_LIMIT, window=UNDO_COALESCE_SECONDS, clock=time.time):
        self.limit = limit
        self.window = window
        self.clock = clock
        self.undo_stack, self.redo_stack = [], []
        self._last_key, self._last_t = None, 0.0

    def record(self, take_snapshot, key=None):
        """Store the state *before* an edit. Returns False if coalesced."""
        now = self.clock()
        if key and key == self._last_key and now - self._last_t < self.window:
            self._last_t = now
            return False
        self._last_key, self._last_t = key, now
        self.undo_stack.append(take_snapshot())
        if len(self.undo_stack) > self.limit:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        return True

    def undo(self, take_snapshot):
        if not self.undo_stack:
            return None
        self.redo_stack.append(take_snapshot())
        self._last_key = None
        return self.undo_stack.pop()

    def redo(self, take_snapshot):
        if not self.redo_stack:
            return None
        self.undo_stack.append(take_snapshot())
        self._last_key = None
        return self.redo_stack.pop()

    def clear(self):
        self.undo_stack.clear()
        self.redo_stack.clear()

    @property
    def can_undo(self):
        return bool(self.undo_stack)

    @property
    def can_redo(self):
        return bool(self.redo_stack)
