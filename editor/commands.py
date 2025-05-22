from PySide6.QtWidgets import QApplication

from actions import DeselectEdges, SelectEdges
from applicationframework.actions import Composite
from updateflag import UpdateFlag

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


def select_edges(edges):
    action = Composite([
        DeselectEdges(QApplication.instance().doc.selected_edges),
        SelectEdges(edges)
    ], flags=UpdateFlag.SELECTION)
    QApplication.instance().action_manager.push(action)
    QApplication.instance().doc.updated(action(), dirty=False)
