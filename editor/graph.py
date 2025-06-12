from __future__ import annotations
import abc
import io
import logging
from collections import defaultdict
from functools import singledispatchmethod
from typing import Any

import networkx as nx
from PySide6.QtCore import QPointF

from applicationframework.contentbase import ContentBase
from gameengines.build.duke3d import MapReader as Duke3dMapReader, MapWriter, Map


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
        print("node:", node)
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

    # TODO: Dont inherit.

    # def __hash__(self):
    #     return hash(self.data)

    @singledispatchmethod
    def __contains__(self, node: Node):
        print("node:", node)
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


class Face(Element):

    @singledispatchmethod
    def __contains__(self, node: Node):
        print("node:", node)
        return node in self.nodes

    @__contains__.register
    def _(self, edge: Edge):
        print("edge:", edge, type(edge))
        return edge in self.edges

    @__contains__.register
    def _(self, hedge: Hedge):
        print("hedge:", hedge, type(hedge))
        return hedge in self.hedges

    def get_attribute(self, key, default=None):
        return self.graph._faces[self].get(key, default)

    def set_attribute(self, key, value):
        self.graph._faces[self][key] = value

    @property
    def nodes(self) -> tuple[Node]:
        return tuple(self.graph.face_to_nodes[self])

    @property
    def edges(self) -> tuple[Edge]:
        return tuple(self.graph.face_to_edges[self])

    @property
    def hedges(self) -> tuple[Hedge]:
        return tuple(self.graph.face_to_hedges[self])


