from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from applicationframework.actions import Edit

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


@dataclass
class Tweak:

    nodes: set[Any] = field(default_factory=set)
    hedges: set[tuple] = field(default_factory=set)
    faces: set[tuple] = field(default_factory=set)
    node_attrs: dict[Any, dict] = field(default_factory=lambda: defaultdict(dict))
    hedge_attrs: dict[tuple, dict] = field(default_factory=lambda: defaultdict(dict))
    face_attrs: dict[tuple, dict] = field(default_factory=lambda: defaultdict(dict))


class AddRemoveBase(Edit):

    def __init__(self, tweak: Tweak, *args, **kwargs):
        self.tweak = tweak
        super().__init__(*args, **kwargs)

    def remove(self):
        for face in self.tweak.faces:
            self.obj.remove_face(face)
        for edge in self.tweak.hedges:
            self.obj.remove_hedge(edge)
        for node in self.tweak.nodes:
            self.obj.remove_node(node)
        self.obj.update()

    def add(self):
        for node in self.tweak.nodes:
            self.obj.add_node(node, **self.tweak.node_attrs.get(node, {}))
        for hedge in self.tweak.hedges:
            self.obj.add_hedge(hedge, **self.tweak.hedge_attrs.get(hedge, {}))
        for face in self.tweak.faces:
            self.obj.add_face(face, **self.tweak.face_attrs.get(face, {}))
        self.obj.update()


class Add(AddRemoveBase):

    def undo(self):
        self.remove()

    def redo(self):
        self.add()


class Remove(AddRemoveBase):

    def undo(self):
        self.add()

    def redo(self):
        self.remove()
