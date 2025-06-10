from PySide6.QtCore import QPointF, QLineF

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


def project_point_onto_segment(p: QPointF, line: QLineF) -> QPointF:
    dx = line.dx()
    dy = line.dy()
    if dx == dy == 0:
        return line.p1()

    t = ((p.x() - line.x1()) * dx + (p.y() - line.y1()) * dy) / (
                dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return line.point_at(t)


def percentage_along_line(A: QPointF, B: QPointF, C: QPointF) -> float:
    AB = B - A
    AC = C - A
    dot_product = AB.x() * AC.x() + AB.y() * AC.y()
    length_squared = AB.x() ** 2 + AB.y() ** 2
    t = dot_product / length_squared
    return t# * 100


def lerp(v0, v1, t):

    # TODO: Move to mathslib
    return (1 - t) * v0 + t * v1
