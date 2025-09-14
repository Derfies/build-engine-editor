from editor.clipboard import Clipboard
from editor.tests.testcasebase import TestCaseBase


class ClipboardTestCase(TestCaseBase):

    def test_copy_node(self):
        """
        Copying node 0 which should add only that node to the clipboard.

        1           3
          ┌───────┐
          │       │
          │       │
          │       │
          └───────┘
        0           2

        """
        # Set up test data.
        clipboard = Clipboard()
        self.build_grid(self.c, 3, 2)
        node = self.c.get_node(0)
        node.set_attribute('foo', 'bar')

        # Start test.
        clipboard.copy([node])

        # Assert results.
        tweak = clipboard._tweak
        self.assertSetEqual(tweak.nodes, {0})
        self.assertSetEqual(tweak.edges, set())
        self.assertSetEqual(tweak.faces, set())
        self.assertDictEqual(tweak.node_attrs, {0: {'x': 0, 'y': 0, 'foo': 'bar'}})
        self.assertDictEqual(tweak.edge_attrs, {})
        self.assertDictEqual(tweak.face_attrs, {})

    def test_copy_edge(self):
        """
        Copying edge 0, 2 which should add that edge and its nodes to the clipboard.

        1           3
          ┌───────┐
          │       │
          │       │
          │       │
          └───────┘
        0           2

        """
        # Set up test data.
        clipboard = Clipboard()
        self.build_grid(self.c, 2, 2)
        node = self.c.get_node(0)
        node.set_attribute('foo', 'bar')
        edge = self.c.get_edge(0, 2)
        edge.set_attribute('baz', 'bang')

        # Start test.
        clipboard.copy([edge])

        # Assert results.
        tweak = clipboard._tweak
        self.assertSetEqual(tweak.nodes, {0, 2})
        self.assertSetEqual(tweak.edges, {(0, 2)})
        self.assertSetEqual(tweak.faces, set())
        self.assertDictEqual(tweak.node_attrs[0], {'x': 0, 'y': 0, 'foo': 'bar'})
        self.assertDictEqual(tweak.node_attrs[2], {'x': 1, 'y': 0})
        self.assertDictEqual(tweak.edge_attrs, {(0, 2): {'baz': 'bang'}})
        self.assertDictEqual(tweak.face_attrs, {})

    def test_copy_face(self):
        """
        Copying face 0, 2, 3, 1, 0 which should add that face, its edges and its
        nodes to the clipboard.

        1           3
          ┌───────┐
          │       │
          │       │
          │       │
          └───────┘
        0           2

        """
        # Set up test data.
        clipboard = Clipboard()
        self.build_grid(self.c, 2, 2)
        node = self.c.get_node(0)
        node.set_attribute('foo', 'bar')
        edge = self.c.get_edge(0, 2)
        edge.set_attribute('baz', 'bang')
        face = self.c.get_face((0, 2, 3, 1, 0))
        face.set_attribute('qux', 'quack')

        # Start test.
        clipboard.copy([face])

        # Assert results.
        tweak = clipboard._tweak
        self.assertSetEqual(tweak.nodes, {0, 2, 3, 1})
        self.assertSetEqual(tweak.edges, {(0, 2), (2, 3), (3, 1), (1, 0)})
        self.assertSetEqual(tweak.faces, {(0, 2, 3, 1, 0)})
        self.assertDictEqual(tweak.node_attrs[0], {'x': 0, 'y': 0, 'foo': 'bar'})
        self.assertDictEqual(tweak.node_attrs[2], {'x': 1, 'y': 0})
        self.assertDictEqual(tweak.node_attrs[3], {'x': 1, 'y': 1})
        self.assertDictEqual(tweak.node_attrs[1], {'x': 0, 'y': 1})
        self.assertDictEqual(tweak.edge_attrs[(0, 2)], {'baz': 'bang'})
        self.assertDictEqual(tweak.edge_attrs[(2, 3)], {})
        self.assertDictEqual(tweak.edge_attrs[(3, 1)], {})
        self.assertDictEqual(tweak.edge_attrs[(1, 0)], {})
        self.assertDictEqual(tweak.face_attrs, {(0, 2, 3, 1, 0): {'qux': 'quack'}})

    def test_paste_face(self):
        """
        Copying face 0, 2, 3, 1, 0 which should add that face, its edges and its nodes to the clipboard.

        TODO: Assert pasted attributes.

        1           3
          ┌───────┐
          │       │
          │       │
          │       │
          └───────┘
        0           2

        """
        # Set up test data.
        clipboard = Clipboard()
        self.build_grid(self.c, 2, 2)
        node = self.c.get_node(0)
        node.set_attribute('foo', 'bar')
        edge = self.c.get_edge(0, 2)
        edge.set_attribute('baz', 'bang')
        face = self.c.get_face((0, 2, 3, 1, 0))
        face.set_attribute('qux', 'quack')

        # Start test.
        clipboard.copy([face])
        tweak, _ = clipboard.paste()

        # Assert results.
        self.assertEqual(len(tweak.nodes), 4)
        self.assertEqual(len(tweak.edges), 4)
        self.assertEqual(len(tweak.faces), 1)
