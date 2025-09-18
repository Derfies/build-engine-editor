import argparse
import logging
import sys
from dataclasses import asdict, fields
from pathlib import Path

import marshmallow_dataclass
import qdarktheme
from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import QDockWidget, QFileDialog, QVBoxLayout, QWidget

from adaptors.manager import AdaptorManager
from applicationframework.application import Application
from applicationframework.document import Document
from applicationframework.mainwindow import MainWindow as MainWindowBase
from editor import commands
from editor.clipboard import Clipboard
from editor.constants import MapFormat, ModalTool, SelectionMode
from editor.document import Document
from editor.editorpropertygrid import PropertyGrid
from editor.graph import Graph
from editor.graphicsscene import GraphicsScene
from editor.graphicsview import GraphicsView
from editor.mapio import build, doom, gexf, fallenaces, marathon
from editor.preferencesdialog import PreferencesDialog
from editor.settings import (
    ColourSettings,
    GeneralSettings,
    GridSettings,
    HotkeySettings,
)
from editor.texture import Texture
from editor.updateflag import UpdateFlag
from editor.viewport import Viewport

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


logger = logging.getLogger(__name__)


DEFAULT_COMPANY_NAME = 'Enron'
DEFAULT_APP_NAME = 'Build Engine Map Editor'

