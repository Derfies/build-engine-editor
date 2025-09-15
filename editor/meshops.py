from PySide6.QtCore import QPointF
from shapely.geometry import LineString


def downsample_path(qpoints, tolerance=2.0):
    coords = [(p.x(), p.y()) for p in qpoints]
    simplified = LineString(coords).simplify(tolerance)
    return [QPointF(x, y) for x, y in simplified.coords]
