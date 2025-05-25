from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsView


# noinspection PyUnresolvedReferences
from __feature__ import snake_case


class GraphicsView(QGraphicsView):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_mouse_tracking(True)

        # TODO: Auto scale to fit content.
        self.scale(0.03, 0.03)

        self._start_screen_pos = None

    def scale(self, *args, **kwargs):
        super().scale(*args, **kwargs)

        for item in self.scene().items():
            item.prepare_geometry_change()

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
