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

        modifiers = event.modifiers()
        add = modifiers & Qt.ShiftModifier
        toggle = modifiers & Qt.ControlModifier

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

        scene_pos = event.scene_pos()
        item = self.scene.item_at(scene_pos, QTransform())
        if item is not None and item.element().is_selected:
            self._last_scene_pos = scene_pos
        else:
            super().mouse_press_event(event)

    def mouse_move_event(self, event):

        if self._last_scene_pos is not None:
            scene_pos = event.scene_pos()
            delta_pos = scene_pos - self._last_scene_pos
            for item in self.scene.items():
                if item is self._rubber_band:
                    continue
                if item.element().is_selected:
                    item.move_by(delta_pos.x(), delta_pos.y())
                    item.invalidate_shapes()
            self._last_scene_pos = scene_pos
        else:
            super().mouse_move_event(event)

    def mouse_release_event(self, event):
        #super().mouse_release_event(event)

        #print('self._last_scene_pos:', self._last_scene_pos)
        if self._last_scene_pos is not None:
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
