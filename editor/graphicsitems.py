from PySide6.QtCore import Qt, QPointF, QLineF, QRect
from PySide6.QtGui import QBrush, QPen, QColorConstants, QPainterPath, QPainterPathStroker, QPainter, QTransform
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsItem, QGraphicsLineItem, QWidget, QStyleOptionGraphicsItem

from editor.graph import Edge, Node

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


NODE_RADIUS = 2
WALL_COLLISION_THICKNESS = 7


class GraphicsItemBaseMixin:

    def __init__(self, element: Edge | Node, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.pen = None
        self.set_data(0, element)
        self.update_pen()

        #self.set_flag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)

    def element(self):
        return self.data(0)

    def update_pen(self):
        colour = QColorConstants.Cyan if self.element().is_selected else QColorConstants.DarkGray
        width = 2 if self.element().is_selected else 1
        self.pen = QPen(colour, width)
        self.pen.set_cosmetic(True)
        self.set_pen(self.pen)


class NodeGraphicsItem(GraphicsItemBaseMixin, QGraphicsRectItem):

    def __init__(self, node: Node):
        super().__init__(node)

        self.set_flag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)

        x = self.element().x
        y = self.element().y
        self.set_pos(QPointF(x, y))

    # def mouse_press_event(self, event):
    #     scene_pos = self.map_to_scene(event.pos())
    #     items = self.scene().items(scene_pos)
    #     print("Hit items at", scene_pos, ":", items)

    def shape(self):
        path = QPainterPath()
        path.add_rect(-NODE_RADIUS, -NODE_RADIUS, NODE_RADIUS * 2, NODE_RADIUS * 2)  # Same shape, no scaling
        return path

    def paint(self, painter, option, widget = ...):


        rect = QRect(
            - NODE_RADIUS,
            - NODE_RADIUS,
            NODE_RADIUS * 2,
            NODE_RADIUS * 2,
        )

        painter.set_pen(self.pen)
        painter.draw_rect(
            rect,
        )

    def prepare_geometry_change(self):
        super().prepare_geometry_change()

        self.painter_path = None

    # def shape(self):
    #
    #     # Get the current view scale
    #     view = self.scene().views()[0]
    #     transform = view.transform()
    #     scale = transform.m11()  # Assuming uniform scaling (no shear/skew)
    #
    #     # Inverse scale: scene units per screen unit
    #     inverse_scale = 1.0 / scale# * 10
    #
    #     print('inverse_scale:', inverse_scale)
    #     rect = QRect(
    #             - inverse_scale,
    #             - inverse_scale,
    #             inverse_scale * 2,
    #             inverse_scale * 2,
    #         )
    #     print('rect:', rect)
    #     print('width:', rect.width(), 'height:', rect.height())
    #     print('bounding_rect:', self.bounding_rect())
    #
    #     #radius = 50#5 * inverse_scale  # 5 is the screen-space radius from paint()
    #
    #     path = QPainterPath()
    #     #path.add_ellipse(-inverse_scale, -inverse_scale, 2 * inverse_scale, 2 * inverse_scale)
    #     path.add_rect(
    #         rect
    #     )
    #     return path

    # def shape(self):
    #     view = self.scene().views()[0]
    #     transform = view.transform()
    #
    #     x_scale = transform.m11()
    #     y_scale = transform.m22()
    #     radius_x = 3 / x_scale
    #     radius_y = 3 / y_scale
    #     path = QPainterPath()
    #     path.add_ellipse(
    #         QRect(-radius_x, -radius_y, 2 * radius_x, 2 * radius_y))
    #
    #     return path

#     def shape(self):
#         view = self.scene().views()[0]
#
#         # Convert 1 screen pixel to scene length
#         screen_origin = QPointF(0, 0)
#         screen_one_pixel = QPointF(1, 0)
#
#         scene_origin = view.map_to_scene(screen_origin.to_point())
#         print('scene_origin:', scene_origin)
#         scene_one_pixel = view.map_to_scene(screen_one_pixel.to_point())
#         print('scene_one_pixel:', scene_one_pixel)
#         scene_pixel_size = (scene_one_pixel - scene_origin).x()
#         print('scene_pixel_size:', scene_pixel_size)
#
#         # Now use the scene length equivalent of the radius in pixels
#         radius_in_scene = 5 * scene_pixel_size
#
#         path = QPainterPath()
#         path.add_ellipse(-radius_in_scene, -radius_in_scene,
#                         2 * radius_in_scene, 2 * radius_in_scene)
#         return path
#
# def bounding_rect(self):
#     # Conservative guess — doesn't need to match shape exactly but must contain it
#     return QRect(-20, -20, 40, 40)


class EdgeGraphicsItem(GraphicsItemBaseMixin, QGraphicsLineItem):

    """
    TODO: Should the line be positioned at min(p1, p2) and then p2 set as p2-p1?
    """

    def __init__(self, edge: Edge):
        super().__init__(edge)

        self.painter_path = None
        p1 = QPointF(self.element().node1.x, self.element().node1.y)
        p2 = QPointF(self.element().node2.x, self.element().node2.y)
        self.set_line(QLineF(p1, p2))

    def prepare_geometry_change(self):
        super().prepare_geometry_change()

        self.painter_path = None

    def shape(self):
        if self.painter_path is None:

            # Get the current transform matrix - extract the horizontal.
            scale = self.scene().views()[0].transform().m11()
            factor = WALL_COLLISION_THICKNESS * 1 / scale

            # Create a wider shape (e.g., 10px clickable area)
            path = QPainterPath()
            path.move_to(self.line().p1())
            path.line_to(self.line().p2())
            stroker = QPainterPathStroker()
            stroker.set_width(factor)

            self.painter_path = stroker.create_stroke(path)

        return self.painter_path
