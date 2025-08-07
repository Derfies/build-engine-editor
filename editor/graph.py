from __future__ import annotations
import abc
import json
import logging
from collections import defaultdict
from functools import singledispatchmethod
from typing import Any

import marshmallow_dataclass
import networkx as nx
from PySide6.QtCore import QPointF
from networkx.readwrite import json_graph

from applicationframework.contentbase import ContentBase
from editor import maths
from gameengines.build.map import Sector, Wall

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


logger = logging.getLogger(__name__)


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
    def get_attribute(self, key, default=None):
        ...

    @abc.abstractmethod
    def set_attribute(self, key, value):
        ...

    @property
    @abc.abstractmethod
    def nodes(self) -> tuple:
        ...

    @property
    def is_selected(self):
        return self.get_attribute('is_selected')

    @is_selected.setter
    def is_selected(self, value: bool):
        self.set_attribute('is_selected', value)


class Node(Element):

    def get_attribute(self, key, default=None):
        return self.graph.data.nodes[self.data].get(key, default)

    def set_attribute(self, key, value):
        self.graph.data.nodes[self.data][key] = value

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
        return self.get_attribute('pos')

    @pos.setter
    def pos(self, pos: QPointF):
        self.set_attribute('pos', pos)


class Edge(Element):

    def __hash__(self):
        return hash(frozenset(self.data))

    @singledispatchmethod
    def __contains__(self, node: Node):
        return node in self.nodes

    def get_attribute(self, key, default=None):
        return self.graph.undirected_data.edges[self.data].get(key, default)

    def set_attribute(self, key, value):
        self.graph.undirected_data.edges[self.data][key] = value

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

    def get_attribute(self, key, default=None):
        return self.graph.data.edges[self.data].get(key, default)

    def set_attribute(self, key, value):
        self.graph.data.edges[self.data][key] = value

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

    def get_attribute(self, key, default=None):
        return self.graph.data.graph['faces'][self].get(key, default)

    def set_attribute(self, key, value):
        self.graph.data.graph['faces'][self][key] = value

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

    def __init__(self):

        # TODO: Allow setting of whatever kind of graph we like.
        # TODO: Put this in a new method - it's already tripped me over once
        # during load / save
        self.data = nx.DiGraph()
        self.data.graph['faces'] = {}
        #self.data.graph['faces'] = {}

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

        for face in self.data.graph['faces']:
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
        return {self.get_face(face) for face in self.data.graph['faces']}

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
        assert face in self.data.graph['faces'], f'Face not found: {face}'
        return Face(self, face)

    def has_node(self, node: Any):
        return node in self.data.nodes

    def has_hedge(self, head, tail):
        return (head, tail) in self.data.edges

    def add_node(self, node: Any, **node_attrs):
        self.data.add_node(node, **node_attrs)

    def add_hedge(self, hedge: tuple[Any, Any], **hedge_attrs):
        self.data.add_edge(*hedge, **hedge_attrs)

    def add_face(self, face: tuple[Any, ...], **face_attrs):
        self.data.graph['faces'][face] = face_attrs

    def remove_node(self, node: Any):
        self.data.remove_node(node)

    def remove_hedge(self, hedge: tuple[Any, Any]):
        self.data.remove_edge(*hedge)

    def remove_face(self, face: tuple[Any, ...]):
        del self.data.graph['faces'][face]

    def load(self, file_path: str):
        """
        Feels pretty ugly. Can we use marshmallow better for this...?

        """
        def deserialize_attr(key, obj):
            if key == 'pos':
                return QPointF(*obj)
            elif key == 'wall':
                return Wall(**obj)
            else:
                return obj

        with open(file_path, 'r') as f:
            data = json_graph.node_link_graph(json.load(f))

        g = nx.DiGraph()
        for n, attrs in data.nodes(data=True):
            g.add_node(n, **{k: deserialize_attr(k, v) for k, v in attrs.items()})
        for u, v, attrs in data.edges(data=True):
            g.add_edge(u, v, **{k: deserialize_attr(k, v) for k, v in attrs.items()})
        g.graph['faces'] = {}
        for face_nodes, face_data in data.graph['faces'].items():
            nodes = face_nodes.split(', ')
            schema = marshmallow_dataclass.class_schema(Sector)()
            g.graph['faces'][tuple(nodes)] = {'sector': schema.load(face_data['sector'])}

        self.data = g
        self.update()

    def save(self, file_path: str):
        """
        Feels pretty ugly. Can we use marshmallow better for this...?

        """
        def serialize_attr(obj):
            if isinstance(obj, QPointF):
                return obj.to_tuple()
            elif isinstance(obj, Wall):
                schema = marshmallow_dataclass.class_schema(Wall)()
                return schema.dump(obj)
            elif isinstance(obj, Sector):
                schema = marshmallow_dataclass.class_schema(Sector)()
                return schema.dump(obj)
            elif isinstance(obj, list):
                return [serialize_attr(v) for v in obj]
            elif isinstance(obj, dict):
               return {k: serialize_attr(v) for k, v in obj.items()}
            else:
               return obj

        g = nx.DiGraph()
        g.graph['faces'] = {}
        for k, v in self.data.graph['faces'].items():
            g.graph['faces'][', '.join(k)] = serialize_attr(v)
        for n, attrs in self.data.nodes(data=True):
            g.add_node(n, **{k: serialize_attr(v) for k, v in attrs.items()})
        for u, v, attrs in self.data.edges(data=True):
            g.add_edge(u, v, **{k: serialize_attr(v) for k, v in attrs.items()})

        data = json_graph.node_link_data(g)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