# TODO: Replace with adaptors.
IMPORTERS = {
    MapFormat.BLOOD: build.import_build,
    MapFormat.DOOM: doom.import_doom,
    MapFormat.DUKE_3D: build.import_build,
    MapFormat.MARATHON: marathon.import_marathon,
}
EXPORTERS = {
    MapFormat.BLOOD: build.export_build,
    MapFormat.DOOM: doom.export_doom,
    MapFormat.DUKE_3D: build.export_build,
    MapFormat.FALLEN_ACES: fallenaces.export_fallen_aces,
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
        self.app().adaptor_manager = AdaptorManager()
        self.app().held_keys = set()

        super().__init__(*args, **kwargs)

        self.clipboard = Clipboard()

        self.create_tool_bar()
        self.scene = GraphicsScene()
        self.view_2d = GraphicsView(self.scene)
        self.view_3d = Viewport()
        self.property_grid = PropertyGrid()
        self.property_grid.model().dataChanged.connect(self.on_data_changed)

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

        dataclasses = {
            'general_settings': self.app().general_settings,
            'colour_settings': self.app().colour_settings,
            'grid_settings': self.app().grid_settings,
            'hotkey_settings': self.app().hotkey_settings,
            'adaptors': self.app().adaptor_manager.settings,
        } | {
            f'{adaptor.name}_adaptor_settings': adaptor.settings
            for adaptor in self.app().adaptor_manager.adaptors.values()
        }
        for name, dataclass in dataclasses.items():
            self.app().preferences_manager.register_dataclass(name, dataclass)

        self.select_action.set_checked(True)
        self.no_filter_action.set_checked(True)
        self.on_tool_action_group()
        self.on_select_action_group()

        # Load all window / settings preferences.
        self.app().preferences_manager.load()

    def show_event(self, event):
        """
        Need to call global update *after* the window has been shown as this is
        what causes initializeGL to be called, and some of the code there cannot
        be called any earlier.

        """
        super().show_event(event)

        self.app().doc.updated(dirty=False)

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
        self.create_edges_action = QAction(self.get_icon('edge--plus', icons_path=self.local_icons_path), '&Create Edges', self)
        self.create_edges_action.set_data(ModalTool.CREATE_EDGES)
        self.create_edges_action.set_checkable(True)
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
        self.remove_action = QAction(self.get_icon('minus', icons_path=self.local_icons_path), '&Remove', self)
        self.delete_action = QAction(self.get_icon('cross', icons_path=self.local_icons_path), '&Delete',self)
        self.play_actions = []
        for adaptor in self.app().adaptor_manager.adaptors.values():
            exe_name = Path(adaptor.settings.exe_path or '').stem
            action = QAction(self.get_icon(adaptor.icon_name, icons_path=self.local_icons_path), f'&Play In {exe_name.capitalize()}', self)
            action.set_data({'adaptor': adaptor})
            self.play_actions.append(action)

        # Tool action group.
        self.tool_action_group = QActionGroup(self)
        self.tool_action_group.set_exclusive(True)
        self.tool_action_group.add_action(self.select_action)
        self.tool_action_group.add_action(self.move_action)
        self.tool_action_group.add_action(self.rotate_action)
        self.tool_action_group.add_action(self.scale_action)
        self.tool_action_group.add_action(self.create_node_action)
        self.tool_action_group.add_action(self.create_edges_action)
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
        self.delete_action.triggered.connect(self.delete)
        for action in self.play_actions:
            adaptor = action.data()['adaptor']
            action.triggered.connect(adaptor.play)

    def connect_settings_hotkeys(self):

        # Tool actions.
        hotkeys: HotkeySettings = self.app().hotkey_settings
        self.select_action.set_shortcut(QKeySequence(hotkeys.select))
        self.move_action.set_shortcut(QKeySequence(hotkeys.move))
        self.rotate_action.set_shortcut(QKeySequence(hotkeys.rotate))
        self.scale_action.set_shortcut(QKeySequence(hotkeys.scale))

        # Select actions.
        self.no_filter_action.set_shortcut(hotkeys.no_filter)
        self.select_node_action.set_shortcut(hotkeys.select_node)
        self.select_edge_action.set_shortcut(hotkeys.select_edge)
        self.select_poly_action.set_shortcut(hotkeys.select_poly)

        # Misc actions.
        self.join_edges_action.set_shortcut(hotkeys.join_edges)
        self.split_edges_action.set_shortcut(hotkeys.split_edges)
        self.frame_selection_action.set_shortcut(hotkeys.frame_selection)
        self.remove_action.set_shortcut(hotkeys.remove)
        self.delete_action.set_shortcut(hotkeys.delete)

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
        self.edit_menu.add_action(self.delete_action)
        self.edit_menu.add_separator()
        self.edit_menu.add_action(self.show_preferences_action)

    def create_tool_bar(self):
        tool_bar = self.tool_bar()

        tool_bar.add_action(self.select_action)
        tool_bar.add_action(self.move_action)
        tool_bar.add_action(self.rotate_action)
        tool_bar.add_action(self.scale_action)
        tool_bar.add_action(self.create_node_action)
        tool_bar.add_action(self.create_edges_action)
        tool_bar.add_action(self.create_polygon_action)
        tool_bar.add_action(self.create_freeform_polygon_action)
        tool_bar.add_action(self.split_face_action)
        tool_bar.add_action(self.slice_action)
        tool_bar.add_separator()
        tool_bar.add_action(self.join_edges_action)
        tool_bar.add_action(self.split_edges_action)
        tool_bar.add_action(self.frame_selection_action)
        tool_bar.add_action(self.remove_action)
        tool_bar.add_action(self.delete_action)
        tool_bar.add_separator()
        tool_bar.add_action(self.no_filter_action)
        tool_bar.add_action(self.select_node_action)
        tool_bar.add_action(self.select_edge_action)
        tool_bar.add_action(self.select_poly_action)
        tool_bar.add_separator()
        for action in self.play_actions:
            tool_bar.add_action(action)

    def create_document(self, file_path: str = None) -> Document:
        content = Graph(foo=True)

        # content.add_node_attribute_definition('x', 0)
        # content.add_node_attribute_definition('y', 0)
        # content.add_node_attribute_definition('bar', 2)
        # content.add_edge_attribute_definition('baz', 3.0)
        # content.add_face_attribute_definition('qux', 'four')

        # TODO: Move this somewhere else / add method of indirection.
        for attr_name, attr_default in {
            'cstat': 0,
            'pal': 0,
            'shade': 0,
            'xrepeat': 0,
            'yrepeat': 0,
            'xpanning': 0,
            'ypanning': 0,
            'lotag': 0,
            'hitag': 0,
            'extra': -1,
            'low_tex': Texture(0),
            'mid_tex': Texture(0),
            'top_tex': Texture(0),
        }.items():
            content.add_edge_attribute_definition(attr_name, attr_default)

        for attr_name, attr_default in {
            'ceilingz': 0,
            'floorz': 0,
            'ceilingstat': 0,
            'floorstat': 0,
            'ceilingheinum': 0,
            'ceilingshade': 0,
            'ceilingpal': 0,
            'ceilingxpanning': 0,
            'ceilingypanning': 0,
            'floorheinum': 0,
            'floorshade': 0,
            'floorpal': 0,
            'floorxpanning': 0,
            'floorypanning': 0,
            'visibility': 0,
            'filler': 0,
            'lotag': 0,
            'hitag': 0,
            'extra': -1,
            'floor_tex': Texture(0),
            'ceiling_tex': Texture(0),
        }.items():
            content.add_face_attribute_definition(attr_name, attr_default)

        # Sensible default values.
        content.add_edge_attribute_definition('shade', 1)
        content.add_edge_attribute_definition('xrepeat', 32)
        content.add_edge_attribute_definition('yrepeat', 32)
        content.add_face_attribute_definition('floorz', 0)
        content.add_face_attribute_definition('ceilingz', 1024)
        content.add_face_attribute_definition('ceilingshade', 0.9)
        content.add_face_attribute_definition('floorshade', 0.9)

        # For rooms
        #content.add_edge_attribute_definition('door', False)

        return Document(file_path, content, UpdateFlag)

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
            'adaptors': self.app().adaptor_manager.settings,
        } | {
            adaptor.name: adaptor.settings
            for adaptor in self.app().adaptor_manager.adaptors.values()
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
        # NOTE: Don't use rehydrated dataclass instances - keep original instance
        # and change fields in place.
        for name, dataclass in dataclasses.items():
            schema = marshmallow_dataclass.class_schema(dataclass.__class__)()
            new_dataclass = schema.load(dialog.preferences[name])
            for field in fields(new_dataclass):
                setattr(dataclass, field.name, getattr(new_dataclass, field.name))

        # If any of the wad file settings have changed, raise that specific flag
        # in order to reload those assets (which is expensive).
        # TODO: Replace with adaptors.
        flags = UpdateFlag.SETTINGS
        if any([
            preferences[adaptor.name] != asdict(adaptor.settings)
            for adaptor in self.app().adaptor_manager.adaptors.values()
        ]) or preferences['adaptors'] != asdict(self.app().adaptor_manager.settings):
            flags |= UpdateFlag.ADAPTOR_TEXTURES

        # Don't treat modification of prefs as a content change.
        self.app().doc.updated(flags, dirty=False)

    def remove(self):
        commands.remove_elements(self.app().doc.selected_elements)

    def delete(self):
        commands.delete_elements(*self.app().doc.selected_elements)

    def join_edges(self):
        commands.join_edges(*self.app().doc.selected_edges)

    def split_edges(self):
        print('split')

    def on_data_changed(self, index: QModelIndex):
        prop = index.internal_pointer()
        commands.set_attributes(prop.object(), prop.name(), prop.value())

    def frame_selection(self):

        # Gross. We obviously need to keep better track of the mapping between
        # items and elements, but then items can change when we do a full scene
        # rebuild.
        # TODO: Allow framing independently on either viewport.
        items = [
            item
            for item in self.scene.items()
            if item.element().is_selected
        ]
        items = items or self.scene.items()
        self.view_2d.frame(items)
        self.view_3d.frame(items)

    def update_event(self, doc: Document, flags: UpdateFlag):
        """
        Run on initial app load (all flags called from init) or on other update
        events incuding the preferences panel being dismissed.

        """
        super().update_event(doc, flags)

        # Settings may have changed - rebind hotkeys.
        if UpdateFlag.SETTINGS in flags:
            self.connect_settings_hotkeys()

    def copy_event(self):
        self.clipboard.copy(self.app().doc.selected_elements)

    def paste_event(self):
        if self.clipboard.is_empty():
            logger.info('Clipboard is empty')
            return
        self.clipboard.paste()

    def import_event(self):

        # TODO: Need to build list of exporters from adaptors *and* standalone functions...?
        file_formats = ';;'.join([fmt.value for fmt in MapFormat])
        file_path, file_format = QFileDialog.get_open_file_name(caption='Import', filter=file_formats)
        if not file_path:
            return False

        map_format = MapFormat(file_format)
        IMPORTERS[map_format](self.app().doc.content, file_path, MapFormat(file_format))
        self.app().doc.updated(self.app().doc.default_flags & ~UpdateFlag.ADAPTOR_TEXTURES, dirty=True)

    def export_event(self):
        file_formats = ';;'.join([fmt.value for fmt in MapFormat])
        file_path, file_format = QFileDialog.get_save_file_name(caption='Export', filter=file_formats)
        if not file_path:
            return False

        map_format = MapFormat(file_format)
        EXPORTERS[map_format](self.app().doc.content, file_path, MapFormat(file_format))


if __name__ == '__main__':

    # Allow setting of log level from argv.
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Set the logging level (default: INFO)'
    )
    args = parser.parse_args()
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logging.basicConfig(level=log_level)

    app = Application(DEFAULT_COMPANY_NAME, DEFAULT_APP_NAME, sys.argv)
    qdarktheme.setup_theme()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
