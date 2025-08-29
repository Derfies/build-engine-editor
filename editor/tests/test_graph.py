import json
import os
import tempfile
import unittest
from pathlib import Path

from editor.constants import ATTRIBUTES, EDGE_DEFAULT, FACE_DEFAULT, NODE_DEFAULT
from editor.graph import Graph
from editor.tests.testcasebase import TestCaseBase


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
        # g.data.graph[NODE_DEFAULT]['x'] = 0.1
        # g.data.graph[NODE_DEFAULT]['y'] = 0.2
        # g.data.graph[NODE_DEFAULT]['bar'] = 2
        # g.data.graph[EDGE_DEFAULT]['baz'] = 3.0
        # g.data.graph[FACE_DEFAULT]['qux'] = 'four'
        g.add_node_attribute_definition('x', 0.1)
        g.add_node_attribute_definition('y', 0.2)
        g.add_node_attribute_definition('bar', 2)
        g.add_edge_attribute_definition('baz', 3.0)
        g.add_face_attribute_definition('qux', 'four')
        self.create_polygon(g, (0, 0), (1, 0), (1, 1), (0, 1))

        handle, file_path = tempfile.mkstemp()
        os.close(handle)
        try:

            # Start test.
            g.save(file_path)

            # Assert results.
            with open(file_path, 'r') as f:
                data = json.load(f)
            print(json.dumps(data, indent=2))
            self.assertDictEqual(data['graph'][ATTRIBUTES], {'foo': True})
            self.assertDictEqual(data['graph'][NODE_DEFAULT], {'x': 0.1, 'y': 0.2, 'bar': 2})
            self.assertDictEqual(data['graph'][EDGE_DEFAULT], {'baz': 3.0})
            self.assertDictEqual(data['graph'][FACE_DEFAULT], {'qux': 'four'})
        finally:
            os.remove(file_path)
