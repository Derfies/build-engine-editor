from PySide6.QtCore import Qt, QPointF, QLineF
from PySide6.QtGui import QPen, QColorConstants, QPainterPath, QPainterPathStroker, QPolygonF, QBrush
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsItem, QGraphicsLineItem, QGraphicsPathItem

from editor.content import EditorWall, EditorSector

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


NODE_RADIUS = 2
WALL_COLLISION_THICKNESS = 7


class NodeGraphicsItem(QGraphicsRectItem):

    def __init__(self, node):
        super().__init__(-NODE_RADIUS, -NODE_RADIUS, 2 * NODE_RADIUS, 2 * NODE_RADIUS)

        self.node = node
        self.rad = NODE_RADIUS
        self.set_flag(QGraphicsItem.ItemIgnoresTransformations)
        # self.set_flag(QGraphicsItem.ItemIsMovable)
        # self.set_flag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setZValue(1)

        pen = QPen(Qt.green, 1)
        pen.set_cosmetic(True)  # <- Key line
        self.set_pen(pen)

    #def update_position(self):
    #    self.set_line(QLineF(self.head, self.tail))

    # def item_change(self, change, value):
    #     if self.edge is not None:
    #         self.edge.head = self.scene_pos()
    #         self.edge.update_position()
    #     return super().item_change(change, value)


class WallGraphicsItem(QGraphicsLineItem):

    def __init__(self, wall: EditorWall, head: QPointF, tail: QPointF, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_data(0, wall)
        self.head = head
        self.tail = tail
        self.update_position()
        self.update_pen()
        self._stroke = None

    def invalidate_shape(self):
        self._stroke = None

    def update_pen(self):
        colour = QColorConstants.Cyan if self.wall.is_selected else QColorConstants.DarkGray
        width = 2 if self.data(0).is_selected else 1
        pen = QPen(colour, width)
        pen.set_cosmetic(True)
        self.set_pen(pen)

    @property
    def wall(self):
        return self.data(0)

    def update_position(self):
        self.set_line(QLineF(self.head, self.tail))

    def shape(self):

        if self._stroke is None:

            # Create a wider shape (e.g., 10px clickable area)
            path = QPainterPath()
            path.move_to(self.line().p1())
            path.line_to(self.line().p2())

            # Get the current transform matrix
            view = self.scene().views()[0]
            transform_matrix = view.transform()

            # Extract the horizontal
            # TODO: Still not giving consistent widths.
            horizontal_scale = transform_matrix.m11()
            stroker_pen_width = WALL_COLLISION_THICKNESS * 1 / horizontal_scale
            stroker = QPainterPathStroker()
            stroker.set_width(stroker_pen_width)
            self._stroke = stroker.create_stroke(path)

        return self._stroke


class SectorGraphicsItem(QGraphicsPathItem):

    def __init__(self, sector: EditorSector, *args, **kwargs):
        outer = QPolygonF([
            QPointF(wall.raw.x, wall.raw.y)
            for wall in sector.walls
        ])
        outer.append(QPointF(sector.walls[0].raw.x, sector.walls[0].raw.y))
        path = QPainterPath()
        path.add_polygon(outer)
        super().__init__(path, *args, **kwargs)
        self.set_data(0, sector)
        self.set_brush(QBrush(QColorConstants.DarkBlue))

    @property
    def sector(self):
        return self.data(0)
