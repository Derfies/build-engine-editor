from PySide6.QtWidgets import QApplication

from applicationframework.actions import Composite
from editor.actions import DeselectElements, SelectElements
from editor.graph import Edge, Node
from editor.updateflag import UpdateFlag

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


def select_elements(elements: set[Node] | set[Edge]):
    action = Composite([
        DeselectElements(QApplication.instance().doc.selected_elements),
        SelectElements(elements)
    ], flags=UpdateFlag.SELECTION)
    QApplication.instance().action_manager.push(action)
    QApplication.instance().doc.updated(action(), dirty=False)
