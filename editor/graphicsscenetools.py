from PySide6.QtCore import QCoreApplication, Qt, QRectF
from PySide6.QtGui import QTransform, QPen, QColorConstants, QPolygonF
from PySide6.QtWidgets import QGraphicsScene, QApplication

from editor import commands
from editor.content import EditorWall
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
