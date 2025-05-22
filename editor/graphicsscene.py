import logging

from PySide6.QtCore import QCoreApplication, QPointF, Qt, QLineF, QRectF
from PySide6.QtGui import QActionGroup, QBrush, QColorConstants, QPainterPath, QPainterPathStroker, QPen, QPolygonF, QTransform
from PySide6.QtWidgets import QApplication, QGraphicsScene, QGraphicsLineItem, QGraphicsPathItem

import commands
from applicationframework.document import Document
from editor.constants import ModalTool
from editor.content import EditorSector, EditorWall
from rubberband import RubberBandGraphicsItem
from updateflag import UpdateFlag

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


logger = logging.getLogger(__name__)


NODE_RADIUS = 2


class GraphicsSceneToolBase:

    def __init__(self, scene: QGraphicsScene):
        self.scene = scene

    def app(self) -> QCoreApplication:
        return QApplication.instance()

    def mouse_press_event(self, event):
        ...

    def mouse_move_event(self, event):
        ...

    def mouse_release_event(self, event):
        ...


class SelectGraphicsSceneTool(GraphicsSceneToolBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._mouse_origin = None
        self.rubber_band = None
        self.walls = []

    def mouse_press_event(self, event):
        self.walls = []

        scene_pos = event.scene_pos()
        self._mouse_origin = scene_pos
        item = self.scene.item_at(scene_pos, QTransform())
        if item is None:

            # Click occurred over empty space. Deselect walls if there are any.
            if self.app().doc.selected_edges:
                commands.select_edges([])

            # Start rubber band.
            self.rubber_band = RubberBandGraphicsItem()
            self.scene.add_item(self.rubber_band)
        else:

            # If ctrl is held during selection process, add / remove the clip
            # from the current selection appropriately.
            if event.modifiers() & Qt.ControlModifier:
                select_edges = self.app().doc.selected_edges[:]
                if item.wall in select_edges:
                    select_edges.remove(item.wall)
                else:
                    select_edges.append(item.wall)
            else:
                select_edges = [item.wall]

            # Don't trigger selection change unless something has actually changed.
            # if set(select_edges) != set(self.app().doc.selected_edges):
            commands.select_edges(select_edges)

    def mouse_move_event(self, event):
        if self.rubber_band is not None:
            scene_pos = event.scene_pos()
            delta_pos = scene_pos - self._mouse_origin
            rect = QRectF(self._mouse_origin.x(), self._mouse_origin.y(), delta_pos.x(), delta_pos.y()).normalized()
            self.rubber_band.set_rect(rect)

    def mouse_release_event(self, event):
        if self.rubber_band is not None:
            walls = []
            rubber_band_bb = self.rubber_band.bounding_rect()
            for item in self.scene.items():
                wall = item.data(0)
                if not isinstance(wall, EditorWall):
                    continue
                if rubber_band_bb.contains(item.bounding_rect()):
                    self.walls.append(wall)
            self.scene.remove_item(self.rubber_band)
            self.rubber_band = None
            if self.walls:
                commands.select_edges(self.walls)


class DrawSectorGraphicsSceneTool(GraphicsSceneToolBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._points = []
        self.temp_polygon = None
        self.pen = QPen(QColorConstants.DarkGray, 1, Qt.DashLine)
        self.pen.set_cosmetic(True)

    def _update_polygon_preview(self, temp_point=None):
        if self.temp_polygon:
            self.scene.remove_item(self.temp_polygon)

        polygon_points = self._points[:]
        if temp_point:
            polygon_points.append(temp_point)
        self.temp_polygon = self.scene.add_polygon(QPolygonF(polygon_points), self.pen)

    def mouse_press_event(self, event):
        if event.button() == Qt.LeftButton:
            point = event.scene_pos()
            self._points.append(point)
            self._update_polygon_preview()
        elif event.button() == Qt.RightButton:
            self.finish_polygon()

    def mouse_move_event(self, event):
        if self._points:
            self._update_polygon_preview(event.scene_pos())

    def finish_polygon(self):
        if self.temp_polygon:
            self.scene.remove_item(self.temp_polygon)
            self.temp_polygon = None
            self._points = []

# class Node(QGraphicsRectItem):
#
#     def __init__(self, edge):
#         super().__init__(-NODE_RADIUS, -NODE_RADIUS, 2 * NODE_RADIUS, 2 * NODE_RADIUS)
#
#         self.edge = edge
#         self.rad = NODE_RADIUS
#         self.set_flag(QGraphicsItem.ItemIgnoresTransformations)  # Key line
#         self.setZValue(1)
#         self.set_flag(QGraphicsItem.ItemIsMovable)
#         self.set_flag(QGraphicsItem.ItemSendsGeometryChanges)
#         pen = QPen(Qt.green, 1)
#         pen.set_cosmetic(True)  # <- Key line
#         self.set_pen(pen)
#
#     def item_change(self, change, value):
#         if self.edge is not None:
#             self.edge.head = self.scene_pos()
#             self.edge.update_position()
#         return super().item_change(change, value)


# class GraphicsItemBase:
#
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#
#         self._stroke = None
#



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
            stroker_pen_width = 6 * 1 / horizontal_scale
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


class GraphicsScene(QGraphicsScene):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.current_tool = None
        self.app().updated.connect(self.update_event)

    def app(self) -> QCoreApplication:
        return QApplication.instance()

    def set_modal_tool(self, modal_tool: ModalTool):
        tool_cls = {
            ModalTool.SELECT: SelectGraphicsSceneTool,
            ModalTool.DRAW_SECTOR: DrawSectorGraphicsSceneTool,
        }[modal_tool]
        self.current_tool = tool_cls(self)

    def mouse_press_event(self, event):
        super().mouse_press_event(event)

        self.current_tool.mouse_press_event(event)

    def mouse_move_event(self, event):
        super().mouse_move_event(event)

        self.current_tool.mouse_move_event(event)

    def mouse_release_event(self, event):
        super().mouse_release_event(event)

        self.current_tool.mouse_release_event(event)

    def update_event(self, doc: Document, flags: UpdateFlag):
        self.block_signals(True)
        if flags != UpdateFlag.SELECTION:

            logger.debug(f'Updating graphics scene: {flags}')

            self.clear()
            if doc.content.map is not None:

                edges = {}
                for wall_idx in range(len(doc.content.map.walls)):
                    head = doc.content.map.walls[wall_idx]
                    if head.nextwall > -1 and head.nextwall in edges:
                        #print('next wall found')
                        continue
                    tail = doc.content.map.walls[head.point2]
                    p1 = QPointF(head.x, head.y)
                    p2 = QPointF(tail.x, tail.y)
                    edge = WallGraphicsItem(doc.content.walls[wall_idx], p1, p2)
                    edge.setZValue(100)
                    self.add_item(edge)
                    edges[wall_idx] = edge

            for sector in doc.content.sectors:
                self.add_item(SectorGraphicsItem(sector))

        else:
            for item in self.items():
                wall = getattr(item, 'wall', None)
                if wall is not None:
                    item.update_pen()

        self.block_signals(False)
