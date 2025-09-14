import unittest
from itertools import pairwise
from unittest.mock import Mock

from PySide6.QtWidgets import QApplication

from applicationframework.actions import Manager as ActionManager
from editor.document import Document
from editor.graph import Graph
from editor.updateflag import UpdateFlag


_instance = None


class TestCaseBase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        global _instance
        if _instance is None:
            _instance = QApplication([])
            _instance.action_manager = ActionManager()
            _instance.updated = Mock()
        cls.mock_app = _instance

    @classmethod
    def tearDownClass(cls):
        del cls.mock_app

    def setUp(self):
        super().setUp()
        self.mock_app.doc = Document(None, Graph(), UpdateFlag)

    @property
    def c(self):
        return self.mock_app.doc.content

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
