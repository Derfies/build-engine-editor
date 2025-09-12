from typing import Any

from PySide6.QtGui import QDoubleValidator, QIntValidator
from PySide6.QtWidgets import QCheckBox, QComboBox, QLineEdit

from applicationframework.mixins import HasAppMixin
from applicationframework.preferencesdialog import (
    DataclassPreferenceWidgetBase,
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


class AdaptorWidget(ManagedPreferenceWidgetBase, HasAppMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.combo_box = QComboBox()
        self.combo_box.add_item('None')
        for name in self.app().adaptor_manager.adaptors:
            self.combo_box.add_item(name.capitalize())
        self.combo_box.set_current_index(0)
        self.add_managed_widget('Current Adaptor', self.combo_box)

    def preferences(self) -> dict[str, Any]:
        index = self.combo_box.current_index()
        value = self.combo_box.current_text().lower() if index > 0 else None
        return {'current_adaptor': value}

    def set_preferences(self, data: dict[str, Any]):
        value = data['current_adaptor']
        index = 0 if value is None else self.combo_box.find_text(value.capitalize())
        self.combo_box.set_current_index(index)


class PreferencesDialog(PreferenceDialogBase, HasAppMixin):

    def __init__(self, *args, **kwargs):
        super().__init__( *args, **kwargs)

        general = GeneralWidget('General')
        general_item = self.add_widget(general)
        self.add_widget(ColoursWidget('Colours'))
        self.add_widget(GridWidget('Grid'))
        self.add_widget(HotkeysWidget('Hotkeys'))

        adaptors = AdaptorWidget('Adaptors')
        adaptors_item = self.add_widget(adaptors)
        for name, adaptor in self.app().adaptor_manager.adaptors.items():
            widget = DataclassPreferenceWidgetBase(adaptor.settings, adaptor.name.capitalize())
            self.add_widget(widget, adaptors_item)

        # Set the initial item until we think of a better way to persist between
        # sessions.
        self.tree_view.set_current_item(general_item)
