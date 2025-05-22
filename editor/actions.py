from applicationframework.actions import Base
from updateflag import UpdateFlag

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


class SelectDeselectEdgesBase(Base):

    def __init__(self, edges):
        self.edges = edges

    def _select_edges(self):
        for edge in self.edges:
            edge.is_selected = True
        return UpdateFlag.SELECTION

    def _deselect_edges(self):
        for edge in self.edges:
            edge.is_selected = False
        return UpdateFlag.SELECTION


class SelectEdges(SelectDeselectEdgesBase):

    def undo(self):
        self._deselect_edges()

    def redo(self):
        self._select_edges()


class DeselectEdges(SelectDeselectEdgesBase):

    def undo(self):
        self._select_edges()

    def redo(self):
        self._deselect_edges()
