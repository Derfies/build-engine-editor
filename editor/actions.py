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

    def __init__(self, *args, **kwargs):
        self.nodes = kwargs.pop('nodes', tuple())
        self.edges = kwargs.pop('edges', tuple())
        self.faces = kwargs.pop('faces', tuple())
        self.node_attrs = kwargs.pop('node_attrs', {})
        self.edge_attrs = kwargs.pop('edge_attrs', {})
        self.face_attrs = kwargs.pop('face_attrs', {})
        super().__init__(*args, **kwargs)

    def remove(self):

        # TODO: Use nicer interface.
        # TODO: Needs to handle all node / edge / face with attr combos.
        for face in self.faces:
            del self.obj._faces[face]
        for edge in self.edges:
            self.obj.data.remove_edge(*edge)
        for node in self.nodes:
            self.obj.data.remove_node(node)
        self.obj.update_undirected()

    def add(self):
        for node in self.nodes:
            #print('ADD:', node, '->', self.node_attrs.get(node, {}))
            self.obj.data.add_node(node)

        for edge in self.edges:
            self.obj.data.add_edge(*edge, **self.edge_attrs.get(edge, {}))
        for face in self.faces:
            self.obj._faces[face] = self.face_attrs.get(face, {})

        for node, node_attr in self.node_attrs.items():
            for key, value in node_attr.items():
                wrapped = self.obj.get_node(node)
                wrapped.set_attribute(key, value)
                #self.obj.data.nodes[node][key] = value
                #print('SET ATTR:', node, key, value)


        self.obj.update_undirected()


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
