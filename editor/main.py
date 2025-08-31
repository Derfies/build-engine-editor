import logging
import subprocess
import sys
from dataclasses import fields
from pathlib import Path

import marshmallow_dataclass
import qdarktheme
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import QDockWidget, QFileDialog, QVBoxLayout, QWidget

from applicationframework.application import Application
from applicationframework.document import Document
from applicationframework.mainwindow import MainWindow as MainWindowBase
from editor import commands
from editor.constants import EDGE_DEFAULT, FACE_DEFAULT
from editor.constants import MapFormat, ModalTool, SelectionMode
from editor.editorpropertygrid import PropertyGrid
from editor.graph import Graph
from editor.graphicsscene import GraphicsScene
from editor.graphicsview import GraphicsView
from editor.mapdocument import MapDocument
from editor.mapio import build
from editor.mapio import doom
from editor.mapio import gexf
from editor.preferencesdialog import PreferencesDialog
from editor.settings import ColourSettings, GeneralSettings, GridSettings, HotkeySettings, PlaySettings
from editor.updateflag import UpdateFlag
from editor.viewport import Viewport
from propertygrid.model import ModelEvent

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


logger = logging.getLogger(__name__)


DEFAULT_COMPANY_NAME = 'Enron'
DEFAULT_APP_NAME = 'Build Engine Map Editor'
IMPORTERS = {
    MapFormat.BLOOD: build.import_build,
    MapFormat.DUKE_3D: build.import_build,
    MapFormat.DOOM: doom.import_doom,
}
EXPORTERS = {
    MapFormat.BLOOD: build.export_build,
    MapFormat.DUKE_3D: build.export_build,
    MapFormat.GEXF: gexf.export_gexf,
}


