from __future__ import annotations
import abc
import copy
import json
import logging
from collections import defaultdict
from functools import singledispatchmethod
from pathlib import Path
from typing import Any

import networkx as nx
from PySide6.QtCore import QPointF
from networkx.readwrite import json_graph

from applicationframework.contentbase import ContentBase
from editor import maths
from editor.constants import ATTRIBUTES, EDGE_DEFAULT, FACES, FACE_DEFAULT, IS_SELECTED, NODE_DEFAULT
from editor.texture import Texture

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


logger = logging.getLogger(__name__)


class TextureEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, Texture):
            return obj.value
        return super().default(obj)


class ElementBase(metaclass=abc.ABCMeta):

    def __init__(self, graph: 'Graph', data):
        self.graph = graph
        self.data = data

    def __str__(self):
        return str(self.data)

    def __hash__(self):
        return hash(self.data)

    def __eq__(self, other):
        return hash(self) == hash(other)

    @property
    @abc.abstractmethod
    def nodes(self) -> tuple[Node]:
        ...


class Element(ElementBase):

    def __getitem__(self, item):
        return self.get_attributes()[item]

    @abc.abstractmethod
    def get_private_attributes(self):
        ...

    def get_attributes(self):
        return self.get_private_attributes()[ATTRIBUTES]

    def get_attribute(self, key, default=None):
        return self.get_attributes().get(key, default)

    def set_attribute(self, key, value):
        self.get_attributes()[key] = value

    @property
    def is_selected(self):
        return self.get_private_attributes().get(IS_SELECTED, False)

    @is_selected.setter
    def is_selected(self, value: bool):
        self.get_private_attributes()[IS_SELECTED] = value


class Node(Element):

    def get_private_attributes(self):
        return self.graph.data.nodes[self.data]

    @property
    def nodes(self) -> tuple[Node]:
        return (self,)

    @property
    def node(self):
        return self

    @property
    def edges(self) -> tuple[Edge]:
        return tuple(self.graph.node_to_edges[self])

    @property
    def in_edges(self) -> tuple[Edge]:
        return tuple(self.graph.node_to_in_edges[self])

    @property
    def out_edges(self) -> tuple[Edge]:
        return tuple(self.graph.node_to_out_edges[self])

    @property
    def faces(self) -> tuple[Face]:
        return tuple(self.graph.node_to_faces[self])

    @property
    def pos(self) -> QPointF:

        # TODO: Wean off QPointF type.
        return QPointF(self.get_attribute('x'), self.get_attribute('y'))

    @pos.setter
    def pos(self, pos: QPointF):

        # TODO: Wean off QPointF type.
        self.set_attribute('x', pos.x())
        self.set_attribute('y', pos.y())


class Edge(Element):

    @singledispatchmethod
    def __contains__(self, node: Node):
        return node in self.nodes

    def get_private_attributes(self):
        return self.graph.data.edges[self.data]

    @property
    def head(self):

        # Techincally should use a dict like everything else?
        return self.graph.get_node(self.data[0])

    @property
    def tail(self):

        # Techincally should use a dict like everything else?
        return self.graph.get_node(self.data[1])

    @property
    def nodes(self) -> tuple[Node]:
        return self.graph.edge_to_nodes[self]

    @property
    def face(self) -> Face | None:
        return self.graph.edge_to_face.get(self)

    @property
    def normal(self):
        return maths.edge_normal(self.head.pos.to_tuple(), self.tail.pos.to_tuple())

    @property
    def reversed(self) -> Edge | None:
        rev_edge = self.data[1], self.data[0]
        if not self.graph.has_edge(*rev_edge):
            return None
        return self.graph.get_edge(*rev_edge)

    @property
    def reversed_face(self):

        # TODO: Not the best name for this property...
        rev_edge = self.reversed
        if rev_edge is None:
            return None
        return rev_edge.face


class Ring(ElementBase):

    @property
    def nodes(self) -> tuple[Node]:
        return self.graph.ring_to_nodes[self]

    @property
    def edges(self) -> tuple[Edge]:
        return self.graph.ring_to_edges[self]


