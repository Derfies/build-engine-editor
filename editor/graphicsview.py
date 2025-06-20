from PySide6.QtCore import Qt, QRectF
from PySide6.QtWidgets import QGraphicsItem, QGraphicsView


# noinspection PyUnresolvedReferences
from __feature__ import snake_case


class GraphicsView(QGraphicsView):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        #self.xform = None

        self.set_mouse_tracking(True)

        # TODO: Auto scale to fit content.
        #self.scale(0.03, 0.03)
        self.scale(0.3, 0.3)

        self._start_screen_pos = None

    def scale(self, *args, **kwargs):
        super().scale(*args, **kwargs)

        # Hax
        for item in self.scene().items():
            if hasattr(item, 'invalidate_shapes'):
                item.invalidate_shapes()

        # TODO: Just encountered a scale-adjusting crash because we tried to
        # access this from a graphics item, which apparantly is not good practice.
        # Doing it here seems to be a better bet.
        self.scene().xform = self.scene().views()[0].transform().m11()

    def mouse_press_event(self, event):
        if event.button() == Qt.MiddleButton:
            screen_pos = event.screen_pos()
            self._start_screen_pos = screen_pos
            self.set_cursor(Qt.ClosedHandCursor)
            self.set_interactive(False)
        else:
            super().mouse_press_event(event)

    def mouse_move_event(self, event):
        if self._start_screen_pos is not None:
            screen_pos = event.screen_pos()
            delta_pos = screen_pos - self._start_screen_pos
            self.horizontal_scroll_bar().set_value(self.horizontal_scroll_bar().value() - delta_pos.x())
            self.vertical_scroll_bar().set_value(self.vertical_scroll_bar().value() - delta_pos.y())
            self._start_screen_pos = screen_pos
        else:
            super().mouse_move_event(event)

    def mouse_release_event(self, event):
        if event.button() == Qt.MiddleButton:
            self._start_screen_pos = None
            self.set_cursor(Qt.ArrowCursor)
            self.set_interactive(True)
        else:
            super().mouse_release_event(event)

    def wheel_event(self, event):
        if event.angle_delta().y() > 0:
            factor = 1.25
        else:
            factor = 0.8
        self.scale(factor, factor)

    def frame(self, items: list[QGraphicsItem]):
        bounding_rect = QRectF()
        for item in items:
            bounding_rect = bounding_rect.united(item.scene_bounding_rect())
        self.fit_in_view(bounding_rect, Qt.KeepAspectRatio)