class MainWindow(MainWindowBase):

    """
    https://stackoverflow.com/questions/2173146/how-can-i-draw-nodes-and-edges-in-pyqt

    """

    def __init__(self, *args, **kwargs):

        # TODO: Create custom app instance.
        self.app().general_settings = GeneralSettings()
        self.app().colour_settings = ColourSettings()
        self.app().grid_settings = GridSettings()
        self.app().hotkey_settings = HotkeySettings()
        self.app().play_settings = PlaySettings()
        self.app().held_keys = set()

        super().__init__(*args, **kwargs)

        self.create_tool_bar()
        self.scene = GraphicsScene()
        self.view_2d = GraphicsView(self.scene)
        self.view_3d = Viewport()
        self.property_grid = PropertyGrid()
        self.property_grid.model().data_changed.connect(self.on_data_changed)

        # Moving openGl widget sometimes crashes :/
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.set_contents_margins(0, 0, 0, 0)
        layout.add_widget(self.view_3d)

        dock1 = QDockWidget('2D View', self)
        dock2 = QDockWidget('3D View', self)
        dock3 = QDockWidget('Properties', self)

        dock1.set_object_name('dock1')
        dock2.set_object_name('dock2')
        dock3.set_object_name('dock3')

        dock1.set_widget(self.view_2d)
        dock2.set_widget(wrapper)
        dock3.set_widget(self.property_grid)

        self.set_dock_nesting_enabled(True)
        self.add_dock_widget(Qt.LeftDockWidgetArea, dock1)
        self.add_dock_widget(Qt.RightDockWidgetArea, dock2)
        self.add_dock_widget(Qt.RightDockWidgetArea, dock3)
        self.split_dock_widget(dock1, dock3, Qt.Horizontal)
        self.tabify_dock_widget(dock1, dock2)
        dock1.raise_()
        self.resize_docks([dock1, dock3], [4, 1], Qt.Horizontal)

        for name, dataclass in {
            'general_settings': self.app().general_settings,
            'colour_settings': self.app().colour_settings,
            'grid_settings': self.app().grid_settings,
            'hotkey_settings': self.app().hotkey_settings,
            'play_settings': self.app().play_settings,
        }.items():
            self.app().preferences_manager.register_dataclass(name, dataclass)

        self.select_action.set_checked(True)
        self.no_filter_action.set_checked(True)
        self.on_tool_action_group()
        self.on_select_action_group()

        #self.open_event(r'C:\Users\Jamie Davies\Documents\git\build-engine-editor\test.map')
        #self.open_event(r'C:\Program Files (x86)\Steam\steamapps\common\Duke Nukem 3D\gameroot\maps\LL-SEWER.MAP')
        #self.open_event(r'C:\Program Files (x86)\Steam\steamapps\common\Duke Nukem 3D\gameroot\maps\1.MAP')
        #self.open_event(r'C:\Users\Jamie Davies\Documents\git\build-engine-editor\editor\tests\data\2_squares.map')
        #self.open_event(r'C:\Users\Jamie Davies\Documents\git\build-engine-editor\test5.map')

        #self.import_event()

        #mapio.doom.import_doom(self.app().doc.content, r'C:\Program Files (x86)\GOG Galaxy\Games\DOOM\DOOM.WAD', MapFormat.DOOM)

        self.app().doc.updated(dirty=False)



        #self.app().doc.file_path = r'C:\Program Files (x86)\Steam\steamapps\common\Duke Nukem 3D\gameroot\maps\out.map'
        #self.app().doc.save()

    def key_press_event(self, event):

        # TODO: Might not be very robust, but we want to be able to match with
        # hotkey settings.
        self.app().held_keys.add(event.text())

    def key_release_event(self, event):
        self.app().held_keys.discard(event.text())

    @property
    def local_icons_path(self) -> Path:
        return Path(__file__).parent.joinpath('data', 'icons')

    def create_actions(self):
        super().create_actions()

        # File actions.
        self.import_action = QAction(self.get_icon('arrow-transition-270.png', icons_path=self.local_icons_path), '&Import...', self)
        self.export_action = QAction(self.get_icon('arrow-transition.png', icons_path=self.local_icons_path), '&Export...', self)

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
        self.create_node_action = QAction(self.get_icon('node--plus', icons_path=self.local_icons_path), '&Create Node', self)
        self.create_node_action.set_data(ModalTool.CREATE_NODE)
        self.create_node_action.set_checkable(True)
        self.create_polygon_action = QAction(self.get_icon('layer-shape', icons_path=self.local_icons_path), '&Create Polygon', self)
        self.create_polygon_action.set_data(ModalTool.CREATE_POLYGON)
        self.create_polygon_action.set_checkable(True)
        self.create_freeform_polygon_action = QAction(self.get_icon('layer-shape-polygon', icons_path=self.local_icons_path), '&Create Freeform Polygon', self)
        self.create_freeform_polygon_action.set_data(ModalTool.CREATE_FREEFORM_POLYGON)
        self.create_freeform_polygon_action.set_checkable(True)
        self.split_face_action = QAction(self.get_icon('face-split', icons_path=self.local_icons_path), '&Split Face', self)
        self.split_face_action.set_data(ModalTool.SPLIT_FACES)
        self.split_face_action.set_checkable(True)
        self.slice_action = QAction(self.get_icon('cutter', icons_path=self.local_icons_path), '&Split Face', self)
        self.slice_action.set_data(ModalTool.SLICE_FACES)
        self.slice_action.set_checkable(True)

        # Select actions.
        self.no_filter_action = QAction(self.get_icon('funnel--cross', icons_path=self.local_icons_path), '&No Selection Filter', self)
        self.no_filter_action.set_data(SelectionMode.ALL)
        self.no_filter_action.set_checkable(True)
        self.select_node_action = QAction(self.get_icon('layer-select-point', icons_path=self.local_icons_path), '&Select Node', self)
        self.select_node_action.set_data(SelectionMode.NODE)
        self.select_node_action.set_checkable(True)
        self.select_edge_action = QAction(self.get_icon('layer-select-line', icons_path=self.local_icons_path), '&Select Edge', self)
        self.select_edge_action.set_data(SelectionMode.EDGE)
        self.select_edge_action.set_checkable(True)
        self.select_poly_action = QAction(self.get_icon('layer-select-polygon', icons_path=self.local_icons_path), '&Select Poly', self)
        self.select_poly_action.set_data(SelectionMode.FACE)
        self.select_poly_action.set_checkable(True)

        # Misc actions.
        self.join_edges_action = QAction( self.get_icon('join-edge', icons_path=self.local_icons_path), '&Join Edges', self)
        self.split_edges_action = QAction(self.get_icon('split-edge', icons_path=self.local_icons_path),'&Split Edges', self)
        self.frame_selection_action = QAction(self.get_icon('image-instagram-frame', icons_path=self.local_icons_path), '&Frame Selection', self)
        self.remove_action = QAction(self.get_icon('cross', icons_path=self.local_icons_path), '&Remove', self)
        self.play_in_eduke32_action = QAction(self.get_icon('eduke32', icons_path=self.local_icons_path), '&Play In EDuke32', self)
        self.play_in_nblood_action = QAction(self.get_icon('nblood', icons_path=self.local_icons_path), '&Play In Nblood', self)

        # Tool action group.
        self.tool_action_group = QActionGroup(self)
        self.tool_action_group.set_exclusive(True)
        self.tool_action_group.add_action(self.select_action)
        self.tool_action_group.add_action(self.move_action)
        self.tool_action_group.add_action(self.rotate_action)
        self.tool_action_group.add_action(self.scale_action)
        self.tool_action_group.add_action(self.create_node_action)
        self.tool_action_group.add_action(self.create_polygon_action)
        self.tool_action_group.add_action(self.create_freeform_polygon_action)
        self.tool_action_group.add_action(self.split_face_action)
        self.tool_action_group.add_action(self.slice_action)
        self.tool_action_group.triggered.connect(self.on_tool_action_group)

        # Select action group.
        self.select_action_group = QActionGroup(self)
        self.select_action_group.set_exclusive(True)
        self.select_action_group.add_action(self.no_filter_action)
        self.select_action_group.add_action(self.select_node_action)
        self.select_action_group.add_action(self.select_edge_action)
        self.select_action_group.add_action(self.select_poly_action)
        self.select_action_group.triggered.connect(self.on_select_action_group)

    def connect_actions(self):
        super().connect_actions()

        # File actions.
        self.import_action.triggered.connect(self.import_event)
        self.export_action.triggered.connect(self.export_event)

        # Edit actions.
        self.show_preferences_action.triggered.connect(self.show_preferences)

        # Misc actions.
        self.join_edges_action.triggered.connect(self.join_edges)
        self.split_edges_action.triggered.connect(self.split_edges)
        self.frame_selection_action.triggered.connect(self.frame_selection)
        self.remove_action.triggered.connect(self.remove)
        self.play_in_eduke32_action.triggered.connect(lambda: self.play(self.app().play_settings.eduke32_path, MapFormat.DUKE_3D))
        self.play_in_nblood_action.triggered.connect(lambda: self.play(self.app().play_settings.nblood_path, MapFormat.BLOOD))

    def connect_hotkeys(self):
        super().connect_hotkeys()

        # Tool actions.
        hotkeys: HotkeySettings = self.app().hotkey_settings
        self.select_action.set_shortcut(QKeySequence(hotkeys.select))
        self.move_action.set_shortcut(QKeySequence(hotkeys.move))
        self.rotate_action.set_shortcut(QKeySequence(hotkeys.rotate))
        self.scale_action.set_shortcut(QKeySequence(hotkeys.scale))

        # Misc actions.
        self.join_edges_action.set_shortcut(hotkeys.join_edges)
        self.split_edges_action.set_shortcut(hotkeys.split_edges)
        self.frame_selection_action.set_shortcut(hotkeys.frame_selection)
        self.remove_action.set_shortcut(hotkeys.remove)

    def create_menu_bar(self):
        super().create_menu_bar()

        # File menu.
        self.file_menu.insert_action(self.exit_action, self.import_action)
        self.file_menu.insert_action(self.exit_action, self.export_action)
        self.file_menu.insert_separator(self.exit_action)

        # Edit actions.
        self.edit_menu.add_separator()
        self.edit_menu.add_action(self.join_edges_action)
        self.edit_menu.add_action(self.split_edges_action)
        self.edit_menu.add_action(self.frame_selection_action)
        self.edit_menu.add_action(self.remove_action)
        self.edit_menu.add_separator()
        self.edit_menu.add_action(self.show_preferences_action)

    def create_tool_bar(self):
        tool_bar = self.tool_bar()

        tool_bar.add_action(self.select_action)
        tool_bar.add_action(self.move_action)
        tool_bar.add_action(self.rotate_action)
        tool_bar.add_action(self.scale_action)
        tool_bar.add_action(self.create_node_action)
        tool_bar.add_action(self.create_polygon_action)
        tool_bar.add_action(self.create_freeform_polygon_action)
        tool_bar.add_action(self.split_face_action)
        tool_bar.add_action(self.slice_action)
        tool_bar.add_separator()
        tool_bar.add_action(self.join_edges_action)
        tool_bar.add_action(self.split_edges_action)
        tool_bar.add_action(self.frame_selection_action)
        tool_bar.add_action(self.remove_action)
        tool_bar.add_separator()
        tool_bar.add_action(self.no_filter_action)
        tool_bar.add_action(self.select_node_action)
        tool_bar.add_action(self.select_edge_action)
        tool_bar.add_action(self.select_poly_action)
        tool_bar.add_separator()
        tool_bar.add_action(self.play_in_eduke32_action)
        tool_bar.add_action(self.play_in_nblood_action)

    def create_document(self, file_path: str = None) -> Document:
        content = Graph(foo=True)

        # content.add_node_attribute_definition('x', 0)
        # content.add_node_attribute_definition('y', 0)
        # content.add_node_attribute_definition('bar', 2)
        # content.add_edge_attribute_definition('baz', 3.0)
        # content.add_face_attribute_definition('qux', 'four')

        # TODO: Move this somewhere else / add method of indirection.
        from gameengines.build.map import Sector, Wall

        for field in fields(Wall):
            content.add_edge_attribute_definition(field.name, field.default)

        for field in fields(Sector):
            content.add_face_attribute_definition(field.name, field.default)

        # Sensible default values.
        content.data.graph[EDGE_DEFAULT]['xrepeat'] = 32
        content.data.graph[EDGE_DEFAULT]['yrepeat'] = 32
        content.data.graph[FACE_DEFAULT]['floorz'] = 0
        content.data.graph[FACE_DEFAULT]['ceilingz'] = -1024 * 16

        # For rooms
        #content.add_edge_attribute_definition('door', False)

        return MapDocument(file_path, content, UpdateFlag)

    def on_tool_action_group(self):
        action = self.tool_action_group.checked_action().data()
        self.scene.set_modal_tool(action)

    def on_select_action_group(self):
        action = self.select_action_group.checked_action().data()
        self.scene.set_selection_mode(action)

    def show_preferences(self):

        # Collect settings.
        preferences = {}
        dataclasses = {
            'general': self.app().general_settings,
            'colours': self.app().colour_settings,
            'grid': self.app().grid_settings,
            'hotkeys': self.app().hotkey_settings,
            'play': self.app().play_settings,
        }
        for name, dataclass in dataclasses.items():
            schema = marshmallow_dataclass.class_schema(dataclass.__class__)()
            preferences[name] = schema.dump(dataclass)

        # Show the dialog.
        dialog = PreferencesDialog()
        dialog.load_preferences(preferences)
        if not dialog.exec():
            return

        # Deserialize back to data objects and set.
        for name, dataclass in dataclasses.items():
            for k, v in dialog.preferences[name].items():
                setattr(dataclass, k, v)

        # Don't treat modification of prefs as a content change.
        self.app().doc.updated(UpdateFlag.SETTINGS, dirty=False)

    def remove(self):
        commands.remove_elements(self.app().doc.selected_elements)

    def join_edges(self):
        commands.join_edges(*self.app().doc.selected_edges)

    def split_edges(self):
        print('split')

    def on_data_changed(self, event: ModelEvent):
        commands.set_attribute(event.object(), event.name(), event.value())

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
        self.view_2d.frame(items)

    def play(self, exe_path: str, map_format: MapFormat):

        exe_path = Path(exe_path)
        if not exe_path.exists():
            raise Exception(f'Cannot find executable at: {exe_path}')

        # TODO: Since we're loading an external non-blocking process not sure
        # how to clean up properly here.
        temp_map_path = exe_path.parent.joinpath('out.map')
        build.export_build(self.app().doc.content, temp_map_path, map_format)

        # Launch game executable.
        # TODO: Different build exes might require different args / flags here.
        process = subprocess.Popen(
            [exe_path] + ['-map', 'out.map'],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,  # ensures output is in string format instead of bytes
            cwd=exe_path.parent,
        )

        # Read and print stderr.
        stderr_output, stdout_output = process.communicate()

        print('STDERR:')
        print(stderr_output)

        print('STDOUT:')
        print(stdout_output)

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

    def import_event(self):
        file_formats = ';;'.join([fmt.value for fmt in MapFormat])
        file_path, file_format = QFileDialog.get_open_file_name(caption='Import', filter=file_formats)
        if not file_path:
            return False

        map_format = MapFormat(file_format)
        IMPORTERS[map_format](self.app().doc.content, file_path, MapFormat(file_format))
        self.app().doc.updated(dirty=False)

    def export_event(self):
        file_formats = ';;'.join([fmt.value for fmt in MapFormat])
        file_path, file_format = QFileDialog.get_save_file_name(caption='Export', filter=file_formats)
        if not file_path:
            return False

        map_format = MapFormat(file_format)
        EXPORTERS[map_format](self.app().doc.content, file_path, MapFormat(file_format))


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    app = Application(DEFAULT_COMPANY_NAME, DEFAULT_APP_NAME, sys.argv)
    qdarktheme.setup_theme()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
