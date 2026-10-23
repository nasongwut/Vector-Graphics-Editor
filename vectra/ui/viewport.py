"""World <-> screen mapping (zoom + pan offset)."""

from vectra.config import MAX_ZOOM, MIN_ZOOM


class Viewport:
    def __init__(self, zoom=1.0, ox=60.0, oy=60.0):
        self.zoom, self.ox, self.oy = zoom, ox, oy

    def to_world(self, sx, sy):
        return (sx - self.ox) / self.zoom, (sy - self.oy) / self.zoom

    def to_screen(self, pts):
        z, ox, oy = self.zoom, self.ox, self.oy
        return [v * z + (ox if i % 2 == 0 else oy) for i, v in enumerate(pts)]

    def pan(self, dx, dy):
        self.ox += dx
        self.oy += dy

    def zoom_at(self, factor, sx, sy):
        """Zoom keeping the world point under (sx, sy) fixed."""
        wx, wy = self.to_world(sx, sy)
        self.zoom = min(MAX_ZOOM, max(MIN_ZOOM, self.zoom * factor))
        self.ox = sx - wx * self.zoom
        self.oy = sy - wy * self.zoom

    def fit(self, rect, width, height, margin=120):
        """Centre ``rect`` in a width×height view. Returns False if the view is too small."""
        if width < 10 or height < 10:
            return False
        rw, rh = rect[2] - rect[0], rect[3] - rect[1]
        self.zoom = min((width - margin) / rw, (height - margin) / rh)
        self.ox = (width - rw * self.zoom) / 2 - rect[0] * self.zoom
        self.oy = (height - rh * self.zoom) / 2 - rect[1] * self.zoom
        return True

    def grid_step(self, grid):
        """On-screen grid spacing, doubled/halved to stay readable."""
        g = grid
        while g * self.zoom < 10:
            g *= 2
        while g * self.zoom > 60 and g > 1:
            g /= 2
        return g * self.zoom
