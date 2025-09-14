import unittest
import uuid
from unittest.mock import Mock, patch

from PySide6.QtWidgets import QApplication

from applicationframework.actions import Manager as ActionManager
from editor import commands
from editor.document import Document
from editor.graph import Graph
from editor.tests.testcasebase import TestCaseBase
from editor.updateflag import UpdateFlag


_instance = None


class UsesQApplication(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        global _instance
        if _instance is None:
            _instance = QApplication([])
            _instance.action_manager = ActionManager()
            _instance.updated=Mock()
        cls.mock_app = _instance

    @classmethod
    def tearDownClass(cls):
        del cls.mock_app


class CommandsTestCase(UsesQApplication, TestCaseBase):

    def setUp(self):
        super().setUp()
        self.mock_app.doc = Document(None, Graph(), UpdateFlag)

    @property
    def c(self):
        return self.mock_app.doc.content

    def test_add_node(self):

        # Start test.
        with patch.object(uuid, 'uuid4', side_effect=('A')):
            add_tweak, _ = commands.add_node((1, 2))

        # Assert results.
        self.assertSetEqual(add_tweak.nodes, {'A'})
        self.assertEqual((add_tweak.node_attrs['A']['x'], add_tweak.node_attrs['A']['y']), (1, 2))

    def test_add_edges(self):

        # Start test.
        with patch.object(uuid, 'uuid4', side_effect=('A', 'B')):
            add_tweak, _ = commands.add_edges(((1, 2), (3, 4)))

        # Assert results.
        self.assertSetEqual(add_tweak.nodes, {'A', 'B'})
        self.assertEqual((add_tweak.node_attrs['A']['x'], add_tweak.node_attrs['A']['y']), (1, 2))
        self.assertEqual((add_tweak.node_attrs['B']['x'], add_tweak.node_attrs['B']['y']), (3, 4))
        self.assertIn(('A', 'B'), add_tweak.edges)

    def test_add_polygon(self):
        """
        1           2
          ┌───────┐
          │       │
          │       │
          │       │
          └───────┘
        0           3

        """
        # Set up test data.
        points = (((0, 0), (0, 1), (1, 1), (1, 0)))

        # Start test.
        with patch.object(uuid, 'uuid4', side_effect=('A', 'B', 'C', 'D')):
            add_tweak, _ = commands.add_polygon(points)

        # Assert results.
        # NOTE: Winding order was different to input since we wind CC be default.
        self.assertSetEqual(add_tweak.nodes, {'A', 'B', 'C', 'D'})
        self.assertSetEqual(add_tweak.edges, {('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')})
        self.assertSetEqual(add_tweak.faces, {('A', 'B', 'C', 'D', 'A')})
        self.assertEqual((add_tweak.node_attrs['A']['x'], add_tweak.node_attrs['A']['y']), (0, 0))
        self.assertEqual((add_tweak.node_attrs['B']['x'], add_tweak.node_attrs['B']['y']), (1, 0))
        self.assertEqual((add_tweak.node_attrs['C']['x'], add_tweak.node_attrs['C']['y']), (1, 1))
        self.assertEqual((add_tweak.node_attrs['D']['x'], add_tweak.node_attrs['D']['y']), (0, 1))

    def test_remove_elements_edge(self):
        """
        Remove edge (0, 1). Effectively a no-op because this element cannot be
        removed without removing additional elements.

        1           2
          ┌───────┐
          │       │
          │       │
          │       │
          └───────┘
        0           3

              ↓

        1           2
          ┌───────┐
          │       │
          │       │
          │       │
          └───────┘
        0           3

        """

    def test_delete_elements_node(self):
        """
        Remove node 0 which destroys the entire face including all edges and nodes.

        1           3
          ┌───────┐
          │       │
          │       │   →    NOTHING
          │       │
          └───────┘
        0           2

        """
        # Set up test data.
        self.build_grid(self.c, 2, 2)

        # Start test.
        node = self.c.get_node(0)
        add_tweak, rem_tweak = commands.delete_elements(node)

        # Assert results.
        self.assertSetEqual(rem_tweak.nodes, {0, 1, 2, 3})
        self.assertSetEqual(rem_tweak.edges, {(0, 2), (2, 3), (3, 1), (1, 0)})
        self.assertSetEqual(rem_tweak.faces, {(0, 2, 3, 1, 0)})

    def test_delete_elements_node_joined_face(self):
        """
        Remove node 4 which destroys only the face with that node, including all
        edges and nodes.

        1         3         5   1           3
          ┌───────┬───────┐       ┌───────┐
          │       │       │       │       │
          │       │       │   →   │       │
          │       │       │       │       │
          └───────┴───────┘       └───────┘
        0         2         4   0           2

        """
        # Set up test data.
        self.build_grid(self.c, 3, 2)

        # Start test.
        node = self.c.get_node(4)
        add_tweak, rem_tweak = commands.delete_elements(node)

        # Assert results.
        self.assertSetEqual(rem_tweak.nodes, {4, 5})
        self.assertSetEqual(rem_tweak.edges, {(2, 4), (4, 5), (5, 3), (3, 2)})
        self.assertSetEqual(rem_tweak.faces, {(2, 4, 5, 3, 2)})

    def test_delete_elements_edge(self):
        """
        Remove edge 0, 2 which destroys the entire face including all edges and nodes.

        1           3
          ┌───────┐
          │       │
          │       │   →    NOTHING
          │       │
          └───────┘
        0           2

        """
        # Set up test data.
        self.build_grid(self.c, 2, 2)

        # Start test.
        edge = self.c.get_edge(0, 2)
        add_tweak, rem_tweak = commands.delete_elements(edge)

        # Assert results.
        self.assertSetEqual(rem_tweak.nodes, {0, 1, 2, 3})
        self.assertSetEqual(rem_tweak.edges, {(0, 2), (2, 3), (3, 1), (1, 0)})
        self.assertSetEqual(rem_tweak.faces, {(0, 2, 3, 1, 0)})

    def test_delete_elements_face(self):
        """
        Remove face 0, 2, 3, 1, 0 which destroys the entire face including all edges and nodes.

        1           3
          ┌───────┐
          │       │
          │       │   →    NOTHING
          │       │
          └───────┘
        0           2

        """
        # Set up test data.
        self.build_grid(self.c, 2, 2)

        # Start test.
        face = self.c.get_face((0, 2, 3, 1, 0))
        add_tweak, rem_tweak = commands.delete_elements(face)

        # Assert results.
        self.assertSetEqual(rem_tweak.nodes, {0, 1, 2, 3})
        self.assertSetEqual(rem_tweak.edges, {(0, 2), (2, 3), (3, 1), (1, 0)})
        self.assertSetEqual(rem_tweak.faces, {(0, 2, 3, 1, 0)})

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
    #     e1 = self.c.get_edge((0, 1))
    #     e2 = self.c.get_edge((2, 3))
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
    #     self.assertEqual(len(self.c.edges), 8)
    #     self.assertEqual(len(self.c.faces), 2)

    def test_join_edges_single(self):

        # TODO: Test face / edge data is retained.
        """
        1           3   5           7
          ┌───────┐       ┌───────┐
          │       │       │       │
          │       │       │       │
          │       │       │       │
          └───────┘       └───────┘
        0           2   4           6

                      ↓

        1             A             7
          ┌───────────┬───────────┐
          │           │           │
          │           │           │
          │           │           │
          └───────────┴───────────┘
        0             B             6

        """
        # Set up test data.
        self.build_grid(self.c, 2, 2)
        self.build_grid(self.c, 2, 2, offset_x=2)

        # Start test.
        e1 = self.c.get_edge(2, 3)
        e2 = self.c.get_edge(5, 4)
        with patch.object(uuid, 'uuid4', side_effect=('B', 'A')):
            add_tweak, rem_tweak = commands.join_edges(e1, e2)

        # Assert results.
        self.assertSetEqual(rem_tweak.nodes, {2, 3, 4, 5})
        self.assertSetEqual(add_tweak.nodes, {'A', 'B'})
        self.assertSetEqual(rem_tweak.edges, {(0, 2), (2, 3), (3, 1), (7, 5), (5, 4), (4, 6)})
        self.assertSetEqual(add_tweak.edges, {(0, 'B'), ('B', 'A'), ('A', 1), (7, 'A'), ('A', 'B'), ('B', 6)})
        self.assertSetEqual(rem_tweak.faces, {(0, 2, 3, 1, 0), (4, 6, 7, 5, 4)})
        self.assertSetEqual(add_tweak.faces, {(0, 'B', 'A', 1, 0), ('B', 6, 7, 'A', 'B')})
        self.assertEqual((rem_tweak.node_attrs[2]['x'], rem_tweak.node_attrs[2]['y']), (1, 0))
        self.assertEqual((rem_tweak.node_attrs[3]['x'], rem_tweak.node_attrs[3]['y']), (1, 1))
        self.assertEqual((rem_tweak.node_attrs[4]['x'], rem_tweak.node_attrs[4]['y']), (2, 0))
        self.assertEqual((rem_tweak.node_attrs[5]['x'], rem_tweak.node_attrs[5]['y']), (2, 1))
        self.assertEqual((add_tweak.node_attrs['A']['x'], add_tweak.node_attrs['A']['y']), (1.5, 1))
        self.assertEqual((add_tweak.node_attrs['B']['x'], add_tweak.node_attrs['B']['y']), (1.5, 0))

    def test_join_edges_with_hole(self):
        # TODO: Test face / edge data is retained.
        """
        1           2   9           10
          ┌───────┐       ┌───────┐
          │5┌───┐6│       │       │
          │ │   │ │       │       │
          │4└───┘7│       │       │
          └───────┘       └───────┘
        0           3   8           11

                      ↓

        1             A             10
          ┌───────────┬───────────┐
          │5┌───┐6    │           │
          │ │   │     │           │
          │4└───┘7    │           │
          └───────────┴───────────┘
        0             B             11

        """
        # Set up test data.
        self.create_polygon(self.c, ((0, 0), (0, 3), (3, 3), (3, 0)), ((1, 1), (1, 2), (2, 2), (2, 1)))
        self.create_polygon(self.c, ((4, 0), (4, 3), (7, 3), (7, 0)))

        # Start test.
        e1 = self.c.get_edge(2, 3)
        e2 = self.c.get_edge(8, 9)
        with patch.object(uuid, 'uuid4', side_effect=('A', 'B')):
            add_tweak, rem_tweak = commands.join_edges(e1, e2)

        # Assert results.
        self.assertSetEqual(rem_tweak.nodes, {2, 3, 9, 8})
        self.assertSetEqual(add_tweak.nodes, {'A', 'B'})
        self.assertSetEqual(rem_tweak.edges, {(1, 2), (2, 3), (3, 0), (11, 8), (8, 9), (9, 10)})
        self.assertSetEqual(add_tweak.edges, {(1, 'A'), ('A', 'B'), ('B', 0), (11, 'B'), ('B', 'A'), ('A', 10)})
        self.assertSetEqual(rem_tweak.faces, {(0, 1, 2, 3, 0, 4, 5, 6, 7, 4), (8, 9, 10, 11, 8)})
        self.assertSetEqual(add_tweak.faces, {(0, 1, 'A', 'B', 0, 4, 5, 6, 7, 4), ('B', 'A', 10, 11, 'B')})
        self.assertEqual((rem_tweak.node_attrs[2]['x'], rem_tweak.node_attrs[2]['y']), (3, 3))
        self.assertEqual((rem_tweak.node_attrs[3]['x'], rem_tweak.node_attrs[3]['y']), (3, 0))
        self.assertEqual((rem_tweak.node_attrs[8]['x'], rem_tweak.node_attrs[8]['y']), (4, 0))
        self.assertEqual((rem_tweak.node_attrs[9]['x'], rem_tweak.node_attrs[9]['y']), (4, 3))
        self.assertEqual((add_tweak.node_attrs['A']['x'], add_tweak.node_attrs['A']['y']), (3.5, 3))
        self.assertEqual((add_tweak.node_attrs['B']['x'], add_tweak.node_attrs['B']['y']), (3.5, 0))

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
        self.create_polygon(self.c, ((0, 0), (0, 0.5), (0, 1), (1, 1), (1, 0.5), (1, 0)))
        self.create_polygon(self.c, ((2, 0), (2, 0.5), (2, 1), (3, 1), (3, 0.5), (3, 0)))

        # Start test.
        e1 = self.c.get_edge(3, 4)
        e2 = self.c.get_edge(4, 5)
        e3 = self.c.get_edge(6, 7)
        e4 = self.c.get_edge(7, 8)
        with patch.object(uuid, 'uuid4', side_effect=('A', 'B', 'C')):
            add_tweak, rem_tweak = commands.join_edges(e1, e2, e3, e4)

        # Assert results.
        self.assertSetEqual(rem_tweak.nodes, {3, 4, 5, 6, 7, 8})
        self.assertSetEqual(add_tweak.nodes, {'A', 'B', 'C'})
        self.assertSetEqual(rem_tweak.edges, {(2, 3), (3, 4), (4, 5), (5, 0), (11, 6), (6, 7), (7, 8), (8, 9)})
        self.assertSetEqual(add_tweak.edges, {(2, 'A'), ('A', 'B'), ('B', 'C'), ('C', 0), (11, 'C'), ('C', 'B'), ('B', 'A'), ('A', 9)})
        self.assertSetEqual(rem_tweak.faces, {(0, 1, 2, 3, 4, 5, 0), (6, 7, 8, 9, 10, 11, 6)})
        self.assertSetEqual(add_tweak.faces, {(0, 1, 2, 'A', 'B', 'C', 0), ('C', 'B', 'A', 9, 10, 11, 'C')})
        self.assertEqual((rem_tweak.node_attrs[3]['x'], rem_tweak.node_attrs[3]['y']), (1, 1))
        self.assertEqual((rem_tweak.node_attrs[4]['x'], rem_tweak.node_attrs[4]['y']), (1, 0.5))
        self.assertEqual((rem_tweak.node_attrs[5]['x'], rem_tweak.node_attrs[5]['y']), (1, 0))
        self.assertEqual((rem_tweak.node_attrs[6]['x'], rem_tweak.node_attrs[6]['y']), (2, 0))
        self.assertEqual((rem_tweak.node_attrs[7]['x'], rem_tweak.node_attrs[7]['y']), (2, 0.5))
        self.assertEqual((rem_tweak.node_attrs[8]['x'], rem_tweak.node_attrs[8]['y']), (2, 1))
        self.assertEqual((add_tweak.node_attrs['A']['x'], add_tweak.node_attrs['A']['y']), (1.5, 1))
        self.assertEqual((add_tweak.node_attrs['B']['x'], add_tweak.node_attrs['B']['y']), (1.5, 0.5))
        self.assertEqual((add_tweak.node_attrs['C']['x'], add_tweak.node_attrs['C']['y']), (1.5, 0))
