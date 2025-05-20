import logging
import sys
from enum import Flag

import qdarktheme
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsView, QSplitter, QVBoxLayout, QWidget

from applicationframework.application import Application
from applicationframework.document import Document
from applicationframework.mainwindow import MainWindow as MainWindowBase
from content import Content
from graphicsscene import GraphicsScene
from propertygrid.widget import Widget as PropertyGrid

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


logger = logging.getLogger(__name__)


DEFAULT_COMPANY_NAME = 'Enron'
DEFAULT_APP_NAME = 'Application Framework'


class UpdateFlag(Flag):

    pass


class View(QGraphicsView):

    def wheel_event(self, event):
        if event.angle_delta().y() > 0:
            factor = 1.25
        else:
            factor = 0.8
        self.scale(factor, factor)


class MainWindow(MainWindowBase):

    """
    https://stackoverflow.com/questions/2173146/how-can-i-draw-nodes-and-edges-in-pyqt

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.scene = GraphicsScene()
        self.view = View(self.scene)

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

        self.view.fit_in_view(self.scene.scene_rect(), Qt.AspectRatioMode.KeepAspectRatio)

        #self.open_event(r'C:\Program Files (x86)\Steam\steamapps\common\Duke Nukem 3D\gameroot\maps\LL-SEWER.MAP')
        self.app().doc.updated(dirty=False)

    def create_document(self, file_path: str = None) -> Document:
        return Document(file_path, Content(), UpdateFlag)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    app = Application(DEFAULT_COMPANY_NAME, DEFAULT_APP_NAME, sys.argv)
    qdarktheme.setup_theme()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
