import math
import uuid

from PySide6.QtCore import QCoreApplication, QPointF, QRectF, Qt
from PySide6.QtGui import QTransform, QPen, QColorConstants, QPolygonF
from PySide6.QtWidgets import QApplication, QGraphicsPolygonItem, QGraphicsScene

from editor import commands
from editor.graph import Edge, Face, Node
from gameengines.build.map import Map, Sector, Sprite, Wall
from rubberband import RubberBandGraphicsItem

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


DRAG_TOLERANCE = 4


#
# def create_poly_edges(points: list[QPointF]):
#     nodes = [Node(Wall(x=int(point.x()), y=int(point.y()))) for point in points]
#     poly_edges = []
#     for i in range(len(nodes)):
#         node1 = nodes[i]
#         node2 = nodes[(i + 1) % len(nodes)]
#
#         # TODO: Ensure correct winding order - the wall that the edge
#         # owns is on the LEFT (I think).
#         edge = Edge(node1, node2, node1.data)
#         poly_edges.append(edge)
#     return poly_edges


def create_poly_nodes(points: tuple[QPointF]):
    return tuple([
        (str(uuid.uuid4()), {'x': points[i].x(), 'y': points[i].y()})
        for i in range(len(points))
    ])


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

    def cancel(self):
        ...


