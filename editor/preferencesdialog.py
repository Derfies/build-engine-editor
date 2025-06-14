from PySide6.QtGui import QColor, QDoubleValidator, QIntValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from applicationframework.preferencesdialog import PreferencesDialog as PreferenceDialogBase, PreferenceWidgetBase


# noinspection PyUnresolvedReferences
from __feature__ import snake_case


class ColourPicker(QWidget):

    """
    TODO: Could be useful. Put in qtextras package.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._colour = QColor()

        self.button = QPushButton()
        self.button.clicked.connect(self.show_colour_dialog)

        layout = QVBoxLayout()
        layout.add_widget(self.button)
        layout.set_contents_margins(0, 0, 0, 0)
        self.set_layout(layout)

        self.set_colour(QColor())

    def show_colour_dialog(self):
        dialog = QColorDialog(self._colour)
        dialog.set_option(QColorDialog.ShowAlphaChannel, True)
        if dialog.exec():
            self.set_colour(dialog.selected_color())

    def colour(self):
        return self._colour

    def set_colour(self, colour: QColor):
        self._colour = colour
        self.button.set_style_sheet(f'background-color: {self.colour().name()};')


class GeneralWidget(PreferenceWidgetBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QGridLayout()

        self.snap_tolerance = QCheckBox()
        self.rubberband_drag_tolerance = QLineEdit()
        self.node_selectable_thickness = QLineEdit()
        self.edge_selectable_thickness = ColourPicker()

        i = 0
        for text, widget in {
            'Snap Tolerance': self.snap_tolerance,
            'Rubberband Drag Tolerance': self.rubberband_drag_tolerance,
            'Node Selectable Thickness': self.node_selectable_thickness,
            'Edge Selectable Thickness': self.edge_selectable_thickness,
        }.items():
            layout.add_widget(QLabel(text), i, 0)
            layout.add_widget(widget, i, 1)
            i += 1

        int_validator = QIntValidator()
        self.minor_spacing.set_validator(int_validator)
        self.major_spacing.set_validator(int_validator)

        double_validator = QDoubleValidator()
        self.zoom_threshold.set_validator(double_validator)

        self.layout.add_layout(layout)
        self.layout.add_stretch()

    def preferences(self) -> dict:
        return {
            'snap_tolerance': self.visible.is_checked(),
            'rubberband_drag_tolerance': float(self.zoom_threshold.text()),
            'node_selectable_thickness': int(self.minor_spacing.text()),
            'edge_selectable_thickness': self.minor_colour.colour(),
        }

    def set_preferences(self, data: dict):
        self.snap_tolerance.set_text(str(data['snap_tolerance']))
        self.rubberband_drag_tolerance.set_text(str(data['rubberband_drag_tolerance']))
        self.node_selectable_thickness.set_colour(QColor(*data['node_selectable_thickness']))
        self.edge_selectable_thickness.set_colour(QColor(*data['edge_selectable_thickness']))


class ColoursWidget(PreferenceWidgetBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QGridLayout()
        self.texts = [
            'Node',
            'Selected Node',
            'Edge',
            'Selected Edge',
            'Poly',
            'Selected Poly',
        ]
        self.colour_pickers = {}

        for i, text in enumerate(self.texts):
            label = QLabel(text)
            line_edit = ColourPicker()
            layout.add_widget(label, i, 0)
            layout.add_widget(line_edit, i, 1)
            self.colour_pickers[text.lower().replace(' ', '_')] = line_edit

        self.layout.add_layout(layout)
        self.layout.add_stretch()

    def preferences(self) -> dict:
        return {
            text: widget.colour()
            for text, widget in self.colour_pickers.items()
        }

    def set_preferences(self, data: dict):
        for text, widget in self.colour_pickers.items():
            widget.set_colour(QColor(*data[text]))


class HotkeysWidget(PreferenceWidgetBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QGridLayout()
        self.texts = [
            'Select',
            'Move',
            'Rotate',
            'Scale',
            'Join Edges',
            'Split Edges',
            'Remove',
            'Frame Selection',
            'Grid Snap',
            'Vertex Snap',
        ]
        self.line_edits = {}

        for i, text in enumerate(self.texts):
            label = QLabel(text)
            line_edit = QLineEdit()
            layout.add_widget(label, i, 0)
            layout.add_widget(line_edit, i, 1)
            self.line_edits[text.lower().replace(' ', '_')] = line_edit

        self.layout.add_layout(layout)
        self.layout.add_stretch()

    def preferences(self) -> dict:
        return {
            text.lower().replace(' ', '_'): widget.text()
            for text, widget in self.line_edits.items()
        }

    def set_preferences(self, data: dict):
        for key, value in data.items():
            widget = self.line_edits[key]
            widget.set_text(value)


class GridWidget(PreferenceWidgetBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QGridLayout()

        self.visible = QCheckBox()
        self.zoom_threshold = QLineEdit()
        self.minor_spacing = QLineEdit()
        self.minor_colour = ColourPicker()
        self.major_spacing = QLineEdit()
        self.major_colour = ColourPicker()
        self.axes_colour = ColourPicker()

        i = 0
        for text, widget in {
            'Visible': self.visible,
            'Zoom Threshold': self.zoom_threshold,
            'Minor Spacing': self.minor_spacing,
            'Minor Colour': self.minor_colour,
            'Major Spacing': self.major_spacing,
            'Major Colour': self.major_colour,
            'Axes Colour': self.axes_colour,
        }.items():
            layout.add_widget(QLabel(text), i, 0)
            layout.add_widget(widget, i, 1)
            i += 1

        int_validator = QIntValidator()
        self.minor_spacing.set_validator(int_validator)
        self.major_spacing.set_validator(int_validator)

        double_validator = QDoubleValidator()
        self.zoom_threshold.set_validator(double_validator)

        self.layout.add_layout(layout)
        self.layout.add_stretch()

    def preferences(self) -> dict:
        return {
            'visible': self.visible.is_checked(),
            'zoom_threshold': float(self.zoom_threshold.text()),
            'minor_spacing': int(self.minor_spacing.text()),
            'minor_colour': self.minor_colour.colour(),
            'major_spacing': int(self.major_spacing.text()),
            'major_colour': self.major_colour.colour(),
            'axes_colour': self.axes_colour.colour(),
        }

    def set_preferences(self, data: dict):
        self.visible.set_checked(data['visible'])
        self.zoom_threshold.set_text(str(data['zoom_threshold']))
        self.minor_spacing.set_text(str(data['minor_spacing']))
        self.minor_colour.set_colour(QColor(*data['minor_colour']))
        self.major_spacing.set_text(str(data['major_spacing']))
        self.major_colour.set_colour(QColor(*data['major_colour']))
        self.axes_colour.set_colour(QColor(*data['axes_colour']))


class PlayWidget(PreferenceWidgetBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QGridLayout()

        self.eduke32_path = QLineEdit()

        i = 0
        for text, widget in {
            'EDuke32 Path': self.eduke32_path,
        }.items():
            layout.add_widget(QLabel(text), i, 0)
            layout.add_widget(widget, i, 1)
            i += 1

        self.layout.add_layout(layout)
        self.layout.add_stretch()

    def preferences(self) -> dict:
        return {
            'eduke32_path': self.eduke32_path.text(),
        }

    def set_preferences(self, data: dict):
        self.eduke32_path.set_text(data['eduke32_path'])


class PreferencesDialog(PreferenceDialogBase):

    def __init__(self, *args, **kwargs):
        super().__init__( *args, **kwargs)

        colours = ColoursWidget('Colours')
        self.add_widget(colours)

        grid = GridWidget('Grid')
        self.add_widget(grid)

        hotkeys = HotkeysWidget('Hotkeys')
        self.add_widget(hotkeys)

        play = PlayWidget('Play')
        self.add_widget(play)
