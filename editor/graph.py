from __future__ import annotations
import abc
import io
import logging
from collections import defaultdict
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
    def node(self):
        return self.graph.get_node(self.data)

    @property
    def nodes(self) -> tuple:
        return (self.node, )

    @property
    def pos(self) -> QPointF:
        return self.get_attribute('pos')

    @pos.setter
    def pos(self, pos: QPointF):
        self.set_attribute('pos', pos)


class Edge(Element):

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
    def nodes(self) -> tuple:
        return self.data

    @property
    def hedges(self) -> set:

        # TODO: Replace with hashmap on graph obj?
        hedges = set()
        head, tail = self.data
        if self.graph.has_hedge((head, tail)):
            hedges.add(self.graph.get_hedge((head, tail)))
        if self.graph.has_hedge((tail, head)):
            hedges.add(self.graph.get_hedge((tail, head)))
        # head, tail = self.data
        # if (head, tail) in self.graph.data.edges:
        #     hedges.append(Hedge(self.graph, (head, tail)))
        # if (tail, head) in self.graph.data.edges:
        #     hedges.append(Hedge(self.graph, (tail, head)))
        return hedges
    #
    # @property
    # def faces


class Hedge(Edge):

    def get_attribute(self, key, default=None):
        return self.graph.data.edges[self.data].get(key, default)

    def set_attribute(self, key, value):
        self.graph.data.edges[self.data][key] = value

    @property
    def face(self) -> Face | None:

        # TODO: Cache property.
        #return Face(self.graph, face)
        return next((face for face in self.graph.faces if self in face), None)


class Face(Element):

    # def __in__(self, obj: Hedge):
    #     if not isinstance(obj, Hedge):
    #         raise
    #     return obj in self.hedges
    def __contains__(self, item):

        if not isinstance(item, Hedge):
            raise
        return item in self.hedges


    def get_attribute(self, key, default=None):
        return self.graph._faces[self].get(key, default)

    def set_attribute(self, key, value):
        self.graph._faces[self][key] = value

    @property
    def nodes(self) -> tuple:
        return self.data

    @property
    def hedges(self) -> tuple[Hedge]:

        # TODO: Cache property
        hedges = []
        for i in range(len(self.data)):
            hedge = (self.data[i], self.data[(i + 1) % len(self.data)])
            hedges.append(self.graph.get_hedge(hedge))
        return tuple(hedges)


class Graph(ContentBase):

    def __init__(self):

        # TODO: Allow setting of whatever kind of graph we like.
        self.data = nx.DiGraph()
        self.update_undirected()
        self._faces = {}

    @property
    def nodes(self) -> set[Node]:
        return {self.get_node(node) for node in self.data.nodes}

    @property
    def edges(self) -> set[Edge]:
        return {self.get_edge(edge) for edge in self.undirected_data.edges}

    @property
    def hedges(self) -> set[Hedge]:
        return {self.get_hedge(edge) for edge in self.data.edges}

    @property
    def faces(self) -> set[Face]:
        return {self.get_face(face) for face in self._faces}

    def get_node(self, node) -> Node:
        assert node in self.data, f'Node not found: {node}'
        return Node(self, node)

    def get_edge(self, edge: tuple[Any, Any]) -> Edge:
        assert edge in self.undirected_data.edges, f'Edge not found: {edge}'
        return Edge(self, edge)

    def get_hedge(self, edge) -> Hedge:
        assert edge in self.data.edges, f'Half edge not found: {edge}'
        return Hedge(self, edge)

    def get_face(self, face: tuple) -> Face:
        assert face in self._faces, f'Face not found: {face}'
        return Face(self, face)

    def has_hedge(self, hedge: tuple[Any, Any]):
        return hedge in self.data.edges

    def update_undirected(self):
        self.undirected_data = self.data.to_undirected()

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

        self.update_undirected()


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

