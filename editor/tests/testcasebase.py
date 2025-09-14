import unittest
from itertools import pairwise

from editor.graph import Graph


class TestCaseBase(unittest.TestCase):

    @staticmethod
    def create_polygon(graph: Graph, *rings: tuple[tuple[float, float], ...]):
        all_nodes = []
        for points in rings:
            num_nodes = len(points)
            num_existing_nodes = len(graph.data)
            nodes = tuple(range(num_existing_nodes, num_existing_nodes + num_nodes))
            for i, node in enumerate(nodes):
                graph.add_node(node, x=points[i][0], y=points[i][1])
            edges = [(nodes[i], nodes[(i + 1) % num_nodes]) for i in range(num_nodes)]
            for edge in edges:
                graph.add_edge(edge)
            all_nodes.extend(nodes)
            all_nodes.append(nodes[0])  # To close polygon.
        face = graph.add_face(tuple(all_nodes))
        graph.update()
        return face

    @staticmethod
    def build_grid(graph: Graph, w: int, h: int, offset_x: int = 0, offset_y: int = 0):
        nodes = {}
        for x in range(offset_x, w + offset_x):
            for y in range(offset_y, h + offset_y):
                nodes[(x, y)] = graph.add_node(len(graph.nodes), x=x, y=y).data
        for x1, x2 in pairwise(range(offset_x, w + offset_x)):
            for y1, y2 in pairwise(range(offset_y, h + offset_y)):
                face_nodes = [
                    nodes[(x1, y1)],
                    nodes[(x2, y1)],
                    nodes[(x2, y2)],
                    nodes[(x1, y2)],
                ]
                for i in range(len(face_nodes)):
                    graph.add_edge((face_nodes[i], face_nodes[(i + 1) % len(face_nodes)]))
                graph.add_face(tuple(face_nodes + [face_nodes[0]]))
        graph.update()
