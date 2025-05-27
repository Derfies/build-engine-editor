from PySide6.QtCore import QCoreApplication, Qt, QRectF
from PySide6.QtGui import QTransform, QPen, QColorConstants, QPolygonF
from PySide6.QtWidgets import QGraphicsScene, QApplication

from editor import commands
from editor.graphicsitems import EdgeGraphicsItem
from rubberband import RubberBandGraphicsItem

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


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

    # BUG
    # Sometimes selecting with marquee doesn't work after selecting with pointer.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._mouse_origin = None
        self._rubber_band = None

    def mouse_press_event(self, event):
        scene_pos = event.scene_pos()
        self._mouse_origin = scene_pos
        item = self.scene.item_at(scene_pos, QTransform())
        if item is None:

            # Click occurred over empty space. Deselect walls if there are any.
            if self.app().doc.selected_elements:
                commands.select_elements({})

            # Start rubber band.
            self._rubber_band = RubberBandGraphicsItem()
            self.scene.add_item(self._rubber_band)
        else:

            # If ctrl is held during selection process, add / remove the clip
            # from the current selection appropriately.
            if event.modifiers() & Qt.ControlModifier:
                select_elements = self.app().doc.selected_elements.copy()
                if item.element() in select_elements:
                    select_elements.remove(item.element())
                else:
                    select_elements.add(item.element())
            else:
                select_elements = {item.element()}

            # Don't trigger selection change unless something has actually changed.
            if select_elements != self.app().doc.selected_elements:
                commands.select_elements(select_elements)

    def mouse_move_event(self, event):
        if self._rubber_band is not None:
            scene_pos = event.scene_pos()
            delta_pos = scene_pos - self._mouse_origin
            rect = QRectF(self._mouse_origin.x(), self._mouse_origin.y(), delta_pos.x(), delta_pos.y()).normalized()
            self._rubber_band.set_rect(rect)

    def mouse_release_event(self, event):
        if self._rubber_band is not None:
            elements = set()
            rubber_band_bb = self._rubber_band.bounding_rect()

            # This doesn't seem to speed things up like I would have expected...
            for item in self.scene.items(rubber_band_bb):
                if item is self._rubber_band:
                    continue
                if rubber_band_bb.contains(item.rubberband_shape()):
                    elements.add(item.element())
            self.scene.remove_item(self._rubber_band)
            self._rubber_band = None
            if elements:
                commands.select_elements(elements)


class MoveGraphicsSceneTool(SelectGraphicsSceneTool):

    # TODO: Not sure how Maya does it - but I think move tool is also a select
    # tool? Then why have a select tool? Just if you like pointing at things, I
    # guess.
    # BUG: If this inherits from move tool then we pick before we translate which
    # stops translating multiple elements.

    # TODO: Boil selection down to nodes, then live update move changes.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._last_scene_pos = None

    def mouse_press_event(self, event):
        super().mouse_press_event(event)
        scene_pos = event.scene_pos()
        item = self.scene.item_at(scene_pos, QTransform())
        if item is not None and item.element().is_selected:
            self._last_scene_pos = scene_pos

    def mouse_move_event(self, event):
        super().mouse_move_event(event)
        if self._last_scene_pos is not None:
            scene_pos = event.scene_pos()
            delta_pos = scene_pos - self._last_scene_pos
            for item in self.scene.items():
                if item.element().is_selected:
                    item.move_by(delta_pos.x(), delta_pos.y())
            self._last_scene_pos = scene_pos

    def mouse_release_event(self, event):
        super().mouse_release_event(event)
        if self._last_scene_pos is not None:
            print('COMMIT MOVE')
        self._last_scene_pos = None


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
