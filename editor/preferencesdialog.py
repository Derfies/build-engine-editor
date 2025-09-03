from PySide6.QtGui import QDoubleValidator, QIntValidator
from PySide6.QtWidgets import QCheckBox, QLineEdit

from applicationframework.preferencesdialog import (
    ManagedPreferenceWidgetBase,
    PreferencesDialog as PreferenceDialogBase,
)
from customwidgets.colourpicker import ColourPicker

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


class GeneralWidget(ManagedPreferenceWidgetBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for title, widget, validator in (
            ('Snap Tolerance', QLineEdit(), QIntValidator()),
            ('Rubberband Drag Tolerance', QLineEdit(), QIntValidator()),
            ('Node Selectable Thickness', QLineEdit(), QIntValidator()),
            ('Edge Selectable Thickness', QLineEdit(), QIntValidator()),
        ):
            self.add_managed_widget(title, widget, validator=validator)


class ColoursWidget(ManagedPreferenceWidgetBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for title, widget, validator in (
            ('Node', ColourPicker(), None),
            ('Selected Node', ColourPicker(), None),
            ('Edge', ColourPicker(), None),
            ('Selected Edge', ColourPicker(), None),
            ('Poly', ColourPicker(), None),
            ('Selected Poly', ColourPicker(), None),
        ):
            self.add_managed_widget(title, widget, validator=validator)


class HotkeysWidget(ManagedPreferenceWidgetBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for title, widget, validator in (
            ('Select', QLineEdit(), None),
            ('Move', QLineEdit(), None),
            ('Rotate', QLineEdit(), None),
            ('Scale', QLineEdit(), None),
            ('Join Edges', QLineEdit(), None),
            ('Split Edges', QLineEdit(), None),
            ('Remove', QLineEdit(), None),
            ('Frame Selection', QLineEdit(), None),
            ('Grid Snap', QLineEdit(), None),
            ('Vertex Snap', QLineEdit(), None),
        ):
            self.add_managed_widget(title, widget, validator=validator)


class GridWidget(ManagedPreferenceWidgetBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for title, widget, validator in (
            ('Visible', QCheckBox(), None),
            ('Zoom Threshold', QLineEdit(), QDoubleValidator()),
            ('Minor Spacing', QLineEdit(), QIntValidator()),
            ('Minor Colour', ColourPicker(), None),
            ('Major Spacing', QLineEdit(), QIntValidator()),
            ('Major Colour', ColourPicker(), None),
            ('Axes Colour', ColourPicker(), None),
        ):
            self.add_managed_widget(title, widget, validator=validator)


class PlayWidget(ManagedPreferenceWidgetBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for title, widget, validator in (
            ('EDuke32 Path', QLineEdit(), None),
            ('Nblood Path', QLineEdit(), None),
            ('Gzdoom Path', QLineEdit(), None),
        ):
            self.add_managed_widget(title, widget, validator=validator)


class PreferencesDialog(PreferenceDialogBase):

    def __init__(self, *args, **kwargs):
        super().__init__( *args, **kwargs)

        general = GeneralWidget('General')
        colours = ColoursWidget('Colours')
        grid = GridWidget('Grid')
        hotkeys = HotkeysWidget('Hotkeys')
        play = PlayWidget('Play')

        item = self.add_widget(general)
        self.add_widget(colours)
        self.add_widget(grid)
        self.add_widget(hotkeys)
        self.add_widget(play)

        # Set the initial item until we think of a better way to persist between
        # sessions.
        self.tree_view.set_current_item(item)
