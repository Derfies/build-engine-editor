from PySide6.QtCore import QCoreApplication, QLineF, QPointF
from PySide6.QtGui import QBrush, QColorConstants, QPainterPath, QPainterPathStroker, QPen, QPolygonF, Qt
from PySide6.QtWidgets import QApplication, QGraphicsItem, QGraphicsLineItem, QGraphicsPathItem, QGraphicsRectItem, QGraphicsPolygonItem

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

    def app(self) -> QCoreApplication:
        return QApplication.instance()

    def element(self):
        return self.data(0)

    def update_pen(self):
        ...

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

    def update_nodes(self, nodes, delta: QPointF):
        ...


class NodeGraphicsItem(GraphicsItemBaseMixin, QGraphicsRectItem):

    def __init__(self, node: Node):
        super().__init__(node, -NODE_RADIUS, -NODE_RADIUS, NODE_RADIUS * 2, NODE_RADIUS * 2)

        self.setZValue(100)
        self.set_flag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        p = QPointF(self.element().x, self.element().y)
        self.set_pos(p)

    def update_pen(self):

        # TODO: Can possibly abstract this method a bit more.
        colour = self.app().colour_settings.selected_node if self.element().is_selected else self.app().colour_settings.node
        width = 2 if self.element().is_selected else 1
        self.pen = QPen(colour, width)
        self.pen.set_cosmetic(True)
        self.set_pen(self.pen)

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

    def update_nodes(self, nodes: set[Node], delta: QPointF):
        assert self.element() in nodes, f'Item doesnt own element in set: {nodes}'
        assert len(nodes) == 1
        p = delta
        self.move_by(p.x(), p.y())


class EdgeGraphicsItem(GraphicsItemBaseMixin, QGraphicsLineItem):

    # NOTE: We're doing stuff in local space where whereas doing stuff in scene
    # space for the node...

    def __init__(self, edge: Edge):
        super().__init__(edge)

        self.setZValue(50)
        p1 = QPointF(self.element().node1.x, self.element().node1.y)
        p2 = QPointF(self.element().node2.x, self.element().node2.y)
        self.set_line(QLineF(p1, p2))

    def update_pen(self):

        # TODO: Can possibly abstract this method a bit more.
        colour = self.app().colour_settings.selected_edge if self.element().is_selected else self.app().colour_settings.edge
        width = 2 if self.element().is_selected else 1
        self.pen = QPen(colour, width)
        self.pen.set_cosmetic(True)
        self.set_pen(self.pen)

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

    def update_nodes(self, nodes: set[Node], delta: QPointF):
        p1 = self.line().p1()
        if self.element().node1 in nodes:
            p1 += delta
        p2 = self.line().p2()
        if self.element().node2 in nodes:
            p2 += delta
        self.set_line(QLineF(p1, p2))


class PolyGraphicsItem(GraphicsItemBaseMixin, QGraphicsPolygonItem):

    def __init__(self, poly: Poly, *args, **kwargs):
        super().__init__(poly, *args, **kwargs)

        self.set_polygon([
            QPointF(edge.node1.data.x, edge.node1.data.y)
            for edge in poly.edges
        ])
        self.setZValue(0)

    def update_pen(self):

        # TODO: Can possibly abstract this method a bit more.
        colour = self.app().colour_settings.selected_poly if self.element().is_selected else self.app().colour_settings.poly
        self.pen = Qt.NoPen
        self.set_pen(self.pen)
        self.brush = QBrush(colour)
        self.set_brush(self.brush)

    def get_shape(self):

        # TODO: This could be default as we're having to override override behaviour
        return QGraphicsPolygonItem.shape(self)

    def update_nodes(self, nodes: set[Node], delta: QPointF):
        ps = []
        for i, p in enumerate(self.polygon()):
            if self.element().nodes[i] in nodes:
                p += delta
            ps.append(p)
        self.set_polygon(ps)
