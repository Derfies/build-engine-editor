from collections import defaultdict

from PySide6.QtCore import QCoreApplication, Qt, QRectF
from PySide6.QtGui import QTransform, QPen, QColorConstants, QPolygonF
from PySide6.QtWidgets import QGraphicsScene, QApplication

from editor import commands
from rubberband import RubberBandGraphicsItem

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


DRAG_TOLERANCE = 4


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

            # TODO: Only need to call this during commit, I think.
            for item in self.affected_items:
                item.invalidate_shapes()

            print('COMMIT MOVE')
            #self.app().doc.updated()
            self._last_scene_pos = None
        else:
            super().mouse_release_event(event)


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