class Graph(ContentBase):

    def __init__(self):

        # TODO: Allow setting of whatever kind of graph we like.
        self.data = nx.DiGraph()
        #self.update_undirected()
        self._faces = {}

        # Maps.
        self.node_to_edges = defaultdict(set)
        self.node_to_hedges = defaultdict(set)
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

        for face in self._faces:
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
            hedges = set(self.data.in_edges(node)) | set(self.data.out_edges(node))
            #print(node, '->', hedges)
            self.node_to_hedges[node_].update([self.get_hedge(*hedge) for hedge in hedges])


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
        return {self.get_face(face) for face in self._faces}

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
        assert face in self._faces, f'Face not found: {face}'
        return Face(self, face)

    def has_hedge(self, head, tail):
        return (head, tail) in self.data.edges




    def add_node(self, node: Any, **node_attrs):
        self.data.add_node(node, **node_attrs)

    def add_hedge(self, hedge: tuple[Any, Any], **hedge_attrs):
        self.data.add_edge(*hedge, **hedge_attrs)

    def add_face(self, face: tuple[Any, ...], **face_attrs):
        self._faces[face] = face_attrs




    def remove_node(self, node: Any):
        self.data.remove_node(node)

    def remove_hedge(self, hedge: tuple[Any, Any]):
        self.data.remove_edge(*hedge)

    def remove_face(self, face: tuple[Any, ...]):
        del self._faces[face]
    '''


    @singledispatchmethod
    def add_node(self, node_id: Any, **node_attrs):
        self.data.add_node(node_id, **node_attrs)

    @add_node.register
    def _(self, node: Node, **node_attrs):
        self.add_node(node.data, **node_attrs)

    @singledispatchmethod
    def add_edge(self, edge: tuple[Any, Any], **edge_attrs):
        self.data.add_edge(*edge, **edge_attrs)

    @add_edge.register
    def _(self, edge: Edge, **edge_attrs):
        self.add_edge(edge.data, **edge_attrs)




    #def add_edge(self, edge: Edge, **edge_attrs):
    #    self.data.add_edge(*edge.data, **edge_attrs)

    @singledispatchmethod
    def add_face(self, face: tuple, **face_attrs):

        # def add_face(self, face: Face | tuple, **face_attrs):
        # if isinstance(face, Face):
        #
        # edges = []
        # for i in range(len(face)):
        #     head = face[i]
        #     tail = face[(i + 1) % len(face)]
        #     edges.append((head, tail))
        # self.data.add_edges_from(edges)
        self._faces[face] = face_attrs

    @add_face.register
    def _(self, face: Face, **face_attrs):
        self.add_face(face.data)

    @singledispatchmethod
    def remove_node(self, node: Any):
        self.data.remove_node(node)

    @remove_node.register
    def _(self, node: Node):
        self.remove_node(node.data)

    @singledispatchmethod
    def remove_hedge(self, hedge: tuple[Any, Any]):
        self.data.remove_edge(*hedge)

    @remove_hedge.register
    def _(self, hedge: Hedge):
        self.remove_hedge(hedge.data)

    @singledispatchmethod
    def remove_face(self, face: tuple[Any, ...]):
        del self._faces[face]

    @remove_face.register
    def _(self, face: Face):
        self.remove_face(face.data)

    '''

    def load(self, file_path: str):

        self.data.clear()
        self.faces.clear()

        # TODO: Move this into an import function and let this serialize the native
        # map format.
        with open(file_path, 'rb') as f:
            m = Duke3dMapReader()(f)

        print('\nheader')
        print(m.header)

        print('\nwalls')
        for wall in m.walls:
            print(wall)

        print('\nsectors')
        for sector in m.sectors:
            print(sector)

        # Still not sure how this actually works :lol.
        wall_to_walls = defaultdict(set)
        for wall, wall_data in enumerate(m.walls):
            wall_to_walls[wall].add(wall)
            if wall_data.nextwall > -1:
                nextwall_data = m.walls[wall_data.nextwall]
                wall_set = wall_to_walls.get(nextwall_data.point2, wall_to_walls[wall])
                wall_set.add(wall)
                wall_to_walls[wall] = wall_to_walls[nextwall_data.point2] = wall_set

        print('\nwall_to_walls')
        for wall in sorted(wall_to_walls):
            print(wall, '->', wall_to_walls[wall])

        wall_to_node = {}
        nodes = set()
        for wall, other_walls in wall_to_walls.items():
            node = wall_to_node[wall] = frozenset(other_walls)
            nodes.add(node)
        


        for node in nodes:
            self.data.add_node(node)

        print('\nwall_to_node')
        for wall in sorted(wall_to_node):
            print(wall, '->', wall_to_node[wall])

        print('\nnodes')
        for node in self.data.nodes:
            print(node)

        # Add edges.
        for wall, wall_data in enumerate(m.walls):
            head = wall_to_node[wall]
            tail = wall_to_node[wall_data.point2]
            #print('CREATE:', head, '->', tail)
            self.data.add_edge(head, tail)

            # Need to set the head data.
            #self.data.nodes[head]['x'] = wall_data.x
            #self.data.nodes[head]['y'] = wall_data.y
            self.data.nodes[head]['pos'] = QPointF(wall_data.x, wall_data.y)
            self.data.edges[(head, tail)]['wall'] = wall_data



        print('\nedges')
        for edge in self.data.edges:
            print(edge)

        # Add sectors.

        # TODO: Change to edges to define polygon.
        for i, sector_data in enumerate(m.sectors):
            poly_nodes = []

            # This might not be right. I think this works on the assumption that
            # all sectors walls are written in order, which they're not guaranteed
            # to be.
            start_wall = wall = sector_data.wallptr
            for _ in range(sector_data.wallnum):
                wall_data = m.walls[wall]
                poly_nodes.append(wall_to_node[wall])
                wall = wall_data.point2

                if wall == start_wall:
                    #print('break')
                    break


            self._faces[tuple(poly_nodes)] = {'sector': sector_data}

        #'''

        print('\nfaces:', len(self.faces))
        for face in self.faces:
            print(face)
        #
        # # Create a mapping from old node names to ordinal numbers
        # mapping = {old_label: new_label for new_label, old_label in
        #            enumerate(self.data.nodes())}
        #
        # # Relabel the graph
        # self.data = nx.relabel_nodes(self.data, mapping)


        '''
        wall_to_walls = defaultdict(set)
        for i, wall_data in enumerate(m.walls):
            wall_to_walls[i].add(i)
            if wall_data.nextwall > -1:
                nextwall_data = m.walls[wall_data.nextwall]
                wall_set = wall_to_walls.get(nextwall_data.point2, wall_to_walls[i])
                wall_set.add(i)
                wall_to_walls[i] = wall_to_walls[nextwall_data.point2] = wall_set
        '''

        #self.update_undirected()
        self.update()

        print('\nnodes:')
        for node in self.nodes:
            print('    ->', node, node.pos)
        print('\nedges:')
        for edge in self.edges:
            print('    ->', edge)
        print('\nhedges:')
        for hedge in self.hedges:
            print('    ->', hedge, '->', hedge.face)
        print('\nfaces:')
        for face in self.faces:
            print('    ->', face)


    def save(self, file_path: str):

        METER = 512
        HEIGHT = 2 * METER

        m = Map()

        print('')


        wall_to_edge = []

        edges = []

        edge_map = {}


        wallptr = 0
        sector = 0
        for face in self.faces:

            sector_data = face.get_attribute('sector')
            sector_data.floorz = 0
            sector_data.ceilingz = -HEIGHT * 16
            sector_data.wallptr = wallptr
            sector_data.wallnum = len(face.data)


            #wall = 0
            for i, edge in enumerate(face.hedges):

                wall_data = edge.get_attribute('wall')
                wall_data.x = int(edge.head.pos.x())
                wall_data.y = int(edge.head.pos.y())
                wall_to_edge.append(edge)
                edges.append(edge)
                m.walls.append(wall_data)
                #wall += 1

                edge_map[edge] = face.hedges[(i + 1) % len(face.hedges)]




            m.sectors.append(sector_data)
            sector += 1

        m.cursectnum = 0

        print('\nedge_map:')
        for foo, bar in edge_map.items():
            print(foo, '->', bar)

        # Now we have all walls, go back through and fixup the point2.
        for wall, edge in enumerate(wall_to_edge):
            wall_data = m.walls[wall]

            next_edge = edge_map[edge]
            wall_data.point2 = edges.index(next_edge)#wall_to_edge.index(next_edge.get_attribute('wall'))

            #print('edge.tail.data:', edge.tail.data)
            #out_edges = self.data.out_edges(edge.tail.data)
            #print('out_edges:', out_edges)
            #point2 = self.data.edges(out)
            #print('point2:', point2)
            #wall_data.point2 = m.walls.index(edge.tail.get_attribute('wall'))

        print('\nheader')
        print(m.header)

        print('\nwalls')
        for wall in m.walls:
            print(wall)

        print('\nsectors')
        for sector in m.sectors:
            print(sector)

        output = io.BytesIO()
        MapWriter()(m, output)
        with open(file_path, 'wb') as f:
            #print(MAP_EXPORT_DIR_PATH)
            f.write(output.getbuffer())

