import json
import os
import tempfile
from pathlib import Path

from editor.constants import ATTRIBUTES, EDGE_DEFAULT, FACE_DEFAULT, NODE_DEFAULT
from editor.graph import Graph
from editor.tests.testcasebase import TestCaseBase


class FaceTestCase(TestCaseBase):

    def test_face_rings_one(self):

        # Set up test data.
        g = Graph()
        self.create_polygon(g, ((0, 0), (10, 0), (10, 10), (0, 10)))

        # Start test.
        face = list(g.faces)[0]

        # Assert results.
        self.assertEqual(len(face.nodes), 4)
        self.assertEqual(len(face.edges), 4)
        self.assertEqual(len(face.rings), 1)
        self.assertEqual(len(face.rings[0].nodes), 4)
        self.assertTupleEqual(face.rings[0].nodes, tuple([g.get_node(i) for i in range(4)]))

    def test_face_rings_two(self):

        # Set up test data.
        g = Graph()
        self.create_polygon(g, ((0, 0), (1, 0), (1, 1), (0, 1)), ((1, 1), (1, 9), (9, 9), (9, 1)))

        # Start test.
        face = list(g.faces)[0]

        # Assert results.
        self.assertEqual(len(face.nodes), 8)
        self.assertEqual(len(face.edges), 8)
        self.assertEqual(len(face.rings), 2)
        self.assertEqual(len(face.rings[0].nodes), 4)
        self.assertEqual(len(face.rings[1].nodes), 4)
        self.assertTupleEqual(face.rings[0].nodes, tuple([g.get_node(i) for i in range(4)]))
        self.assertTupleEqual(face.rings[1].nodes, tuple([g.get_node(i) for i in range(4, 8)]))

    def test_face_rings_three(self):

        # FAILING BECAUSE WE'RE SORTING

        # Set up test data.
        g = Graph()
        self.create_polygon(g, ((0, 0), (1, 0), (1, 1), (0, 1)), ((1, 1), (1, 9), (9, 9), (9, 1)), ((2, 2), (2, 8), (8, 8), (8, 1)))

        # Start test.
        face = list(g.faces)[0]

        # Assert results.
        self.assertEqual(len(face.nodes), 12)
        self.assertEqual(len(face.edges), 12)
        self.assertEqual(len(face.rings), 3)
        self.assertEqual(len(face.rings[0].nodes), 4)
        self.assertEqual(len(face.rings[1].nodes), 4)
        self.assertEqual(len(face.rings[2].nodes), 4)
        self.assertTupleEqual(face.rings[0].nodes, tuple([g.get_node(i) for i in range(4)]))
        self.assertTupleEqual(face.rings[1].nodes, tuple([g.get_node(i) for i in range(4, 8)]))
        self.assertTupleEqual(face.rings[2].nodes, tuple([g.get_node(i) for i in range(8, 12)]))


class GraphTestCase(TestCaseBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_data_dir_path = Path(__file__).parent.joinpath('data')

    def test_add_node_attribute_definition(self):

        # Set up test data.
        g = Graph()

        # Start test.
        g.add_node_attribute_definition('bar', 2)

        # Assert results.
        self.assertDictEqual(g.data.graph[NODE_DEFAULT], {'bar': 2})

    def test_add_edge_attribute_definition(self):

        # Set up test data.
        g = Graph()

        # Start test.
        g.add_edge_attribute_definition('baz', 3.0)

        # Assert results.
        self.assertDictEqual(g.data.graph[EDGE_DEFAULT], {'baz': 3.0})

    def test_add_face_attribute_definition(self):

        # Set up test data.
        g = Graph()

        # Start test.
        g.add_face_attribute_definition('qux', 'four')

        # Assert results.
        self.assertDictEqual(g.data.graph[FACE_DEFAULT], {'qux': 'four'})

    def test_get_node_default_attributes(self):

        # Set up test data.
        g = Graph()
        g.data.graph[NODE_DEFAULT]['bar'] = 2

        # Start test.
        data = g.get_node_default_attributes()

        # Assert results.
        self.assertDictEqual({'bar': 2}, data)

    def test_get_edge_default_attributes(self):

        # Set up test data.
        g = Graph()
        g.data.graph[EDGE_DEFAULT]['baz'] = 3.0

        # Start test.
        data = g.get_edge_default_attributes()

        # Assert results.
        self.assertDictEqual({'baz': 3.0}, data)

    def test_get_face_default_attributes(self):

        # Set up test data.
        g = Graph()
        g.data.graph[FACE_DEFAULT]['qux'] = 'four'

        # Start test.
        data = g.get_face_default_attributes()

        # Assert results.
        self.assertDictEqual({'qux': 'four'}, data)

    def test_load(self):

        # Set up test data.
        g = Graph()

        # Start test.
        g.load(self.test_data_dir_path.joinpath('1_squares.json'))

        # Assert results.
        self.assertDictEqual(g.data.graph[ATTRIBUTES], {'foo': True})
        self.assertDictEqual(g.data.graph[NODE_DEFAULT], {'x': 0.1, 'y': 0.2, 'bar': 2})
        self.assertDictEqual(g.data.graph[EDGE_DEFAULT], {'baz': 3.0})
        self.assertDictEqual(g.data.graph[FACE_DEFAULT], {'qux': 'four'})

    def test_save(self):

        # Set up test data.
        g = Graph(foo=True)
        g.data.graph[NODE_DEFAULT]['x'] = 0.1
        g.data.graph[NODE_DEFAULT]['y'] = 0.2
        g.data.graph[NODE_DEFAULT]['bar'] = 2
        g.data.graph[EDGE_DEFAULT]['baz'] = 3.0
        g.data.graph[FACE_DEFAULT]['qux'] = 'four'
        self.create_polygon(g, ((0, 0), (1, 0), (1, 1), (0, 1)))

        handle, file_path = tempfile.mkstemp()
        os.close(handle)
        try:

            # Start test.
            g.save(file_path)

            # Assert results.
            with open(file_path, 'r') as f:
                data = json.load(f)
            self.assertDictEqual(data['graph'][ATTRIBUTES], {'foo': True})
            self.assertDictEqual(data['graph'][NODE_DEFAULT], {'x': 0.1, 'y': 0.2, 'bar': 2})
            self.assertDictEqual(data['graph'][EDGE_DEFAULT], {'baz': 3.0})
            self.assertDictEqual(data['graph'][FACE_DEFAULT], {'qux': 'four'})
        finally:
            os.remove(file_path)