class SelectGraphicsSceneTool(GraphicsSceneToolBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._mouse_origin = None
        self._rubber_band = None

    def add_rubber_band(self):
        self._rubber_band = RubberBandGraphicsItem()
        self.scene.add_item(self._rubber_band)

    def remove_rubber_band(self):
        self.scene.remove_item(self._rubber_band)
        self._rubber_band = None

    def mouse_press_event(self, event):
        self._mouse_origin = event.scene_pos()

    def mouse_move_event(self, event):
        if not self._mouse_origin:
            return

        # Stop micro-movements from engaging the rubber band.
        view = self.scene.views()[0]
        delta_pos = (view.map_from_scene(event.scene_pos()) - view.map_from_scene(self._mouse_origin)).manhattan_length()
        if delta_pos > DRAG_TOLERANCE:
            if self._rubber_band is None:
                self.add_rubber_band()
            else:
                rect = QRectF(self._mouse_origin, event.scene_pos()).normalized()
                self._rubber_band.set_rect(rect)
        elif self._rubber_band is not None:
            self.remove_rubber_band()

    def mouse_release_event(self, event):

        # Resolve items within rubber band bounds or directly under mouse.
        hit_item = self.scene.item_at(self._mouse_origin, QTransform())
        items = set()
        if self._rubber_band is not None:
            rubber_band_bb = self._rubber_band.bounding_rect()
            for item in self.scene.items(rubber_band_bb):
                if item is self._rubber_band:
                    continue
                if rubber_band_bb.contains(item.rubberband_shape()):
                    items.add(item)
        elif hit_item is not None:
            items = {hit_item}

        # Resolve mode based on ctrl / shift modifiers.
        modifiers = event.modifiers()
        add = modifiers & Qt.ShiftModifier
        toggle = modifiers & Qt.ControlModifier

        # Resolve selected elements using modifiers.
        select_elements = self.app().doc.selected_elements.copy() if add or toggle else set()
        for item in items:
            element = item.element()
            if toggle:
                select_elements.symmetric_difference_update({element})
            else:
                select_elements.add(element)

        self._mouse_origin = None
        self.remove_rubber_band()

        commands.select_elements(select_elements)


class MoveGraphicsSceneTool(SelectGraphicsSceneTool):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._last_scene_pos = None

    def mouse_press_event(self, event):

        # Resolve mode based on ctrl / shift modifiers.
        modifiers = event.modifiers()
        add = modifiers & Qt.ShiftModifier
        toggle = modifiers & Qt.ControlModifier

        scene_pos = event.scene_pos()
        item = self.scene.item_at(scene_pos, QTransform())
        if item is not None and item.element().is_selected and not(add or toggle):
            self._last_scene_pos = scene_pos

            # TODO: Not all nodes are affected!!!
            self.affected_nodes = set()
            for element in self.app().doc.selected_elements:
                self.affected_nodes.update(element.nodes)
            self.affected_items = set()
            for node in self.affected_nodes:
                self.affected_items.update(self.scene._node_to_items[node])

        else:
            super().mouse_press_event(event)

    def mouse_move_event(self, event):
        if self._last_scene_pos is not None:

            # Update the graphics view. Note this doesn't change any content data
            # just yet.
            # TODO: Can probably work out a neat way to do the set intersection
            # earlier.
            scene_pos = event.scene_pos()
            delta_pos = scene_pos - self._last_scene_pos
            for item in self.affected_items:
                item.update_nodes(self.scene._item_to_nodes[item] & self.affected_nodes, delta_pos)

            self._last_scene_pos = scene_pos
        else:
            super().mouse_move_event(event)

    def mouse_release_event(self, event):
        if self._last_scene_pos is not None:
            commands.transform_node_items([
                self.scene._node_to_node_item[node]
                for node in self.affected_nodes
            ])
            self._last_scene_pos = None
        else:
            super().mouse_release_event(event)


class CreatePolygonTool(GraphicsSceneToolBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._num_sides = 4
        self._start_point = None
        self._preview = None
        self._pen = QPen(QColorConstants.DarkGray, 1, Qt.DashLine)
        self._pen.set_cosmetic(True)

    @staticmethod
    def _create_polygon(center: QPointF, num_sides: int, radius: float) -> QPolygonF:
        angle_offset = math.pi / num_sides
        points = []
        for i in range(num_sides):
            angle = 2 * math.pi * i / num_sides + angle_offset
            x = center.x() + radius * math.cos(angle)
            y = center.y() + radius * math.sin(angle)
            points.append(QPointF(x, y))
        return QPolygonF(points)

    def mouse_press_event(self, event):
        if event.button() == Qt.LeftButton:
            self._start_point = event.scene_pos()
            self._preview = QGraphicsPolygonItem()
            self._preview.set_pen(self._pen)
            self.scene.add_item(self._preview)

    def mouse_move_event(self, event):
        if self._preview is not None:
            end_point = event.scene_pos()
            radius = (end_point - self._start_point).manhattan_length()
            polygon = self._create_polygon(self._start_point, self._num_sides, radius)
            self._preview.set_polygon(polygon)

    def mouse_release_event(self, event):
        if event.button() == Qt.LeftButton:
            nodes = tuple([str(uuid.uuid4()) for node in self._preview.polygon()])
            node_attrs = {
                nodes[i]: {'x': point.x(), 'y': point.y()}
                for i, point in enumerate(self._preview.polygon())
            }
            edge_attrs = {}
            for i in range(len(nodes)):
                head = nodes[i]
                tail = nodes[(i + 1) % len(nodes)]
                edge_attrs[(head, tail)] = {'wall': Wall()}
            face_attrs = {nodes: {'sector': Sector()}}

            self.scene.remove_item(self._preview)
            self._preview = None
            commands.add_face(nodes, node_attrs=node_attrs, edge_attrs=edge_attrs, face_attrs=face_attrs)


class CreateFreeformPolygonTool(GraphicsSceneToolBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._points = []
        self._preview = None
        self._pen = QPen(QColorConstants.DarkGray, 1, Qt.DashLine)
        self._pen.set_cosmetic(True)

    def _update_preview(self, temp_point: QPointF | None = None):
        if self._preview is not None:
            self.scene.remove_item(self._preview)
        points = self._points[:]
        if temp_point is not None:
            points.append(temp_point)
        self._preview = self.scene.add_polygon(QPolygonF(points), self._pen)

    def mouse_press_event(self, event):
        if event.button() == Qt.LeftButton:
            self._points.append(event.scene_pos())
            self._update_preview()
        elif event.button() == Qt.RightButton and self._preview is not None:
            self._points.append(event.scene_pos())
            nodes = tuple([str(uuid.uuid4()) for node in self._preview.polygon()])
            node_attrs = {
                nodes[i]: {'x': point.x(), 'y': point.y()}
                for i, point in enumerate(self._preview.polygon())
            }
            edge_attrs = {}
            for i in range(len(nodes)):
                head = nodes[i]
                tail = nodes[(i + 1) % len(nodes)]
                edge_attrs[(head, tail)] = {'wall': Wall()}
            face_attrs = {nodes: {'sector': Sector()}}
            self.scene.remove_item(self._preview)
            self._preview = None
            self._points = []
            commands.add_face(nodes, node_attrs=node_attrs, edge_attrs=edge_attrs, face_attrs=face_attrs)

    def mouse_move_event(self, event):
        if self._points:
            self._update_preview(event.scene_pos())
