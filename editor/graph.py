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

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


logger = logging.getLogger(__name__)


TYPES = {
    type_.__name__: type_
    for type_ in {bool, int, float, str}
}


class Element(metaclass=abc.ABCMeta):

    def __init__(self, graph: 'Graph', data):
        self.graph = graph
        self.data = data

    def __str__(self):
        return str(self.data)

    def __hash__(self):
        return hash(self.data)

    def __eq__(self, other):
        return hash(self) == hash(other)

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
    @abc.abstractmethod
    def nodes(self) -> tuple:
        ...

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
    def nodes(self) -> tuple:
        return (self,)

    @property
    def node(self):
        return self

    @property
    def hedges(self) -> tuple[Hedge]:
        return tuple(self.graph.node_to_hedges[self])

    @property
    def in_hedges(self) -> tuple[Hedge]:
        return tuple(self.graph.node_to_in_hedges[self])

    @property
    def out_hedges(self) -> tuple[Hedge]:
        return tuple(self.graph.node_to_out_hedges[self])

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

    def __hash__(self):
        return hash(frozenset(self.data))

    @singledispatchmethod
    def __contains__(self, node: Node):
        return node in self.nodes

    def get_private_attributes(self):
        return self.graph.undirected_data.edges[self.data]

    @property
    def head(self):
        return self.graph.get_node(self.data[0])

    @property
    def tail(self):
        return self.graph.get_node(self.data[1])

    @property
    def nodes(self) -> tuple[Node]:
        return tuple(self.graph.edge_to_nodes[self])

    @property
    def hedges(self) -> tuple[Hedge]:
        return tuple(self.graph.edge_to_hedges[self])

    @property
    def faces(self) -> tuple[Face]:
        return tuple(self.graph.edge_to_faces[self])


class Hedge(Element):

    @singledispatchmethod
    def __contains__(self, node: Node):
        return node in self.nodes

    def get_private_attributes(self):

        # TODO: Whats the correct approach here??
        # The editor will select undirected edges, so that needs to report both
        # sets of attributes, ie one for each hedge.
        return self.graph.data.edges[self.data]

    @property
    def head(self):
        return self.graph.get_node(self.data[0])

    @property
    def tail(self):
        return self.graph.get_node(self.data[1])

    @property
    def nodes(self) -> tuple[Node]:
        return tuple(self.graph.hedge_to_nodes[self])

    @property
    def edges(self) -> tuple[Edge]:
        return tuple(self.graph.hedge_to_edge[self])

    @property
    def face(self) -> Face | None:
        return self.graph.hedge_to_face.get(self)

    @property
    def normal(self):
        return maths.edge_normal(self.head.pos.to_tuple(), self.tail.pos.to_tuple())


