import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication

from applicationframework.actions import Manager as ActionManager
from editor import commands
from editor.graph import Graph
from editor.mapdocument import MapDocument
from editor.updateflag import UpdateFlag


class ContentTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.mock_app = SimpleNamespace(action_manager=ActionManager(), updated=Mock())

    def setUp(self):
        self.mock_app.doc = MapDocument(None, Graph(), UpdateFlag)

    @property
    def c(self):
        return self.mock_app.doc.content

    def create_polygon(self, *points: list[QPointF]):
        num_nodes = len(points)
        num_existing_nodes = len(self.c.data)
        nodes = tuple(range(num_existing_nodes, num_existing_nodes + num_nodes))
        hedges = [(nodes[i], nodes[(i + 1) % num_nodes]) for i in range(num_nodes)]
        self.c.data.add_edges_from(hedges)
        for i, node in enumerate(nodes):
            self.c.get_node(node).pos = points[i]
        self.c.add_face(nodes)
        self.c.update()

    # def test_split_face(self):
    #     """
    #     +----+----+
    #     |    .    |
    #     |    .    |
    #     +----+----+
    #
    #     """
    #     # Set up test data.
    #     nodes = (0, 1, 2, 3)
    #     edges = ((0, 1), (1, 2), (2, 3), (3, 0))
    #     self.c.data.add_nodes_from(nodes)
    #     self.c.get_node(0).pos = QPointF(0, 0)
    #     self.c.get_node(1).pos = QPointF(1, 0)
    #     self.c.get_node(2).pos = QPointF(1, 1)
    #     self.c.get_node(3).pos = QPointF(0, 1)
    #
    #     #for node in nodes:
    #     #    self.c.data.add_node(node)
    #     #for edge in edges:
    #     #    self.c.data.add_edge(*edge)
    #     self.c.data.add_edges_from(edges)
    #     self.c._faces[nodes] = {}
    #     self.c.update_undirected()
    #
    #     # print('content edges:')
    #     # for n in self.c.data.edges:
    #     #    print('->', n)
    #
    #     # Start test.
    #     e1 = self.c.get_hedge((0, 1))
    #     e2 = self.c.get_hedge((2, 3))
    #
    #     # print(e1.head.pos)
    #     # print(e1.tail.pos)
    #     # print(e2.head.pos)
    #     # print(e2.tail.pos)
    #     with patch.object(QApplication, 'instance', return_value=self.mock_app):
    #         commands.split_face((e1, 0.5), (e2, 0.5))
    #     #
    #     # print('\nnodes:')
    #     # for n in self.c.nodes:
    #     #     print('->', n)
    #     #
    #     # print('\nedges:')
    #     # for n in self.c.edges:
    #     #     print('->', n)
    #     #
    #     # print('\nfaces:')
    #     # for n in self.c.faces:
    #     #     print('->', n)
    #
    #     # Assert results.
    #     self.assertEqual(len(self.c.nodes), 6)
    #     self.assertEqual(len(self.c.edges), 7)
    #     self.assertEqual(len(self.c.hedges), 8)
    #     self.assertEqual(len(self.c.faces), 2)

    def test_join_edges_single(self):

        # TODO: Test face / edge data is retained.
        """
        1           2   5           6
          ┌───────┐       ┌───────┐
          │       │       │       │
          │       │       │       │
          │       │       │       │
          └───────┘       └───────┘
        0           3   4           7

                      ↓

        1             A            6
          ┌───────────┬──────────┐
          │           │          │
          │           │          │
          │           │          │
          └───────────┴──────────┘
        0             B            7

        """
        # Set up test data.
        self.create_polygon(
            QPointF(0, 0),
            QPointF(0, 1),
            QPointF(1, 1),
            QPointF(1, 0),
        )
        self.create_polygon(
            QPointF(2, 0),
            QPointF(2, 1),
            QPointF(3, 1),
            QPointF(3, 0),
        )

        # Start test.
        e1 = self.c.get_hedge(2, 3)
        e2 = self.c.get_hedge(4, 5)
        with patch.object(QApplication, 'instance', return_value=self.mock_app), \
                patch.object(uuid, 'uuid4', side_effect=('A', 'B')):
            add_tweak, rem_tweak = commands.join_edges(e1, e2)

        # Assert results.
        self.assertSetEqual(rem_tweak.nodes, {2, 3, 4, 5})
        self.assertSetEqual(add_tweak.nodes, {'A', 'B'})
        self.assertSetEqual(rem_tweak.hedges, {(1, 2), (2, 3), (3, 0), (7, 4), (4, 5), (5, 6)})
        self.assertSetEqual(add_tweak.hedges, {(1, 'A'), ('A', 'B'), ('B', 0), (7, 'B'), ('B', 'A'), ('A', 6)})
        self.assertSetEqual(rem_tweak.faces, {(0, 1, 2, 3), (4, 5, 6, 7)})
        self.assertSetEqual(add_tweak.faces, {(0, 1, 'A', 'B'), ('B', 'A', 6, 7)})
        self.assertEqual(rem_tweak.node_attrs[2]['pos'], QPointF(1, 1))
        self.assertEqual(rem_tweak.node_attrs[3]['pos'], QPointF(1, 0))
        self.assertEqual(rem_tweak.node_attrs[4]['pos'], QPointF(2, 0))
        self.assertEqual(rem_tweak.node_attrs[5]['pos'], QPointF(2, 1))
        self.assertEqual(add_tweak.node_attrs['A']['pos'], QPointF(1.5, 1))
        self.assertEqual(add_tweak.node_attrs['B']['pos'], QPointF(1.5, 0))

    def test_join_edges_double(self):
        # TODO: Test face / edge data is retained.
        """
        2           3   8           9
          ┌───────┐       ┌───────┐
          │       │       │       │
          │       │       │       │
        1 │       │ 4   7 │       │ 10
          │       │       │       │
          │       │       │       │
          └───────┘       └───────┘
        0           5   6           11

                      ↓

        2             A             9
          ┌───────────┬───────────┐
          │           │           │
          │           │           │
        1 │           │B          │ 10
          │           │           │
          │           │           │
          └───────────┴───────────┘
        0             C             11

        """
        # Set up test data.
        self.create_polygon(
            QPointF(0, 0),
            QPointF(0, 0.5),
            QPointF(0, 1),
            QPointF(1, 1),
            QPointF(1, 0.5),
            QPointF(1, 0),
        )
        self.create_polygon(
            QPointF(2, 0),
            QPointF(2, 0.5),
            QPointF(2, 1),
            QPointF(3, 1),
            QPointF(3, 0.5),
            QPointF(3, 0),
        )

        # Start test.
        e1 = self.c.get_hedge(3, 4)
        e2 = self.c.get_hedge(4, 5)
        e3 = self.c.get_hedge(6, 7)
        e4 = self.c.get_hedge(7, 8)
        with patch.object(QApplication, 'instance', return_value=self.mock_app), \
                patch.object(uuid, 'uuid4', side_effect=('C', 'B', 'A')):
            add_tweak, rem_tweak = commands.join_edges(e1, e2, e3, e4)

        # Assert results.
        self.assertSetEqual(rem_tweak.nodes, {3, 4, 5, 6, 7, 8})
        self.assertSetEqual(add_tweak.nodes, {'A', 'B', 'C'})
        self.assertSetEqual(rem_tweak.hedges, {(2, 3), (3, 4), (4, 5), (5, 0), (11, 6), (6, 7), (7, 8), (8, 9)})
        self.assertSetEqual(add_tweak.hedges, {(2, 'A'), ('A', 'B'), ('B', 'C'), ('C', 0), (11, 'C'), ('C', 'B'), ('B', 'A'), ('A', 9)})
        self.assertSetEqual(rem_tweak.faces, {(0, 1, 2, 3, 4, 5), (6, 7, 8, 9, 10, 11)})
        self.assertSetEqual(add_tweak.faces, {(0, 1, 2, 'A', 'B', 'C'), ('C', 'B', 'A', 9, 10, 11)})
        self.assertEqual(rem_tweak.node_attrs[3]['pos'], QPointF(1, 1))
        self.assertEqual(rem_tweak.node_attrs[4]['pos'], QPointF(1, 0.5))
        self.assertEqual(rem_tweak.node_attrs[5]['pos'], QPointF(1, 0))
        self.assertEqual(rem_tweak.node_attrs[6]['pos'], QPointF(2, 0))
        self.assertEqual(rem_tweak.node_attrs[7]['pos'], QPointF(2, 0.5))
        self.assertEqual(rem_tweak.node_attrs[8]['pos'], QPointF(2, 1))
        self.assertEqual(add_tweak.node_attrs['A']['pos'], QPointF(1.5, 1))
        self.assertEqual(add_tweak.node_attrs['B']['pos'], QPointF(1.5, 0.5))
        self.assertEqual(add_tweak.node_attrs['C']['pos'], QPointF(1.5, 0))
