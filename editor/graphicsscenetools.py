import math
import uuid
from itertools import product

from PySide6.QtCore import QCoreApplication, QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import QColorConstants, QPainter, QPen, QPolygonF, QTransform
from PySide6.QtWidgets import QApplication, QGraphicsItem, QGraphicsLineItem, QGraphicsPolygonItem, QGraphicsScene

from editor import commands
from editor.graphicsitems import EdgeGraphicsItem
from editor.maths import project_point_onto_segment, percentage_along_line
from gameengines.build.map import Sector, Wall
from rubberband import RubberBandGraphicsItem

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


DRAG_TOLERANCE = 4
HIT_MARK_SIZE = 5
NODE_RADIUS = 2


def create_foobar(points: tuple[QPointF]):

    # TODO: Clean this up and properly define how we add new graph elements.
    nodes = tuple([str(uuid.uuid4()) for node in points])
    node_attrs = {
        nodes[i]: {'pos': point}
        for i, point in enumerate(points)
    }
    edge_attrs = {}
    for i in range(len(nodes)):
        head = nodes[i]
        tail = nodes[(i + 1) % len(nodes)]
        edge_attrs[(head, tail)] = {'wall': Wall()}
    face_attrs = {nodes: {'sector': Sector()}}
    return nodes, tuple(), tuple(), node_attrs, edge_attrs, face_attrs


class HitMark(QGraphicsItem):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._pen = QPen(Qt.yellow)
        self._pen.set_width(1)
        self._pen.set_cosmetic(True)
        self.setZValue(1000)

    def foo(self):
        return NODE_RADIUS / self.scene().xform

    def bounding_rect(self) -> QRectF:
        foo = self.foo()
        return QRectF(-foo - 1, -foo - 1, foo * 2 + 2, foo * 2 + 2)

    def paint(self, painter: QPainter, option, widget=None):
        foo = self.foo()
        painter.set_pen(self._pen)
        painter.draw_rect(
            -foo,
            -foo,
            foo * 2,
            foo * 2,
        )

    def contains(self, point):
        return False


class GraphicsSceneToolBase:

    def __init__(self, scene: QGraphicsScene):
        self.scene = scene
        self.hit_mark = None
        self.preview = None
        self.preview_pen = QPen(QColorConstants.DarkGray, 1, Qt.DashLine)
        self.preview_pen.set_cosmetic(True)

    def app(self) -> QCoreApplication:
        return QApplication.instance()

    def add_hit_mark(self, pos: QPointF | None = None):
        if self.hit_mark is None:
            self.hit_mark = HitMark()
            self.scene.add_item(self.hit_mark)
        if pos is not None:
            self.hit_mark.set_pos(pos)

    def remove_hit_mark(self):
        if self.hit_mark is not None:
            self.scene.remove_item(self.hit_mark)
            self.hit_mark = None

    def add_preview(self, item: QGraphicsItem):
        self.preview = item
        self.preview.set_pen(self.preview_pen)
        self.scene.add_item(self.preview)

    def remove_preview(self):
        if self.preview is not None:
            self.scene.remove_item(self.preview)
            self.preview = None

    def mouse_press_event(self, event):
        ...

    def mouse_move_event(self, event):
        ...

    def mouse_release_event(self, event):
        ...

    def cancel(self):
        self.remove_hit_mark()
        self.remove_preview()


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
            self.add_preview(QGraphicsPolygonItem())

    def mouse_move_event(self, event):
        if self.preview is not None:
            end_point = event.scene_pos()
            radius = (end_point - self._start_point).manhattan_length()
            polygon = self._create_polygon(self._start_point, self._num_sides, radius)
            self.preview.set_polygon(polygon)

    def mouse_release_event(self, event):
        if event.button() == Qt.LeftButton:
            nodes, _, _, node_attrs, edge_attrs, face_attrs = create_foobar(self.preview.polygon())
            self.cancel()
            commands.add_face(nodes, node_attrs=node_attrs, edge_attrs=edge_attrs, face_attrs=face_attrs)


class CreateFreeformPolygonTool(GraphicsSceneToolBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._points = []

    def _update_preview(self, temp_point: QPointF | None = None):
        self.remove_preview()
        points = self._points[:]
        if temp_point is not None:
            points.append(self.scene.apply_snapping(temp_point))
        self.add_preview(QGraphicsPolygonItem(points))

    def mouse_press_event(self, event):
        if event.button() == Qt.LeftButton:
            self._points.append(self.scene.apply_snapping(event.scene_pos()))
            self._update_preview()
        elif event.button() == Qt.RightButton and self.preview is not None:
            if len(self._points) < 3:
                self.cancel()
                return
            nodes, _, _, node_attrs, edge_attrs, face_attrs = create_foobar(self._points)
            self.cancel()
            commands.add_face(nodes, node_attrs=node_attrs, edge_attrs=edge_attrs, face_attrs=face_attrs)

    def mouse_move_event(self, event):
        if self._points:
            self._update_preview(event.scene_pos())

    def cancel(self):
        super().cancel()
        self._points = []


class SplitFaceTool(GraphicsSceneToolBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._start_point = None
        self._splits = []
        self._points = []
        self._edges = []

    def _get_face(self):
        for a, b in product(self._edges[-2].hedges, self._edges[-1].hedges):
            if a.face == b.face:
                return a, b

    def _get_foo(self, pos):
        hit_item = self.scene.item_at(pos, QTransform())

        # TODO: Better way to check whether its an edge.
        if isinstance(hit_item, EdgeGraphicsItem):
            edge = hit_item.element()
            segment = QLineF(edge.head.pos, edge.tail.pos)
            return edge, project_point_onto_segment(pos, segment)
        return None, pos

    def mouse_press_event(self, event):
        if event.button() == Qt.LeftButton and self.hit_mark is not None:
            edge, pos = self._get_foo(event.scene_pos())
            self._points.append(pos)
            self._edges.append(edge)
            x, y = pos.x(), pos.y()
            self.add_preview(QGraphicsLineItem(x, y, x, y))
            if len(self._edges) > 1:
                a, b = self._get_face()
                self._splits.append((a, percentage_along_line(a.head.pos, a.tail.pos, self._points[-2])))
            self._start_point = pos

        elif event.button() == Qt.RightButton:

            # TODO: Support splitting *just* an edge, ie no new bridge.
            a, b = self._get_face()
            self._splits.append((b, percentage_along_line(b.head.pos, b.tail.pos, self._points[-1])))
            splits = self._splits[:]
            self.cancel()
            commands.split_face(*splits)

    def mouse_move_event(self, event):
        self.remove_hit_mark()
        hit_edge, pos = self._get_foo(event.scene_pos())
        if hit_edge is not None:
            self.add_hit_mark(pos)
        if self.preview is not None:
            self.preview.set_line(QLineF(self._start_point, pos))

    def cancel(self):
        super().cancel()
        self._start_point = None
        self._splits.clear()
        self._points.clear()
        self._edges.clear()
