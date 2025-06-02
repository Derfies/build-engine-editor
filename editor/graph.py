import abc
from collections import defaultdict

from gameengines.build.map import Map, Sector, Sprite, Wall


class ElementBase(metaclass=abc.ABCMeta):

    def __init__(self, data: Sector | Sprite | Wall):
        # self._index = index
        self._data = data
        self.is_selected = False

    # def __eq__(self, other):
    #     if not isinstance(other, self.__class__):
    #         return NotImplemented
    #     return hash(self) == hash(other)

    # @property
    # def index(self) -> int:
    #     return self._index

    @property
    def data(self) -> Sector | Sprite | Wall:
        return self._data

    @property
    @abc.abstractmethod
    def nodes(self) -> set:
        ...


class Node(ElementBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        #self.wall_idxs = set()#self._index}

        self.walls = []

    # def __hash__(self):
    #     return hash(self._index)

    @property
    def nodes(self) -> set:
        return {self}

    @property
    def x(self):
        return self._data.x

    @property
    def y(self):
        return self._data.y


class Edge(ElementBase):

    def __init__(self, node1: Node, node2: Node, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.node1 = node1
        self.node2 = node2

    def __hash__(self):
        return hash(frozenset(self.nodes))

    @property
    def nodes(self) -> set:
        return {self.node1, self.node2}

    @property
    def x(self):
        return self._data.x

    @property
    def y(self):
        return self._data.y


class Poly(ElementBase):

    def __init__(self, nodes: list[Node], *args, **kwargs):
        super().__init__(*args, **kwargs)

        #print('nodes', nodes, args, kwargs)

        # TODO: Figure out whether to store as set / list
        self._nodes = nodes

    def __hash__(self):
        return hash(frozenset(self.nodes))

    @property
    def nodes(self) -> set:
        return set(self._nodes)


class Graph:

    def __init__(self):
        self.nodes = set()
        self.edges = set()
        self.polys = []

    def add_node(self, node: Node):
        self.nodes.add(node)

    def add_edge(self, edge: Edge):
        if edge.node1 not in self.nodes:
            self.add_node(edge.node1)
        if edge.node2 not in self.nodes:
            self.add_node(edge.node2)
        self.edges.add(edge)

    # def add_poly(self, poly: Poly):
    #
    #     print(poly._nodes)
    #
    #     # TODO: Add edges.
    #     for node in poly._nodes:
    #         print(node, self.nodes)
    #         if node not in self.nodes:
    #             print('ADD NODE:', node)
    #             self.add_node(node)
    #
    #     # Guh. Should the poly hold its own edges too? Or *just* its edges and
    #     # not nodes?
    #     import uuid
    #     for i in range(len(poly._nodes)):
    #         edge = Edge(poly._nodes[i], poly._nodes[(i + 1) % len(poly._nodes)], str(uuid.uuid4()), Wall())
    #         if edge not in self.edges:
    #             print('ADD EDGE:', edge)
    #             self.add_edge(edge)
    #     self.polys.append(poly)


class MapGraph(Graph):

    def __init__(self, map: Map):
        super().__init__()
        self._map = map

    # def add_wall_node(self, wall: int):
    #     map_ = defaultdict(set)
    #     wall_data = self._map.walls[wall]
    #     if wall_data.nextwall < 0:
    #         node = Node(wall_data)
    #         self.add_node(node)
    #     else:
    #
    #         nextwall_data = self._map.walls[wall_data.nextwall]
    #         map_[wall].add(nextwall_data.point2)
    #         #other_node = self.wall_to_node(nextwall_data.point2)
    #         # if other_node is None:
    #         #     other_node = Node(nextwall_data.point2, wall_data)
    #         #     self.add_node(other_node)
    #         # else:
    #         #     other_node.wall_idxs.add(nextwall_data.point2)
    #         #other_node.wall_idxs.add(wall)
    #     #if other_node is None:
    #     #    self.add_node(Node( wall_data))
    #
    #     for wall, other_wall in map_.items():
    #         print(wall, '->', other_wall)



    # def add_wall_edge(self, wall: int):
    #     wall_data = self._map.walls[wall]
    #     node1 = self.wall_to_node(wall)
    #     node2 = self.wall_to_node(wall_data.point2)
    #     assert node1 is not None, f'node1 is None: {wall}'
    #     assert node2 is not None, f'node2 is None: {wall_data.point2}'
    #     self.add_edge(Edge(node1, node2, wall, wall_data))
    #
    # def wall_to_node(self, wall: int):
    #
    #     # TODO: Use map?
    #     for node in self.nodes:
    #         if wall in node.wall_idxs:
    #             return node
    #     return None

    def add_sector(self, sector: int):
        sector_data = self._map.sectors[sector]
        nodes = [
            self.wall_to_node(sector_data.wallptr + i)
            for i in range(sector_data.wallnum)
        ]
        self.add_poly(Poly(nodes, sector, sector_data))

    # TODO:
    def new_poly(self):
        pass