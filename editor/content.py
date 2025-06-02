import logging
from collections import defaultdict

from applicationframework.contentbase import ContentBase
from editor.graph import Edge, Graph, Node, Poly
from gameengines.build.duke3d import MapReader as Duke3dMapReader, MapWriter as Duke3dMapWriter
from gameengines.build.map import Map


logger = logging.getLogger(__name__)


class Content(ContentBase):

    # TODO: Combine the map class with this.

    def __init__(self):
        self.g = Graph()

    def load(self, file_path: str):
        with open(file_path, 'rb') as f:
            m = Duke3dMapReader()(f)

        self.g = Graph()

        """
        In this example, i would expect 6 nodes and 7 edges.
        nodes (walls) 1 and 4(?) are the same.
        nodes (walls) 2 and 7(?) are the same.
        
        To get from 1 to 4, I take the nextwall's point2.
        This makes sense because the next wall is the tail of this head for the 
        opposing sector, so that tail would be the equivalent of this point.
        
        To get from 7 to 2, I take the nextwall's point2.
        
        walls 1 and 7 are the same...
        
        """

        wall_to_walls = defaultdict(set)
        for i, wall_data in enumerate(m.walls):
            print('READ:', wall_data)
            wall_to_walls[i].add(i)
            if wall_data.nextwall > -1:
                nextwall_data = m.walls[wall_data.nextwall]
                wall_set = wall_to_walls.get(nextwall_data.point2, wall_to_walls[i])
                wall_set.add(i)
                wall_to_walls[i] = wall_to_walls[nextwall_data.point2] = wall_set


        wall_to_node = dict()
        node_to_walls = defaultdict(set)
        for wall, other_walls in wall_to_walls.items():
            node = wall_to_node.get(wall)
            if node is None:
                node = wall_to_node[wall] = Node(m.walls[wall])
                self.g.add_node(node)
            for other_wall in other_walls:
                wall_to_node[other_wall] = node
            node_to_walls[node].update(other_walls)

        for node in node_to_walls:
            walls = node_to_walls[node]
            node.walls.extend([m.walls[other_wall] for other_wall in walls])


        edges = {}

        # Add edges.
        for i, wall_data in enumerate(m.walls):
            node1 = wall_to_node[i]
            node2 = wall_to_node[wall_data.point2]

            # Dont check edges based on wall id - that's different for each
            # we need to translate back to node and check there instead
            edge = Edge(node1, node2, wall_data)
            if (node1, node2) not in edges:
                self.g.add_edge(edge)
                edges[(node1, node2)] = edge

                # But don't add this one to the graph.
                edges[(node2, node1)] = Edge(node2, node1, wall_data)


        # Add sectors.
        # TODO: Change to edges to define polygon.
        for i, sector_data in enumerate(m.sectors):
            poly_edges = []
            for i in range(sector_data.wallnum):
                wall = sector_data.wallptr + i
                wall_data = m.walls[wall]
                point2 = wall_data.point2

                # BUG: Using the wrong x / y coord. Maybe because we're not
                # selecting the right node?
                node1 = wall_to_node[wall]
                node2 = wall_to_node[point2]

                # Ok I think it's this guy. The nodes are back to front because
                # we're losing the order here...
                # Ok order is now correct but we're adding half edges back to the
                # graph when adding the polygon!
                edge = edges[(node1, node2)]
                poly_edges.append(edge)

            self.g.add_poly(Poly(poly_edges, sector_data))

    def save(self, file_path: str):
        #raise NotImplementedError()

        edge_map = {}
        m = Map()
        for wall, edge in enumerate(self.g.edges):
            m.walls.append(edge.data)
            edge_map[wall] = edge

        # Now ensure wall point2 is calculated correctly
        for wall, wall_data in enumerate(m.walls):
            wall_data.point2 = edge_map[wall].node2.data


        with open(file_path, 'wb') as f:
            m = Duke3dMapWriter()(m, f)


if __name__ == '__main__':
    c = Content()
    c.load(r'C:\Users\Jamie Davies\Documents\git\build-engine-editor\editor\tests\data\4_squares.map')
