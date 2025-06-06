import logging
import sys
from pathlib import Path

import marshmallow_dataclass
import qdarktheme
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from applicationframework.application import Application
from applicationframework.document import Document
from applicationframework.mainwindow import MainWindow as MainWindowBase
from editor.constants import ModalTool, SelectionMode
from editor.editorpropertygrid import PropertyGrid
from editor.graph import Graph
from editor.graphicsscene import GraphicsScene
from editor.graphicsview import GraphicsView
from editor.mapdocument import MapDocument
from editor.preferencesdialog import PreferencesDialog
from editor.settings import ColourSettings, GridSettings, HotkeySettings
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
        self.app().colour_settings = ColourSettings()
        self.app().grid_settings = GridSettings()
        self.app().hotkey_settings = HotkeySettings()

        super().__init__(*args, **kwargs)

        self.create_tool_bar()

        self.scene = GraphicsScene()
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
        self.app().preferences_manager.register_dataclass('colour_settings', self.app().colour_settings)
        self.app().preferences_manager.register_dataclass('grid_settings', self.app().grid_settings)
        self.app().preferences_manager.register_dataclass('hotkey_settings', self.app().hotkey_settings)

        self.select_action.set_checked(True)
        self.select_node_action.set_checked(True)
        self.on_tool_action_group()
        self.on_select_action_group()

        #self.open_event(r'C:\Program Files (x86)\Steam\steamapps\common\Duke Nukem 3D\gameroot\maps\LL-SEWER.MAP')
        #self.open_event(r'C:\Program Files (x86)\Steam\steamapps\common\Duke Nukem 3D\gameroot\maps\1.MAP')
        #self.open_event(r'C:\Users\Jamie Davies\Documents\git\build-engine-editor\editor\tests\data\1_squares.map')
        self.app().doc.updated(dirty=False)

        #self.app().doc.file_path = r'C:\Program Files (x86)\Steam\steamapps\common\Duke Nukem 3D\gameroot\maps\out.map'
        #self.app().doc.save()

    @property
    def local_icons_path(self) -> Path:
        return Path(__file__).parent.joinpath('data', 'icons')

    def create_actions(self):
        super().create_actions()

        # Edit actions.
        # TODO: Should preferences be in base class?
        self.show_preferences_action = QAction(self.get_icon('wrench.png', icons_path=self.local_icons_path), '&Preferences...', self)

        # Tool actions.
        self.select_action = QAction(self.get_icon('cursor', icons_path=self.local_icons_path), '&Select', self)
        self.select_action.set_data(ModalTool.SELECT)
        self.select_action.set_checkable(True)
        self.move_action = QAction(self.get_icon('arrow-move', icons_path=self.local_icons_path),'&Move', self)
        self.move_action.set_data(ModalTool.MOVE)
        self.move_action.set_checkable(True)
        self.rotate_action = QAction(self.get_icon('arrow-circle-double-135', icons_path=self.local_icons_path), '&Rotate', self)
        self.rotate_action.set_data(ModalTool.ROTATE)
        self.rotate_action.set_checkable(True)
        self.scale_action = QAction(self.get_icon('arrow-resize-135', icons_path=self.local_icons_path), '&Select', self)
        self.scale_action.set_data(ModalTool.SCALE)
        self.scale_action.set_checkable(True)
        self.create_poly_action = QAction(self.get_icon('layer-shape', icons_path=self.local_icons_path), '&Draw Poly', self)
        self.create_poly_action.set_data(ModalTool.CREATE_POLY)
        self.create_poly_action.set_checkable(True)
        self.create_freeform_poly_action = QAction(self.get_icon('layer-shape-polygon', icons_path=self.local_icons_path), '&Draw Poly', self)
        self.create_freeform_poly_action.set_data(ModalTool.CREATE_FREEFORM_POLY)
        self.create_freeform_poly_action.set_checkable(True)

        # Select actions.
        self.select_node_action = QAction(self.get_icon('layer-select-point', icons_path=self.local_icons_path), '&Select Node', self)
        self.select_node_action.set_data(SelectionMode.NODE)
        self.select_node_action.set_checkable(True)
        self.select_edge_action = QAction(self.get_icon('layer-select-line', icons_path=self.local_icons_path), '&Select Edge', self)
        self.select_edge_action.set_data(SelectionMode.EDGE)
        self.select_edge_action.set_checkable(True)
        self.select_poly_action = QAction(self.get_icon('layer-select-polygon', icons_path=self.local_icons_path), '&Select Poly', self)
        self.select_poly_action.set_data(SelectionMode.POLY)
        self.select_poly_action.set_checkable(True)

        # Misc actions.
        self.frame_selection_action = QAction(self.get_icon('image-instagram-frame', icons_path=self.local_icons_path), '&Frame Selection', self)

        # Tool action group.
        self.tool_action_group = QActionGroup(self)
        self.tool_action_group.set_exclusive(True)
        self.tool_action_group.add_action(self.select_action)
        self.tool_action_group.add_action(self.move_action)
        self.tool_action_group.add_action(self.rotate_action)
        self.tool_action_group.add_action(self.scale_action)
        self.tool_action_group.add_action(self.create_poly_action)
        self.tool_action_group.add_action(self.create_freeform_poly_action)
        self.tool_action_group.triggered.connect(self.on_tool_action_group)

        # Select action group.
        self.select_action_group = QActionGroup(self)
        self.select_action_group.set_exclusive(True)
        self.select_action_group.add_action(self.select_node_action)
        self.select_action_group.add_action(self.select_edge_action)
        self.select_action_group.add_action(self.select_poly_action)
        self.select_action_group.triggered.connect(self.on_select_action_group)

    def connect_actions(self):
        super().connect_actions()

        # Edit actions.
        self.show_preferences_action.triggered.connect(self.show_preferences)

        # Misc actions.
        self.frame_selection_action.triggered.connect(self.frame_selection)

    def connect_hotkeys(self):
        super().connect_hotkeys()

        # Tool actions.
        hotkeys: HotkeySettings = self.app().hotkey_settings
        self.select_action.set_shortcut(QKeySequence(hotkeys.select))
        self.move_action.set_shortcut(QKeySequence(hotkeys.move))
        self.rotate_action.set_shortcut(QKeySequence(hotkeys.rotate))
        self.scale_action.set_shortcut(QKeySequence(hotkeys.scale))

        # Misc actions.
        self.frame_selection_action.set_shortcut(hotkeys.frame_selection)

    def create_menu_bar(self):
        super().create_menu_bar()

        # Edit actions.
        self.edit_menu.add_separator()
        self.edit_menu.add_action(self.frame_selection_action)
        self.edit_menu.add_separator()
        self.edit_menu.add_action(self.show_preferences_action)

    def create_tool_bar(self):
        tool_bar = self.tool_bar()

        tool_bar.add_action(self.select_action)
        tool_bar.add_action(self.move_action)
        tool_bar.add_action(self.rotate_action)
        tool_bar.add_action(self.scale_action)
        tool_bar.add_action(self.create_poly_action)
        tool_bar.add_action(self.create_freeform_poly_action)
        tool_bar.add_separator()
        tool_bar.add_action(self.select_node_action)
        tool_bar.add_action(self.select_edge_action)
        tool_bar.add_action(self.select_poly_action)

    def create_document(self, file_path: str = None) -> Document:
        return MapDocument(file_path, Graph(), UpdateFlag)

    def on_tool_action_group(self):
        action = self.tool_action_group.checked_action().data()
        self.scene.set_modal_tool(action)

    def on_select_action_group(self):
        action = self.select_action_group.checked_action().data()
        self.scene.set_selection_mode(action)

    def show_preferences(self):

        # Collect settings.
        colour_schema = marshmallow_dataclass.class_schema(ColourSettings)()
        grid_schema = marshmallow_dataclass.class_schema(GridSettings)()
        hotkey_schema = marshmallow_dataclass.class_schema(HotkeySettings)()
        preferences = {
            'colours': colour_schema.dump(self.app().colour_settings),
            'grid': grid_schema.dump(self.app().grid_settings),
            'hotkeys': hotkey_schema.dump(self.app().hotkey_settings),
        }

        # Show the dialog.
        dialog = PreferencesDialog()
        dialog.load_preferences(preferences)
        if not dialog.exec():
            return

        # Deserialize back to data objects and set.
        for k, v in dialog.preferences['colours'].items():
            setattr(self.app().colour_settings, k, v)
        for k, v in dialog.preferences['grid'].items():
            setattr(self.app().grid_settings, k, v)
        for k, v in dialog.preferences['hotkeys'].items():
            setattr(self.app().hotkey_settings, k, v)

        # Don't treat modification of prefs as a content change.
        self.app().doc.updated(UpdateFlag.SETTINGS, dirty=False)

    def frame_selection(self):

        # Gross. We obviously need to keep better track of the mapping between
        # items and elements, but then items can change when we do a full scene
        # rebuild.
        items = [
            item
            for item in self.scene.items()
            if item.element().is_selected
        ]
        items = items or self.scene.items()
        self.view.frame(items)

    def show_event(self, event):
        super().show_event(event)

        # TODO: Think about if there's a cleaner way to do this.
        self.connect_hotkeys()

        # This is a bit of a hack. We need to refresh after preferences are
        # loaded and that gets done during show_event.
        self.app().doc.updated(dirty=False)

    def update_event(self, doc: Document, flags: UpdateFlag):
        super().update_event(doc, flags)

        # TODO: Think about if there's a cleaner way to do this.
        if UpdateFlag.SETTINGS in flags:
            self.connect_hotkeys()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    app = Application(DEFAULT_COMPANY_NAME, DEFAULT_APP_NAME, sys.argv)
    qdarktheme.setup_theme()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
