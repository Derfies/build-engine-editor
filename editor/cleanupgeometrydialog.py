from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QRadioButton,
    QVBoxLayout,
)

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


class CleanUpGeometryDialog(QDialog):

    # TODO: Save settings to preferences, but we don't have that many yet.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_window_title('Cleanup Geometry')

        # Create the main layout.
        main_layout = QVBoxLayout(self)

        effect_group = QGroupBox('Cleanup Effect')
        effect_layout = QVBoxLayout()
        self.cleanup_radio = QRadioButton('Cleanup matching geometry')
        self.select_radio = QRadioButton('Select matching geometry')
        self.cleanup_radio.set_checked(True)
        effect_layout.add_widget(self.cleanup_radio)
        effect_layout.add_widget(self.select_radio)
        effect_group.set_layout(effect_layout)
        main_layout.add_widget(effect_group)

        remove_group = QGroupBox('Remove Geometry')
        remove_layout = QVBoxLayout()
        self.edges_with_no_face = QCheckBox('Edges with no face')
        self.nodes_with_no_edges = QCheckBox('Nodes with no edges')
        remove_layout.add_widget(self.edges_with_no_face)
        remove_layout.add_widget(self.nodes_with_no_edges)
        remove_group.set_layout(remove_layout)
        main_layout.add_widget(remove_group)

        # Add OK and Cancel buttons.
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.add_widget(buttons)

    def get_values(self):
        return {
            'edges_with_no_face': self.edges_with_no_face.is_checked(),
            'nodes_with_no_edges': self.nodes_with_no_edges.is_checked(),
            'delete_geometry': self.cleanup_radio.is_checked(),
        }
