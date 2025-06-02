import abc

from gameengines.build.map import Sector, Sprite, Wall


class ElementBase(metaclass=abc.ABCMeta):

    def __init__(self, data: Sector | Sprite | Wall):
        self._data = data
        self.is_selected = False

    @property
    def data(self) -> Sector | Sprite | Wall:
        return self._data

    @property
    @abc.abstractmethod
    def nodes(self) -> list['Node']:
        ...


class Node(ElementBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.walls = []

    @property
    def nodes(self) -> list['Node']:
        return [self]

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

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return hash(self) == hash(other)

    def __hash__(self):

        # Ensures half edges are not treated as separate objects by the graph.
        return hash(frozenset({self.node1, self.node2}))

    @property
    def nodes(self) -> list['Node']:
        return [self.node1, self.node2]

    @property
    def x(self):
        return self._data.x

    @property
    def y(self):
        return self._data.y


class Poly(ElementBase):

    def __init__(self, edges: list[Edge], *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.edges = edges

    @property
    def nodes(self) -> list['Node']:
        return [edge.node1 for edge in self.edges]


class Graph:

    def __init__(self):
        self.nodes = set()
        self.edges = set()
        self.polys = set()

    def add_node(self, node: Node):
        self.nodes.add(node)

    def add_edge(self, edge: Edge):
        if edge.node1 not in self.nodes:
            self.add_node(edge.node1)
        if edge.node2 not in self.nodes:
            self.add_node(edge.node2)
        self.edges.add(edge)

    def add_poly(self, poly: Poly):

        # Ok so the problem of defining a polygon like this is that the edge
        # needs to be in the correct head -> tail order, but we're not storing
        # half edges in the graph (on purpose)... hmmm
        for edge in poly.edges:
            self.add_edge(edge)
        self.polys.add(poly)

    # TODO: Add these sorts of methods to the Content object so different map
    # formats can be supported.
    def new_poly(self):
        pass
