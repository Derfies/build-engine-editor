import unittest

from editor.graph import Graph


class TestCaseBase(unittest.TestCase):

    @staticmethod
    def create_polygon(graph: Graph, *points: tuple[float, float]):
        num_nodes = len(points)
        num_existing_nodes = len(graph.data)
        nodes = tuple(range(num_existing_nodes, num_existing_nodes + num_nodes))
        for i, node in enumerate(nodes):
            graph.add_node(node, x=points[i][0], y=points[i][1])
        edges = [(nodes[i], nodes[(i + 1) % num_nodes]) for i in range(num_nodes)]
        for edge in edges:
            graph.add_edge(edge)
        graph.add_face(nodes)
        graph.update()
