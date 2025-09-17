from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable

from applicationframework.actions import Base, Composite, Edit
from editor.graph import Edge, Face, Node
from editor.updateflag import UpdateFlag

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


@dataclass
class Tweak:

    nodes: set[Any] = field(default_factory=set)
    edges: set[tuple] = field(default_factory=set)
    faces: set[tuple] = field(default_factory=set)
    node_attrs: dict[Any, dict] = field(default_factory=lambda: defaultdict(dict))
    edge_attrs: dict[tuple, dict] = field(default_factory=lambda: defaultdict(dict))
    face_attrs: dict[tuple, dict] = field(default_factory=lambda: defaultdict(dict))


class AddRemoveBase(Edit):

    def __init__(self, tweak: Tweak, *args, **kwargs):
        self.tweak = tweak
        super().__init__(*args, **kwargs)

    def remove(self):
        for face in self.tweak.faces:
            self.obj.remove_face(face)
        for edge in self.tweak.edges:
            self.obj.remove_edge(edge)
        for node in self.tweak.nodes:
            self.obj.remove_node(node)
        self.obj.update()
        return self.flags

    def add(self):
        for node in self.tweak.nodes:
            self.obj.add_node(node, **self.tweak.node_attrs.get(node, {}))
        for edge in self.tweak.edges:
            self.obj.add_edge(edge, **self.tweak.edge_attrs.get(edge, {}))
        for face in self.tweak.faces:
            self.obj.add_face(face, **self.tweak.face_attrs.get(face, {}))
        self.obj.update()
        return self.flags


class Add(AddRemoveBase):

    def undo(self):
        return self.remove()

    def redo(self):
        return self.add()


class Remove(AddRemoveBase):

    def undo(self):
        return self.add()

    def redo(self):
        return self.remove()


class SetElementAttribute(Edit):

    def __init__(self, name: str, value, *args, **kwargs):
        super().__init__(*args,  **kwargs)
        self.name = name
        self.value = value
        self.old_value = self.obj.get_attribute(self.name)

    def undo(self):
        self.obj.set_attribute(self.name, self.old_value)
        return self.flags

    def redo(self):
        self.obj.set_attribute(self.name, self.value)
        return self.flags


class SetElementsAttribute(Composite):

    def __init__(self, name, value, *objs, **kwargs):
        actions = [SetElementAttribute(name, value, obj) for obj in objs]
        super().__init__(actions, **kwargs)


class SelectDeselectBase(Base):

    """
    Not totally happy with this. Can't easily create an action which will select
    things until after they are added to the graph.

    """

    def __init__(self, elements: Iterable[Node | Edge | Face]):
        super().__init__(flags=UpdateFlag.SELECTION)
        self._elements = elements
        self._old_is_selected = [e.is_selected for e in self._elements]

    def undo(self):
        for i, element in enumerate(self._elements):
            element.is_selected = self._old_is_selected[i]


class Select(SelectDeselectBase):

    def redo(self):
        for element in self._elements:
            element.is_selected = True


class Deselect(SelectDeselectBase):

    def redo(self):
        for element in self._elements:
            element.is_selected = False
