from applicationframework.actions import Base
from editor.graph import Edge, Node, Poly
from editor.updateflag import UpdateFlag

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


class SelectDeselectElementsBase(Base):

    # TODO: Use setattribute?

    def __init__(self, elements: set[Edge, Node]):
        self.elements = elements

    def _select_elements(self):
        for element in self.elements:
            element.is_selected = True
        return UpdateFlag.SELECTION

    def _deselect_elements(self):
        for element in self.elements:
            element.is_selected = False
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


class AddPoly(Base):

    def __init__(self, poly: Poly):
        self.poly = poly

    def undo(self):
        self.app().doc.content.g.polys.remove(self.poly)

    def redo(self):
        self.app().doc.content.g.add_poly(self.poly)


class CreatePoly(Base):

    def __init__(self, points):
        self.points = points

    def undo(self):
        self._deselect_elements()

    def redo(self):
        self._select_elements()
