from dataclasses import dataclass

from applicationframework.actions import Edit

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


@dataclass
class GraphEditData:

    nodes: tuple
    edges: tuple[tuple]
    faces: tuple[tuple]
    node_attrs: dict[tuple]
    edge_attrs: dict[tuple[tuple]]
    face_attrs: dict[tuple[tuple]]


class AddRemoveBase(Edit):

    # Should these deal with raw networkx data or the wrapper?
    # Bit of a rant.
    # We don't have a wrapper of something when we want to create it, since
    # wrapping an object happens on retrieval. Which means we would be using a
    # mix of wrappers to delete and non-wrapped objects to create (yuk). So that's
    # some non-symmetry that I don't like.
    # Further, because of undo adding and removing things are two sides of the
    # same coin - you don't get one without the possibility of the other. So
    # any objects assigned to an action need to be able to pass the api of the
    # content object with both.
    # TODO: Are these just done with SetAttr actions, or is that just too granular?

    def __init__(self, *args, **kwargs):
        self.nodes = kwargs.pop('nodes', tuple())
        self.edges = kwargs.pop('edges', tuple())
        self.faces = kwargs.pop('faces', tuple())
        self.node_attrs = kwargs.pop('node_attrs', {})
        self.edge_attrs = kwargs.pop('edge_attrs', {})
        self.face_attrs = kwargs.pop('face_attrs', {})
        super().__init__(*args, **kwargs)

    def remove(self):
        for face in self.faces:
            self.obj.remove_face(face)
        for edge in self.edges:
            self.obj.remove_hedge(edge)
        for node in self.nodes:
            self.obj.remove_node(node)
        self.obj.update()

    def add(self):
        for node in self.nodes:
            self.obj.add_node(node, **self.node_attrs.get(node, {}))
        for edge in self.edges:
            self.obj.add_hedge(edge, **self.edge_attrs.get(edge, {}))
        for face in self.faces:
            self.obj.add_face(face, **self.face_attrs.get(face, {}))
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
