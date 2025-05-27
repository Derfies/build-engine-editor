from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QLabel, QLineEdit

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


class PreferencesDialog(PreferenceDialogBase):

    def __init__(self, *args, **kwargs):
        super().__init__( *args, **kwargs)

        colours = PreferenceWidgetBase('Colours')
        colours_item = self.add_widget(colours)
        for i in range(2):
            wdiget = TestPreferenceWidget('Foo')
            self.add_widget(wdiget, parent=colours_item)

    def load_preferences(self, data: dict):
        print(data)

    def save_preferences(self):
        self.accept()  # Close the dialog