class Face(Element):

    @singledispatchmethod
    def __contains__(self, node: Node):
        return node in self.nodes

    @__contains__.register
    def _(self, edge: Edge):
        return edge in self.edges

    @__contains__.register
    def _(self, hedge: Hedge):
        return hedge in self.hedges

    def get_private_attributes(self):
        return self.graph.data.graph[FACES][self]

    @property
    def nodes(self) -> tuple[Node]:
        return tuple(self.graph.face_to_nodes[self])

    @property
    def edges(self) -> tuple[Edge]:
        return tuple(self.graph.face_to_edges[self])

    @property
    def hedges(self) -> tuple[Hedge]:
        return tuple(self.graph.face_to_hedges[self])

    @property
    def faces(self) -> tuple[Face]:
        return (self, )


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
        self.node_to_hedges = defaultdict(set)
        self.node_to_in_hedges = defaultdict(set)
        self.node_to_out_hedges = defaultdict(set)
        self.node_to_faces = defaultdict(set)

        self.edge_to_nodes = defaultdict(set)
        self.edge_to_hedges = {}
        self.edge_to_faces = defaultdict(set)

        self.hedge_to_nodes = defaultdict(set)
        self.hedge_to_edge = {}
        self.hedge_to_face = {}

        self.face_to_nodes = defaultdict(list)
        self.face_to_edges = defaultdict(list)
        self.face_to_hedges = defaultdict(list)

        self.update()

    def _get_element_default_attributes(self, key: str):
        return copy.deepcopy(self.data.graph[key])

    def get_node_default_attributes(self):
        return self._get_element_default_attributes(NODE_DEFAULT)

    def get_hedge_default_attributes(self):
        return self._get_element_default_attributes(EDGE_DEFAULT)

    def get_face_default_attributes(self):
        return self._get_element_default_attributes(FACE_DEFAULT)

    def _add_element_attribute_definition(self, element: str, name: str, default):
        self.data.graph[element][name] = default

    def add_node_attribute_definition(self, name: str, default):
        self._add_element_attribute_definition(NODE_DEFAULT, name, default)

    def add_hedge_attribute_definition(self, name: str, default):
        self._add_element_attribute_definition(EDGE_DEFAULT, name, default)

    def add_face_attribute_definition(self, name: str, default):
        self._add_element_attribute_definition(FACE_DEFAULT, name, default)

    def update(self):

        self.node_to_edges.clear()
        self.node_to_hedges.clear()
        self.node_to_in_hedges.clear()
        self.node_to_out_hedges.clear()
        self.node_to_faces.clear()

        self.edge_to_nodes.clear()
        self.edge_to_hedges.clear()
        self.edge_to_faces.clear()

        self.hedge_to_nodes.clear()
        self.hedge_to_edge.clear()
        self.hedge_to_face.clear()

        self.face_to_nodes.clear()
        self.face_to_edges.clear()
        self.face_to_hedges.clear()

        self.undirected_data = self.data.to_undirected()

        for face in self.data.graph[FACES]:
            #print('UPDATE FACE:', face, type(face))
            face_ = self.get_face(face)
            self.face_to_nodes[face].extend([self.get_node(node) for node in face])

            for i in range(len(face)):
                head, tail = face[i], face[(i + 1) % len(face)]

                node_ = self.get_node(head)
                edge_ = self.get_edge(head, tail)
                hedge = self.get_hedge(head, tail)
                self.face_to_edges[face].append(edge_)
                self.face_to_hedges[face].append(hedge)

                self.edge_to_faces[edge_].add(face_)

                self.hedge_to_face[hedge] = face_

                self.node_to_faces[node_].add(face_)

        for node in self.data.nodes:
            node_ = self.get_node(node)
            in_hedges = set(self.data.in_edges(node))
            self.node_to_in_hedges[node_].update([self.get_hedge(*hedge) for hedge in in_hedges])
            out_hedges = set(self.data.out_edges(node))
            self.node_to_out_hedges[node_].update([self.get_hedge(*hedge) for hedge in out_hedges])
            hedges = in_hedges | out_hedges
            self.node_to_hedges[node_].update([self.get_hedge(*hedge) for hedge in hedges])

        for hedge in self.data.edges:
            hedge_ = self.get_hedge(*hedge)
            self.hedge_to_nodes[hedge].add(hedge_.head)
            self.hedge_to_nodes[hedge].add(hedge_.tail)


        for head, tail in self.undirected_data.edges:
            head_ = self.get_node(head)
            tail_ = self.get_node(tail)

            edge_ = self.get_edge(head, tail)
            self.edge_to_nodes[edge_].add(head_)
            self.edge_to_nodes[edge_].add(tail_)

            # TODO: Test removing this - edges hash both ways.
            rev_edge_ = self.get_edge(tail, head)
            self.edge_to_nodes[rev_edge_].add(head_)
            self.edge_to_nodes[rev_edge_].add(tail_)

            if self.has_hedge(head, tail):
                self.edge_to_hedges.setdefault(edge_, set()).add(self.get_hedge(head, tail))
            if self.has_hedge(tail, head):
                self.edge_to_hedges.setdefault(edge_, set()).add(self.get_hedge(tail, head))

    @property
    def nodes(self) -> set[Node]:
        return {self.get_node(node) for node in self.data.nodes}

    @property
    def edges(self) -> set[Edge]:
        return {self.get_edge(*edge) for edge in self.undirected_data.edges}

    @property
    def hedges(self) -> set[Hedge]:
        return {self.get_hedge(*edge) for edge in self.data.edges}

    @property
    def faces(self) -> set[Face]:
        return {self.get_face(face) for face in self.data.graph[FACES]}

    def get_node(self, node) -> Node:
        assert node in self.data, f'Node not found: {node}'
        return Node(self, node)

    def get_edge(self, head, tail) -> Edge:
        assert (head, tail) in self.undirected_data.edges, f'Edge not found: {(head, tail)}'
        return Edge(self, (head, tail))

    def get_hedge(self, head, tail) -> Hedge:
        assert (head, tail) in self.data.edges, f'Half edge not found: {(head, tail)}'
        return Hedge(self, (head, tail))

    def get_face(self, face: tuple) -> Face:
        assert face in self.data.graph[FACES], f'Face not found: {face}'
        return Face(self, face)

    def has_node(self, node: Any):
        return node in self.data.nodes

    def has_hedge(self, head, tail):
        return (head, tail) in self.data.edges

    def add_node(self, node: Any, **node_attrs):
        default_node_attrs = self.get_node_default_attributes()
        default_node_attrs.update(node_attrs)
        self.data.add_node(node, **{ATTRIBUTES: default_node_attrs})

    def add_hedge(self, hedge: tuple[Any, Any], **hedge_attrs):
        default_hedge_attrs = self.get_hedge_default_attributes()
        default_hedge_attrs.update(hedge_attrs)
        self.data.add_edge(*hedge, **{ATTRIBUTES: default_hedge_attrs})

    def add_face(self, face: tuple[Any, ...], **face_attrs):
        default_face_attrs = self.get_face_default_attributes()
        default_face_attrs.update(face_attrs)
        self.data.graph[FACES][face] = {ATTRIBUTES: default_face_attrs}

    def remove_node(self, node: Any):
        self.data.remove_node(node)

    def remove_hedge(self, hedge: tuple[Any, Any]):
        self.data.remove_edge(*hedge)

    def remove_face(self, face: tuple[Any, ...]):
        del self.data.graph[FACES][face]

    def load(self, file_path: str | Path):
        with open(file_path, 'r') as f:
            g = json_graph.node_link_graph(json.load(f))

        # Build faces from comma-separated list.
        g.graph[FACES] = {
            tuple(face_nodes.split(', ')): face_attrs
            for face_nodes, face_attrs in g.graph[FACES].items()
        }

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
            json.dump(data, f, indent=2)
