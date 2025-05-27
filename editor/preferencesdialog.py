from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QLabel, QLineEdit, QGridLayout

from applicationframework.preferencesdialog import PreferencesDialog as PreferenceDialogBase, PreferenceWidgetBase


# noinspection PyUnresolvedReferences
from __feature__ import snake_case


class TestPreferenceWidget(PreferenceWidgetBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.resolution_rows = QLineEdit()
        self.layout.add_widget(QLabel('Number of rows:'))
        self.layout.add_widget(self.resolution_rows)
        self.resolution_cols = QLineEdit()
        self.layout.add_widget(QLabel('Number of columns:'))
        self.layout.add_widget(self.resolution_cols)

        int_validator = QIntValidator()
        self.resolution_rows.set_validator(int_validator)
        self.resolution_cols.set_validator(int_validator)

        self.layout.add_stretch()

    def preferences(self) -> dict:
        return {
            'resolution_rows': int(self.resolution_rows.text()),
            'resolution_cols': int(self.resolution_cols.text()),
        }

    def set_preferences(self, data: dict):
        self.resolution_rows.set_text(str(data['resolution_rows']))
        self.resolution_cols.set_text(str(data['resolution_cols']))


class HotkeysWidget(PreferenceWidgetBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QGridLayout()
        labels = [
            'Select',
            'Move',
            'Rotate',
            'Scale',
            'Draw Poly',
            'Select by Node',
            'Select by Edge',
            'Select by Poly',
        ]
        self.line_edits = []

        for i, text in enumerate(labels):
            label = QLabel(text)
            line_edit = QLineEdit()
            layout.add_widget(label, i, 0)
            layout.add_widget(line_edit, i, 1)
            self.line_edits.append(line_edit)

        self.layout.add_layout(layout)
        self.layout.add_stretch()

    def preferences(self) -> dict:
        pass

    def set_preferences(self, data: dict):
        pass


class PreferencesDialog(PreferenceDialogBase):

    def __init__(self, *args, **kwargs):
        super().__init__( *args, **kwargs)

        colours = PreferenceWidgetBase('Colours')
        colours_item = self.add_widget(colours)
        for i in range(2):
            wdiget = TestPreferenceWidget('Foo')
            self.add_widget(wdiget, parent=colours_item)

        hotkeys = HotkeysWidget('Hotkeys')
        self.add_widget(hotkeys)
        #hotkeys_item = self.add_widget(hotkeys)
        #for i in range(2):
        #    wdiget = TestPreferenceWidget('Foo')
        #    self.add_widget(wdiget, parent=colours_item)

    def load_preferences(self, data: dict):
        print(data)

    def save_preferences(self):
        self.accept()  # Close the dialog
