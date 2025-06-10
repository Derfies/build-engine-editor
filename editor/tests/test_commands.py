import unittest
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


    def test_split_face(self):
        """
        +----+----+
        |    .    |
        |    .    |
        +----+----+

        """
        # Set up test data.
        nodes = (0, 1, 2, 3)
        edges = ((0, 1), (1, 2), (2, 3), (3, 0))
        self.c.data.add_nodes_from(nodes)
        self.c.get_node(0).pos = QPointF(0, 0)
        self.c.get_node(1).pos = QPointF(0, 1)
        self.c.get_node(2).pos = QPointF(1, 1)
        self.c.get_node(3).pos = QPointF(1, 0)

        #for node in nodes:
        #    self.c.data.add_node(node)
        #for edge in edges:
        #    self.c.data.add_edge(*edge)
        self.c.data.add_edges_from(edges)
        self.c._faces[nodes] = {}
        self.c.update_undirected()

        print('content edges:')
        for n in self.c.data.edges:
           print('->', n)

        # Start test.
        e1 = self.c.get_hedge((0, 1))
        e2 = self.c.get_hedge((2, 3))

        print(e1.head.pos)
        print(e1.tail.pos)
        print(e2.head.pos)
        print(e2.tail.pos)
        with patch.object(QApplication, 'instance', return_value=self.mock_app):
            commands.split_face((e1, 0.5), (e2, 0.5))

        print('\nnodes:')
        for n in self.c.nodes:
            print('->', n)

        print('\nedges:')
        for n in self.c.edges:
            print('->', n)

        print('\nfaces:')
        for n in self.c.faces:
            print('->', n)

        # Assert results.
        self.assertEqual(len(self.c.nodes), 6)
        self.assertEqual(len(self.c.edges), 7)
        self.assertEqual(len(self.c.hedges), 8)
        self.assertEqual(len(self.c.faces), 2)
