import math
from itertools import product

from PySide6.QtCore import QCoreApplication, QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import QColorConstants, QPainter, QPen, QPolygonF, QTransform
from PySide6.QtWidgets import QApplication, QGraphicsItem, QGraphicsLineItem, QGraphicsPolygonItem, QGraphicsScene
from shapely import box, LineString, Point

from editor import commands
from editor.constants import SelectionMode
from editor.graph import Edge, Face, Hedge, Node
from editor.graphicsitems import EdgeGraphicsItem
from editor.maths import percentage_along_line
from rubberband import RubberBandGraphicsItem

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


# DRAG_TOLERANCE = 4
NODE_RADIUS = 2


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


class SelectTool(GraphicsSceneToolBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._start_point = None
        self._rubber_band = None

    def add_rubber_band(self):
        self._rubber_band = RubberBandGraphicsItem()
        self.scene.add_item(self._rubber_band)

    def remove_rubber_band(self):
        self.scene.remove_item(self._rubber_band)
        self._rubber_band = None

    def mouse_press_event(self, event):
        self._start_point = event.scene_pos()

    def mouse_move_event(self, event):
        if not self._start_point:
            return

        # Stop micro-movements from engaging the rubber band.
        view = self.scene.views()[0]
        delta = (view.map_from_scene(event.scene_pos()) - view.map_from_scene(self._start_point)).manhattan_length()
        if delta > self.app().general_settings.rubberband_drag_tolerance:
            if self._rubber_band is None:
                self.add_rubber_band()
            else:
                rect = QRectF(self._start_point, event.scene_pos()).normalized()
                self._rubber_band.set_rect(rect)
        elif self._rubber_band is not None:
            self.remove_rubber_band()

    def mouse_release_event(self, event):

        # Resolve items within rubber band bounds or directly under mouse.
        hit_item = self.scene.item_at(self._start_point, QTransform())
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

        # Filter.
        for item in set(items):
            if self.scene.selection_mode == SelectionMode.NODE and not isinstance(item.element(), Node):
                items.remove(item)
            elif self.scene.selection_mode == SelectionMode.EDGE and not isinstance(item.element(), Edge):
                items.remove(item)
            elif self.scene.selection_mode == SelectionMode.FACE and not isinstance(item.element(), Face):
                items.remove(item)

        # Resolve mode based on ctrl / shift modifiers.
        modifiers = event.modifiers()
        add = modifiers & Qt.ShiftModifier
        toggle = modifiers & Qt.ControlModifier

        # Resolve selected elements using modifiers.
        select_elements = self.app().doc.selected_elements
        select_elements = select_elements.copy() if add or toggle else set()
        for item in items:
            element = item.element()
            if toggle:
                select_elements.symmetric_difference_update({element})
            else:
                select_elements.add(element)

        self._start_point = None
        self.remove_rubber_band()

        commands.select_elements(select_elements)


class MoveTool(SelectTool):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_point = None

    def mouse_press_event(self, event):

        # Resolve mode based on ctrl / shift modifiers.
        modifiers = event.modifiers()
        add = modifiers & Qt.ShiftModifier
        toggle = modifiers & Qt.ControlModifier

        scene_pos = event.scene_pos()
        item = self.scene.item_at(scene_pos, QTransform())
        if item is not None and item.element().is_selected and not(add or toggle):
            self._last_point = scene_pos

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
        if self._last_point is not None:

            # Update the graphics view. Note this doesn't change any content data
            # just yet.
            # TODO: Can probably work out a neat way to do the set intersection
            # earlier.
            scene_pos = self.scene.apply_snapping(event.scene_pos())
            delta_pos = scene_pos - self._last_point
            for item in self.affected_items:
                item.update_nodes(self.scene._item_to_nodes[item] & self.affected_nodes, delta_pos)
            self._last_point = scene_pos
        else:
            super().mouse_move_event(event)

    def mouse_release_event(self, event):
        if self._last_point is not None:
            commands.transform_node_items([
                self.scene._node_to_node_item[node]
                for node in self.affected_nodes
            ])
            self._last_point = None
        else:
            super().mouse_release_event(event)


class RotateTool(GraphicsSceneToolBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._start_point = None

    def mouse_press_event(self, event):
        if event.button() == Qt.LeftButton:
            self._start_point = self.scene.apply_snapping(event.scene_pos())

    def mouse_move_event(self, event):
        if self._start_point is not None:
            end_point = self.scene.apply_snapping(event.scene_pos())
            delta = end_point - self._start_point
            radians = math.atan2(delta.y(), delta.x())
            print('radians:', radians)

            # TODO: Not all nodes are affected!!!
            self.affected_nodes = set()
            for element in self.app().doc.selected_elements:
                self.affected_nodes.update(element.nodes)
            self.affected_items = set()
            for node in self.affected_nodes:
                self.affected_items.update(self.scene._node_to_items[node])


    def mouse_release_event(self, event):
        self.cancel()

    def cancel(self):
        super().cancel()
        self._start_point = None


class CreatePolygonTool(GraphicsSceneToolBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._num_sides = 4
        self._start_point = None

    @staticmethod
    def _create_polygon(center: QPointF, num_sides: int, radius: float, radians: float) -> QPolygonF:
        angle_offset = math.pi / num_sides + radians
        points = []
        for i in range(num_sides):
            angle = 2 * math.pi * i / num_sides + angle_offset
            x = center.x() + radius * math.cos(angle)
            y = center.y() + radius * math.sin(angle)
            points.append(QPointF(x, y))
        return QPolygonF(points)

    def mouse_press_event(self, event):
        if event.button() == Qt.LeftButton:
            self._start_point = self.scene.apply_snapping(event.scene_pos())
            self.add_preview(QGraphicsPolygonItem())

    def mouse_move_event(self, event):
        if self.preview is not None:
            end_point = self.scene.apply_snapping(event.scene_pos())
            delta = end_point - self._start_point
            radius = delta.manhattan_length()
            radians = math.atan2(delta.y(), delta.x())
            polygon = self._create_polygon(self._start_point, self._num_sides, radius, radians)
            self.preview.set_polygon(polygon)

    def mouse_release_event(self, event):
        if event.button() == Qt.LeftButton:
            points = [p.to_tuple() for p in self.preview.polygon()]
            self.cancel()
            commands.add_face(points)


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
            points = [p.to_tuple() for p in self._points]
            self.cancel()
            commands.add_face(points)

    def mouse_move_event(self, event):
        if self._points:
            self._update_preview(event.scene_pos())

    def cancel(self):
        super().cancel()
        self._points = []


class SplitFacesTool(GraphicsSceneToolBase):

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

    def _get_foo(self, pos: QPointF):
        hit_item = self.scene.item_at(pos, QTransform())

        # TODO: Better way to check whether its an edge.
        if isinstance(hit_item, EdgeGraphicsItem):
            edge = hit_item.element()
            line = LineString([edge.head.pos.to_tuple(), edge.tail.pos.to_tuple()])
            pt = Point(pos.to_tuple())
            projected_pt = line.interpolate(line.project(pt))
            return edge, QPointF(projected_pt.x, projected_pt.y)

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
                self._splits.append((b, percentage_along_line(b.head.pos, b.tail.pos, self._points[-1])))
            self._start_point = pos

        elif event.button() == Qt.RightButton:

            # TODO: Support splitting *just* an edge, ie no new bridge.
            # if len(self._edges) > 1:
            #     a, b = self._get_face()
            #     self._splits.append((b, percentage_along_line(b.head.pos, b.tail.pos, self._points[-1])))
            # else:
            #     h = next(iter(self._edges[-1].hedges))
            #     self._splits.append((h, percentage_along_line(h.head.pos,  h.tail.pos, self._points[-1])))
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

        # TODO: Remove all cut lines.
        super().cancel()
        self._start_point = None
        self._splits.clear()
        self._points.clear()
        self._edges.clear()



def extend_line_with_shapely(p1: QPointF, p2: QPointF, view_rect):

    # Convert view rect to shapely box.
    view_box = box(view_rect.left(), view_rect.top(), view_rect.right(), view_rect.bottom())

    # Extend the line far in both directions
    dx, dy = p2.x() - p1.x(), p2.y() - p1.y()
    line = LineString([
        (p1.x() - dx * 1000, p1.y() - dy * 1000),
        (p2.x() + dx * 1000, p2.y() + dy * 1000)
    ])

    # Clip it to the viewport bounding box
    clipped = view_box.intersection(line).coords
    return QLineF(QPointF(*clipped[0]), QPointF(*clipped[-1]))


class SliceFacesTool(GraphicsSceneToolBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._start_point = None

    def mouse_press_event(self, event):
        self._start_point = event.scene_pos()
        self._end_point = self._start_point
        x1, y1 = self._start_point.x(), self._start_point.y()
        x2, y2 = self._end_point.x(), self._end_point.y()
        self.add_preview(QGraphicsLineItem(x1, y1, x2, y2))

    def mouse_move_event(self, event):
        if self.preview is not None:
            self._end_point = event.scene_pos()
            view = self.scene.views()[0]
            view_rect = view.map_to_scene(view.viewport().rect()).bounding_rect()
            extended = extend_line_with_shapely(self._start_point, self._end_point, view_rect)
            self.preview.set_line(extended)

    def mouse_release_event(self, event):
        self.remove_preview()

    def cancel(self):
        self.remove_hit_mark()
        self.remove_preview()
