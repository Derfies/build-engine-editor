import logging
import sys
from pathlib import Path

import qdarktheme
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QIcon
from PySide6.QtWidgets import QSplitter, QToolBar, QVBoxLayout, QWidget

from applicationframework.application import Application
from applicationframework.document import Document
from applicationframework.mainwindow import MainWindow as MainWindowBase
from editor.constants import ModalTool
from editor.content import Content
from editor.editorpropertygrid import PropertyGrid
from editor.graphicsscene import GraphicsScene
from editor.graphicsview import GraphicsView
from editor.mapdocument import MapDocument
from editor.updateflag import UpdateFlag

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


logger = logging.getLogger(__name__)


DEFAULT_COMPANY_NAME = 'Enron'
DEFAULT_APP_NAME = 'Build Engine Map Editor'


class MainWindow(MainWindowBase):

    """
    https://stackoverflow.com/questions/2173146/how-can-i-draw-nodes-and-edges-in-pyqt

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.create_tool_bar()

        self.scene = GraphicsScene()#self.tool_group)
        self.view = GraphicsView(self.scene)
        self.property_grid = PropertyGrid()

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.add_widget(self.view)
        self.splitter.add_widget(self.property_grid)

        self.layout = QVBoxLayout(self)
        self.layout.add_widget(self.splitter)

        self.window = QWidget()
        self.window.set_layout(self.layout)
        self.set_central_widget(self.window)

        self.app().preferences_manager.register_widget('main_splitter', self.splitter)

        self.select_action.set_checked(True)
        self.scene.set_modal_tool(ModalTool.SELECT)

        #self.open_event(r'C:\Program Files (x86)\Steam\steamapps\common\Duke Nukem 3D\gameroot\maps\LL-SEWER.MAP')
        self.open_event(r'C:\Program Files (x86)\Steam\steamapps\common\Duke Nukem 3D\gameroot\maps\1.MAP')
        #self.app().doc.updated(dirty=False)

    @property
    def local_icons_path(self) -> Path:
        return Path(__file__).parent.joinpath('data', 'icons')

    def get_local_icon(self, file_name: str) -> QIcon:
        return QIcon(str(self.local_icons_path.joinpath(file_name)))

    def create_actions(self):
        super().create_actions()

        # Tool actions.
        self.select_action = QAction(self.get_local_icon('cursor'), '&Select', self)
        self.select_action.set_data(ModalTool.SELECT)
        self.select_action.set_checkable(True)
        self.draw_sector_action = QAction(self.get_local_icon('layer-shape-polygon.png'), '&Draw Sector', self)
        self.draw_sector_action.set_data(ModalTool.DRAW_SECTOR)
        self.draw_sector_action.set_checkable(True)

        # Tool group.
        self.tool_group = QActionGroup(self)
        self.tool_group.set_exclusive(True)
        self.tool_group.add_action(self.select_action)
        self.tool_group.add_action(self.draw_sector_action)
        self.tool_group.triggered.connect(self.on_tool_group_changed)

    def create_tool_bar(self):
        tool_bar = QToolBar()
        self.add_tool_bar(tool_bar)

        tool_bar.add_action(self.select_action)
        tool_bar.add_action(self.draw_sector_action)

    def create_document(self, file_path: str = None) -> Document:
        return MapDocument(file_path, Content(), UpdateFlag)

    def on_tool_group_changed(self):
        action = self.tool_group.checked_action().data()
        self.scene.set_modal_tool(action)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    app = Application(DEFAULT_COMPANY_NAME, DEFAULT_APP_NAME, sys.argv)
    qdarktheme.setup_theme()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
