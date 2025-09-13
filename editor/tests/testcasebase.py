import unittest
from itertools import pairwise

import networkx as nx

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
    def build_grid(graph: Graph, w: int, h: int):

        g = nx.grid_2d_graph(w, h)

        nodes = {}
        for i, (x, y) in enumerate(g.nodes):
            nodes[(x, y)] = graph.add_node(i, x=x, y=y).data

        for head, tail in g.edges:
            graph.add_edge((nodes[head], nodes[tail]))

        for x1, x2 in pairwise(range(w)):
            for y1, y2 in pairwise(range(h)):
                face_nodes = [
                    nodes[(x1, y1)],
                    nodes[(x2, y1)],
                    nodes[(x2, y2)],
                    nodes[(x1, y2)],
                ]
                graph.add_face(tuple(face_nodes))
