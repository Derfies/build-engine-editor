from applicationframework.actions import Base
from editor.graph import Edge, Node
from editor.updateflag import UpdateFlag

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


class SelectDeselectElementsBase(Base):

    def __init__(self, elements: set[Edge, Node]):
        self.edges = elements

    def _select_elements(self):
        for edge in self.edges:
            edge.is_selected = True
        return UpdateFlag.SELECTION

    def _deselect_elements(self):
        for edge in self.edges:
            edge.is_selected = False
        return UpdateFlag.SELECTION


class SelectElements(SelectDeselectElementsBase):

    def undo(self):
        self._deselect_elements()

    def redo(self):
        self._select_elements()


class DeselectElements(SelectDeselectElementsBase):

    def undo(self):
        self._select_elements()

    def redo(self):
        self._deselect_elements()
