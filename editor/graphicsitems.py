from PySide6.QtCore import QLineF, QPointF, QRect
from PySide6.QtGui import QBrush, QColorConstants, QPainterPath, QPainterPathStroker, QPen, QPolygonF, Qt
from PySide6.QtWidgets import QGraphicsItem, QGraphicsLineItem, QGraphicsPathItem, QGraphicsRectItem

from editor.graph import Edge, Node, Poly

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


NODE_RADIUS = 2
NODE_COLLISION_RADIUS = 6
WALL_COLLISION_THICKNESS = 7


class GraphicsItemBaseMixin:

    def __init__(self, element: Edge | Node | Poly, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.pen = None
        self._shape = None
        self._rubberband_shape = None
        self.set_data(0, element)
        self.update_pen()

    def element(self):
        return self.data(0)

    def update_pen(self):
        colour = QColorConstants.Cyan if self.element().is_selected else QColorConstants.DarkGray
        width = 2 if self.element().is_selected else 1
        self.pen = QPen(colour, width)
        self.pen.set_cosmetic(True)
        self.set_pen(self.pen)

    def invalidate_shapes(self):
        self._shape = None
        self._rubberband_shape = None

    def get_shape(self):
        ...

    def shape(self):
        if self._shape is None:
            self._shape = self.get_shape()
        return self._shape

    def rubberband_shape(self):
        if self._rubberband_shape is None:
            self._rubberband_shape = self.shape().bounding_rect().translated(self.pos())
        return self._rubberband_shape


class NodeGraphicsItem(GraphicsItemBaseMixin, QGraphicsRectItem):

    def __init__(self, node: Node):
        super().__init__(node, -NODE_RADIUS, -NODE_RADIUS, NODE_RADIUS * 2, NODE_RADIUS * 2)

        self.setZValue(100)
        self.set_flag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        p = QPointF(self.element().x, self.element().y)
        self.set_pos(p)

    def bounding_rect(self):
        return self.shape().bounding_rect()

    def get_shape(self):

        # Get the current transform matrix - extract the horizontal.
        scale = self.scene().views()[0].transform().m11()

        # Create a larger clickable shape.
        path = QPainterPath()
        path.add_rect(
            -NODE_COLLISION_RADIUS / scale,
            -NODE_COLLISION_RADIUS / scale,
            NODE_COLLISION_RADIUS * 2 / scale,
            NODE_COLLISION_RADIUS * 2 / scale,
        )
        return path


class EdgeGraphicsItem(GraphicsItemBaseMixin, QGraphicsLineItem):

    def __init__(self, edge: Edge):
        super().__init__(edge)

        self.setZValue(50)
        p1 = QPointF(self.element().node1.x, self.element().node1.y)
        p2 = QPointF(self.element().node2.x, self.element().node2.y)
        self.set_pos(p1)
        self.set_line(QLineF(QPointF(0, 0), p2 - p1))

    def get_shape(self):

        # Get the current transform matrix - extract the horizontal.
        scale = self.scene().views()[0].transform().m11()
        factor = WALL_COLLISION_THICKNESS / scale

        # Create a larger clickable shape.
        path = QPainterPath()
        path.move_to(self.line().p1())
        path.line_to(self.line().p2())
        stroker = QPainterPathStroker()
        stroker.set_width(factor)

        return stroker.create_stroke(path)


class PolyGraphicsItem(GraphicsItemBaseMixin, QGraphicsPathItem):

    def __init__(self, poly: Poly, *args, **kwargs):
        super().__init__(poly, *args, **kwargs)

        outer = QPolygonF([
            QPointF(node.data.x, node.data.y)
            for node in poly.nodes
        ])
        outer.append(QPointF(poly.nodes[0].data.x, poly.nodes[0].data.y))
        self.poly = outer
        path = QPainterPath()
        path.add_polygon(outer)
        self.set_path(path)
        self.setZValue(0)

    def update_pen(self):
        colour = QColorConstants.Cyan if self.element().is_selected else QColorConstants.DarkBlue
        self.pen = Qt.NoPen
        self.set_pen(self.pen)
        self.brush = QBrush(colour)
        self.set_brush(self.brush)

    def get_shape(self):

        # TODO: This could be default as we're having to override override behaviour
        return QGraphicsPathItem.shape(self)
