from PySide6.QtCore import QCoreApplication, QLineF, QPointF
from PySide6.QtGui import QBrush, QPainterPath, QPainterPathStroker, QPen, Qt
from PySide6.QtWidgets import QApplication, QGraphicsItem, QGraphicsLineItem, QGraphicsRectItem, QGraphicsPolygonItem, QGraphicsPathItem

from editor.graph import Edge, Node, Face

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


NODE_RADIUS = 2


class GraphicsItemBaseMixin:

    def __init__(self, element: Node | Edge | Face, *args, **kwargs):
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

    def move_node(self, node: Node, x: float, y: float):
        ...


class NodeGraphicsItem(GraphicsItemBaseMixin, QGraphicsRectItem):

    def __init__(self, node: Node):
        super().__init__(node, -NODE_RADIUS, -NODE_RADIUS, NODE_RADIUS * 2, NODE_RADIUS * 2)

        self.setZValue(100)
        self.set_flag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.set_pos(self.element().pos)

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
        # Wait, why are we using paint path? Can't I just use a vanilla rect?
        path = QPainterPath()
        radius = self.app().general_settings.node_selectable_thickness
        path.add_rect(
            -radius / scale,
            -radius / scale,
            radius * 2 / scale,
            radius * 2 / scale,
        )
        return path

    def move_node(self, node: Node, x: float, y: float):
        if node == self.element():
            self.set_pos(QPointF(x, y))


class EdgeGraphicsItem(GraphicsItemBaseMixin, QGraphicsLineItem):

    # NOTE: We're doing stuff in local space where whereas doing stuff in scene
    # space for the node...

    def __init__(self, edge: Edge):
        super().__init__(edge)

        self.set_line(QLineF(self.element().head.pos, self.element().tail.pos))
        self.setZValue(50)

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
        factor = self.app().general_settings.edge_selectable_thickness / scale

        # Create a larger clickable shape.
        path = QPainterPath()
        path.move_to(self.line().p1())
        path.line_to(self.line().p2())
        stroker = QPainterPathStroker()
        stroker.set_width(factor)

        return stroker.create_stroke(path)

    def move_node(self, node: Node, x: float, y: float):
        pos = QPointF(x, y)
        line = self.line()
        if node == self.element().head:
            line.set_p1(pos)
        elif node == self.element().tail:
            line.set_p2(pos)
        self.set_line(line)


class FaceGraphicsItem(GraphicsItemBaseMixin, QGraphicsPathItem):

    def __init__(self, face: Face, *args, **kwargs):
        super().__init__(face, *args, **kwargs)

        num_nodes = 0
        path = QPainterPath()
        for ring in face.rings:
            path.add_polygon([node.pos for node in ring.nodes])
            num_nodes += len(ring.nodes)
        self.set_path(path)
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
        return QGraphicsPathItem.shape(self)

    def move_node(self, node: Node, x: float, y: float):

        # This interface is kinda trash now. The pain we have to go through to
        # find the nth point in several polygons. Yuk.
        idx = self.element().nodes.index(node)

        num_nodes = 0
        new_path = QPainterPath()
        for polygon in self.path().to_subpath_polygons():
            new_polygon = []
            for i, p in enumerate(polygon):
                if idx == num_nodes + i:
                    p = QPointF(x, y)
                new_polygon.append(p)
            new_path.add_polygon(new_polygon)
            num_nodes += len(polygon)

        self.set_path(new_path)
