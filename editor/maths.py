import math

import numpy as np
from PySide6.QtCore import QPointF

# noinspection PyUnresolvedReferences
from __feature__ import snake_case
from shapely import LineString


def percentage_along_line(A: QPointF, B: QPointF, C: QPointF) -> float:
    AB = B - A
    AC = C - A
    dot_product = AB.x() * AC.x() + AB.y() * AC.y()
    length_squared = AB.x() ** 2 + AB.y() ** 2
    t = dot_product / length_squared
    return t# * 100


def lerp(v0, v1, t):
    return (1 - t) * v0 + t * v1


def normalize(v):
    norm = np.linalg.norm(v)
    return v / norm if norm > 0 else v


def edge_normal(p1, p2):
    """Return a unit normal vector pointing to the left of the edge."""
    x0, y0 = p1
    x1, y1 = p2
    dx, dy = x1 - x0, y1 - y0
    normal = np.array([dy, -dx])
    return normalize(normal)


def long_line_through(p1, p2, buffer=1000):
    """
    Extend a line between p1 and p2 to a long line that exceeds the given bounds.
    """
    x1, y1 = p1
    x2, y2 = p2
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    dx /= length
    dy /= length

    # Extend well beyond polygon bounds
    extended_p1 = (x1 - dx * buffer, y1 - dy * buffer)
    extended_p2 = (x2 + dx * buffer, y2 + dy * buffer)

    return LineString([extended_p1, extended_p2])


def midpoint(a, b):
    return [(x + y) / 2 for x, y in zip(a, b)]
