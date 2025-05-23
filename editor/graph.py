class Graph:

    def __init__(self):
        self.nodes = {}
        self.edges = {}
        self.polygons = []

    def add_node(self, node, **attrs):
        self.nodes[node] = attrs

    def add_edge(self, node1, node2, **attrs):
        self.add_node(node1)
        self.add_node(node2)
        self.edges[(node1, node2)] = attrs

    def add_polygon(self, polygon_nodes):
        if not all(node in self.nodes for node in polygon_nodes):
            raise ValueError('All nodes in the polygon must exist in the graph.')
        if polygon_nodes[0] != polygon_nodes[-1]:
            raise ValueError('Polygons must be closed (start and end node must be the same).')
        self.polygons.append(polygon_nodes)

    def __str__(self):
        return (f'Graph:\n'
                f' {len(self.nodes)} Nodes: {self.nodes}\n'
                f' Edges: {self.edges}\n'
                f' Polygons: {self.polygons}')
