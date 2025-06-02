import logging

from applicationframework.contentbase import ContentBase
from editor.graph import Edge, MapGraph, Node, Poly
from gameengines.build.duke3d import MapReader as Duke3dMapReader
from gameengines.build.map import Map, Wall


logger = logging.getLogger(__name__)


class Content(ContentBase):

    # TODO: Combine the map class with this.

    def __init__(self):
        self.g = MapGraph(Map())

    def load(self, file_path: str):
        with open(file_path, 'rb') as f:
            m = Duke3dMapReader()(f)

        self.g = MapGraph(m)

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
        from collections import defaultdict


        wall_to_walls = defaultdict(set)
        for i, wall_data in enumerate(m.walls):
            wall_to_walls[i].add(i)
            if wall_data.nextwall > -1:
                nextwall_data = m.walls[wall_data.nextwall]
                wall_set = wall_to_walls.get(nextwall_data.point2, wall_to_walls[i])
                wall_set.add(i)
                wall_to_walls[i] = wall_to_walls[nextwall_data.point2] = wall_set

        # print('\nwall_to_wall')
        # for wall in sorted(wall_to_walls):
        #     print(wall, '->', wall_to_walls[wall])

        wall_to_node = dict()
        node_to_walls = defaultdict(set)
        for wall, other_walls in wall_to_walls.items():
            node = wall_to_node.get(wall)
            if node is None:
                node = wall_to_node[wall] = Node(m.walls[wall])
                self.g.add_node(node)


            for other_wall in other_walls:
                wall_to_node[other_wall] = node

            # BUG: Adding too many walls because they cannt be hashed.
            node_to_walls[node].update(other_walls)
            #node.walls.extend([m.walls[other_wall] for other_wall in other_walls])

        print('\nnode_to_walls:', len(node_to_walls))
        for node in node_to_walls:
            walls = node_to_walls[node]
            print(node, '->', walls)

            node.walls.extend([m.walls[other_wall] for other_wall in walls])

        # #return
        # #
        # # print('\nwall_to_node:', len(wall_to_node))
        # # for wall, node in wall_to_node.items():
        # #     print(wall, '->', node)
        # #
        # # print('\nwall_to_wall')
        # for wall, other_walls in wall_to_walls.items():
        #     #print(wall, '->', other_walls)
        #     wall_node = wall_to_node.get(wall)
        #
        #     # Bug is most likely here. Skipping something we need to connect.
        #     if wall_node is None:
        #         #print('    NO link:', wall)
        #         continue
        #
        #     wall_node.walls.append(m.walls[wall])
        #
        #     for other_wall in other_walls:
        #         #print('    link:', wall, '->', other_wall)
        #         wall_node.walls.append(m.walls[other_wall])
        #         wall_to_node[other_wall] = wall_node


        print('\nwall_to_node:', len(wall_to_node))
        for wall in sorted(wall_to_node):
            node = wall_to_node[wall]
            print(wall, '->', node, len(node.walls))

        #return

        edges = set()

        # Add edges.
        # BUG: Placing both half edges, I think
        for i, wall_data in enumerate(m.walls):
            node1 = wall_to_node.get(i)
            node2 = wall_to_node.get(wall_data.point2)

            if node1 is None or node2 is None:
                #print('CANNOT PLACE EDGE', i, wall_data.point2)
                continue

            edge = Edge(node1, node2, wall_data)


            print('edge:', edge.node1, edge.node2)
            if edge not in edges:
                self.g.add_edge(edge)
            else:
                print('already exists:', edge)

            edges.add(frozenset({i, wall_data.point2}))

        # Add sectors.
        for i, sector_data in enumerate(m.sectors):
            try:
                nodes = [
                    wall_to_node[sector_data.wallptr + i]
                    for i in range(sector_data.wallnum)
                ]
                self.g.polys.append(Poly(nodes, sector_data))
            except:
                print('Cannot place sector:', i)


    def save(self, file_path: str):
        raise NotImplementedError()


if __name__ == '__main__':
    c = Content()
    c.load(r'C:\Users\Jamie Davies\Documents\git\build-engine-editor\editor\tests\data\4_squares.map')
    #print(c.g.nodes)

    # print('\nnodes:', len(c.g.nodes))
    # for node in c.g.nodes:
    #     print(node)
    #     print('    ', node.walls)