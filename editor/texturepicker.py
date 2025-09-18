from typing import Any

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QComboBox, QListView

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


class TextureComboBox(QComboBox):

    def __init__(self, icons: dict[Any, QIcon], *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.icons = icons
        self.set_icon_size(QSize(32, 32))

        # Add textures as items with icons.
        for pid, icon in icons.items():
            self.add_item(icon, '')

        view = QListView()
        icon_size = 32
        horizontal_padding = 1
        view.set_grid_size(QSize(icon_size + horizontal_padding, icon_size))

        view.set_view_mode(QListView.IconMode)
        view.set_resize_mode(QListView.ResizeMode.Adjust)
        self.set_view(view)

    def get_current_icon(self):
        index = self.current_index()
        return list(self.icons.keys())[index]

    def set_current_icon(self, value):
        if value not in self.icons.keys():
            return
        index = list(self.icons.keys()).index(value)
        self.set_current_index(index)