class Face(Element):

    @singledispatchmethod
    def __contains__(self, node: Node):
        return node in self.nodes

    @__contains__.register
    def _(self, edge: Edge):
        return edge in self.edges

    def get_private_attributes(self):
        return self.graph.data.graph[FACES][self]

    @property
    def nodes(self) -> tuple[Node]:
        return self.graph.face_to_nodes[self]

    @property
    def edges(self) -> tuple[Edge]:
        return self.graph.face_to_edges[self]

    @property
    def faces(self) -> tuple[Face]:
        return (self, )

    @property
    def rings(self):
        return self.graph.face_to_rings[self]


class Graph(ContentBase):

    def __init__(self, **default_attrs):

        # TODO: Allow setting of whatever kind of graph we like.
        self.data = nx.DiGraph()

        # TODO: Put this in a new method - it's already tripped me over once
        # during load / save
        self.data.graph[ATTRIBUTES] = default_attrs
        self.data.graph[NODE_DEFAULT] = {}
        self.data.graph[EDGE_DEFAULT] = {}
        self.data.graph[FACE_DEFAULT] = {}
        self.data.graph[FACES] = {}

        # Maps.
        self.node_to_edges = defaultdict(set)
        self.node_to_in_edges = defaultdict(set)
        self.node_to_out_edges = defaultdict(set)
        self.node_to_faces = defaultdict(set)


        self.edge_to_nodes = defaultdict(set)
        self.edge_to_nodes = defaultdict(set)
        self.edge_to_face = {}

        self.ring_to_nodes = {}
        self.ring_to_edges = {}

        self.face_to_nodes = defaultdict(list)
        self.face_to_edges = {}
        self.face_to_rings = {}

        self.update()

    def _get_element_default_attributes(self, key: str):
        return copy.deepcopy(self.data.graph[key])

    def get_node_default_attributes(self):
        return self._get_element_default_attributes(NODE_DEFAULT)

    def get_edge_default_attributes(self):
        return self._get_element_default_attributes(EDGE_DEFAULT)

    def get_face_default_attributes(self):
        return self._get_element_default_attributes(FACE_DEFAULT)

    def _add_element_attribute_definition(self, element: str, name: str, default):
        self.data.graph[element][name] = default

    def add_node_attribute_definition(self, name: str, default):
        self._add_element_attribute_definition(NODE_DEFAULT, name, default)

    def add_edge_attribute_definition(self, name: str, default):
        self._add_element_attribute_definition(EDGE_DEFAULT, name, default)

    def add_face_attribute_definition(self, name: str, default):
        self._add_element_attribute_definition(FACE_DEFAULT, name, default)

    def update(self):

        self.node_to_edges.clear()
        self.node_to_in_edges.clear()
        self.node_to_out_edges.clear()
        self.node_to_faces.clear()

        self.edge_to_nodes.clear()
        self.edge_to_face.clear()

        self.face_to_nodes.clear()
        #self.face_to_edges.clear()

        ring_to_nodes = defaultdict(list)
        ring_to_edges = defaultdict(list)
        face_to_edges = defaultdict(list)
        face_to_rings = defaultdict(list)


        for face in self.data.graph[FACES]:
            face_ = self.get_face(face)

            rings = [[]]

            start_node = face[0]
            i = 0
            while i < len(face) - 1:
                curr, nxt = face[i], face[i + 1]
                rings[-1].append(curr)
                i += 1
                if nxt == start_node and i < len(face) - 1:
                    rings.append([])
                    i += 1
                    start_node = face[i]
            rings = tuple([tuple(ring) for ring in rings])

            for ring in rings:
                ring_nodes_ = []
                ring_edges_ = []
                for i in range(len(ring)):
                    head, tail = ring[i], ring[(i + 1) % len(ring)]
                    node_ = self.get_node(head)
                    edge = self.get_edge(head, tail)
                    face_to_edges[face].append(edge)
                    self.edge_to_face[edge] = face_
                    self.node_to_faces[node_].add(face_)
                    self.face_to_nodes[face].append(node_)

                    ring_nodes_.append(node_)
                    ring_edges_.append(edge)

                ring_ = Ring(self, tuple(ring_nodes_))
                face_to_rings[face].append(ring_)
                ring_to_nodes[ring_].extend(ring_nodes_)
                ring_to_edges[ring_].extend(ring_edges_)

        for node in self.data.nodes:
            node_ = self.get_node(node)
            in_edges = set(self.data.in_edges(node))
            self.node_to_in_edges[node_].update([self.get_edge(*edge) for edge in in_edges])
            out_edges = set(self.data.out_edges(node))
            self.node_to_out_edges[node_].update([self.get_edge(*edge) for edge in out_edges])
            edges = in_edges | out_edges
            self.node_to_edges[node_].update([self.get_edge(*edge) for edge in edges])

        for edge in self.data.edges:
            edge_ = self.get_edge(*edge)
            self.edge_to_nodes[edge].add(edge_.head)
            self.edge_to_nodes[edge].add(edge_.tail)

        self.ring_to_nodes = {k: tuple(v) for k, v in ring_to_nodes.items()}
        self.ring_to_edges = {k: tuple(v) for k, v in ring_to_edges.items()}
        self.face_to_edges = {k: tuple(v) for k, v in face_to_edges.items()}
        self.face_to_rings = {k: tuple(v) for k, v in face_to_rings.items()}

    @property
    def nodes(self) -> set[Node]:
        return {self.get_node(node) for node in self.data.nodes}

    @property
    def edges(self) -> set[Edge]:
        return {self.get_edge(*edge) for edge in self.data.edges}

    @property
    def faces(self) -> set[Face]:
        return {self.get_face(face) for face in self.data.graph[FACES]}

    def get_node(self, node) -> Node:
        assert node in self.data, f'Node not found: {node}'
        return Node(self, node)

    def get_edge(self, head, tail) -> Edge:
        assert (head, tail) in self.data.edges, f'Edge not found: {(head, tail)}'
        return Edge(self, (head, tail))

    def get_face(self, face: tuple) -> Face:
        assert face in self.data.graph[FACES], f'Face not found: {face}'
        return Face(self, face)

    def has_node(self, node: Any):
        return node in self.data.nodes

    def has_edge(self, head, tail):
        return (head, tail) in self.data.edges

    def add_node(self, node: Any, **node_attrs):
        default_node_attrs = self.get_node_default_attributes()
        default_node_attrs.update(node_attrs)
        self.data.add_node(node, **{ATTRIBUTES: default_node_attrs})
        return self.get_node(node)

    def add_edge(self, edge: tuple[Any, Any], **edge_attrs):
        default_edge_attrs = self.get_edge_default_attributes()
        default_edge_attrs.update(edge_attrs)
        self.data.add_edge(*edge, **{ATTRIBUTES: default_edge_attrs})
        return self.get_edge(*edge)

    def add_face(self, face: tuple[Any, ...], **face_attrs):

        # TODO: Test node actually exists?
        default_face_attrs = self.get_face_default_attributes()
        default_face_attrs.update(face_attrs)
        self.data.graph[FACES][face] = {ATTRIBUTES: default_face_attrs}
        return self.get_face(face)

    def remove_node(self, node: Any):
        self.data.remove_node(node)

    def remove_edge(self, edge: tuple[Any, Any]):
        self.data.remove_edge(*edge)

    def remove_face(self, face: tuple[Any, ...]):
        del self.data.graph[FACES][face]

    def load(self, file_path: str | Path):
        """
        NOTE: This makes the assumption that certain keys are a certain type.
        This is bad! We need to define these types in the serialized format.
        
        """
        with open(file_path, 'r') as f:
            g = json_graph.node_link_graph(json.load(f))

        # Build faces from comma-separated list.
        faces = {}
        for nodes, attrs in g.graph.pop(FACES).items():
            faces[tuple(nodes.split(', '))] = attrs
            for key in {'floor_tex', 'ceiling_tex'}:
                if key in attrs[ATTRIBUTES]:
                    attrs[ATTRIBUTES][key] = Texture(attrs[ATTRIBUTES][key])
        g.graph[FACES] = faces

        # Rehydrate textures.
        for head, tail, attrs in g.edges(data=True):
            for key in {'low_tex', 'mid_tex', 'top_tex'}:
                if key in attrs[ATTRIBUTES]:
                    attrs[ATTRIBUTES][key] = Texture(attrs[ATTRIBUTES][key])

        self.data = g
        self.update()

    def save(self, file_path: str):
        g = self.data.copy()

        # Convert faces to a comma-separated list.
        g.graph[FACES] = {
            ', '.join([str(face_node) for face_node in face_nodes]): face_attrs
            for face_nodes, face_attrs in g.graph[FACES].items()
        }

        data = json_graph.node_link_data(g)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, cls=TextureEncoder)
