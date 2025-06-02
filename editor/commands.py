from PySide6.QtWidgets import QApplication

from applicationframework.actions import Composite, SetAttribute
from editor.actions import AddPoly, DeselectElements, SelectElements
from editor.graph import Edge, Node, Poly
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


def transform_node_items(node_items):
    actions = []
    for node_item in node_items:
        actions.append(SetAttribute('x', node_item.pos().x(), node_item.element().data))
        actions.append(SetAttribute('y', node_item.pos().y(), node_item.element().data))
    action = Composite(actions, flags=UpdateFlag.GRAPH)
    QApplication.instance().action_manager.push(action)
    QApplication.instance().doc.updated(action(), dirty=False)


def add_poly(poly: Poly):
    action = AddPoly(poly)
    QApplication.instance().action_manager.push(action)
    QApplication.instance().doc.updated(action(), dirty=True)
