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


class GraphEditBase(Edit):

    def __init__(self, nodes: tuple, edges: tuple[tuple], faces: tuple[tuple], *args, **kwargs):
        self.node_attrs = kwargs.pop('node_attrs', {})
        self.edge_attrs = kwargs.pop('edge_attrs', {})
        self.face_attrs = kwargs.pop('face_attrs', {})
        super().__init__(*args, **kwargs)

        print(faces)
        print(self.face_attrs)

        self.nodes = nodes
        self.edges = edges
        self.faces = faces

    def undo(self):

        # TODO: Use nicer interface.
        # TODO: Needs to handle all node / edge / face with attr combos.
        for face in self.faces:
            del self.obj._faces[face]
        for edge in self.edges:
            self.obj.data.remove_edge(*edge)
        for node in self.nodes:
            self.obj.data.remove_node(node)
        self.obj.update_undirected()

    def redo(self):
        for node in self.nodes:
            self.obj.data.add_node(node, **self.node_attrs.get(node, {}))
        for edge in self.edges:
            self.obj.data.add_edge(*edge, **self.edge_attrs.get(edge, {}))
        for face in self.faces:
            self.obj._faces[face] = self.face_attrs.get(face, {})
            print(face, '->', self.obj._faces[face])
        self.obj.update_undirected()
