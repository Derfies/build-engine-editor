import json
import os
import tempfile
import unittest
from pathlib import Path

from editor.constants import ATTRIBUTE_DEFINITIONS, FACE, GRAPH, HEDGE, NODE
from editor.graph import Graph


class GraphTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_data_dir_path = Path(__file__).parent.joinpath('data')

    def test_add_graph_attribute_definition(self):

        # Set up test data.
        g = Graph()

        # Start test.
        g.add_graph_attribute_definition('foo', bool, True)

        # Assert results.
        attr_def = {
            'name': 'foo',
            'type': 'bool',
            'default': True,
        }
        self.assertListEqual(g.data.graph[ATTRIBUTE_DEFINITIONS][GRAPH], [attr_def])

    def test_add_node_attribute_definition(self):

        # Set up test data.
        g = Graph()

        # Start test.
        g.add_node_attribute_definition('bar', int, 2)

        # Assert results.
        attr_def = {
            'name': 'bar',
            'type': 'int',
            'default': 2,
        }
        self.assertListEqual(g.data.graph[ATTRIBUTE_DEFINITIONS][NODE], [attr_def])

    def test_add_hedge_attribute_definition(self):

        # Set up test data.
        g = Graph()

        # Start test.
        g.add_hedge_attribute_definition('baz', float, 3.0)

        # Assert results.
        attr_def = {
            'name': 'baz',
            'type': 'float',
            'default': 3.0,
        }
        self.assertListEqual(g.data.graph[ATTRIBUTE_DEFINITIONS][HEDGE], [attr_def])

    def test_add_face_attribute_definition(self):

        # Set up test data.
        g = Graph()

        # Start test.
        g.add_face_attribute_definition('qux', str, 'four')

        # Assert results.
        attr_def = {
            'name': 'qux',
            'type': 'str',
            'default': 'four',
        }
        self.assertListEqual(g.data.graph[ATTRIBUTE_DEFINITIONS][FACE], [attr_def])

    def test_get_default_node_attributes(self):

        # Set up test data.
        g = Graph()
        g.data.graph[ATTRIBUTE_DEFINITIONS][NODE].append({
            'name': 'bar',
            'type': 'int',
            'default': 2,
        })

        # Start test.
        data = g.get_default_node_attributes()

        # Assert results.
        self.assertDictEqual({'bar': 2}, data)

    def test_get_default_hedge_attributes(self):

        # Set up test data.
        g = Graph()
        g.data.graph[ATTRIBUTE_DEFINITIONS][HEDGE].append({
            'name': 'baz',
            'type': 'float',
            'default': 3.0,
        })

        # Start test.
        data = g.get_default_hedge_attributes()

        # Assert results.
        self.assertDictEqual({'baz': 3.0}, data)

    def test_get_default_face_attributes(self):

        # Set up test data.
        g = Graph()
        g.data.graph[ATTRIBUTE_DEFINITIONS][FACE].append({
            'name': 'qux',
            'type': 'str',
            'default': 'four',
        })

        # Start test.
        data = g.get_default_face_attributes()

        # Assert results.
        self.assertDictEqual({'qux': 'four'}, data)

    def test_load(self):

        # Set up test data.
        g = Graph()

        # Start test.
        g.load(self.test_data_dir_path.joinpath('1_squares.json'))

        # Assert results.
        self.assertDictEqual(g.data.graph[ATTRIBUTE_DEFINITIONS][GRAPH][0], {
            'name': 'foo',
            'type': 'bool',
            'default': True,
        })
        self.assertDictEqual(g.data.graph[ATTRIBUTE_DEFINITIONS][NODE][0], {
            'name': 'x',
            'type': 'float',
            'default': 0.1,
        })
        self.assertDictEqual(g.data.graph[ATTRIBUTE_DEFINITIONS][NODE][1], {
            'name': 'y',
            'type': 'float',
            'default': 0.2,
        })
        self.assertDictEqual(g.data.graph[ATTRIBUTE_DEFINITIONS][NODE][2], {
            'name': 'bar',
            'type': 'int',
            'default': 2,
        })
        self.assertDictEqual(g.data.graph[ATTRIBUTE_DEFINITIONS][HEDGE][0], {
            'name': 'baz',
            'type': 'float',
            'default': 3.0,
        })
        self.assertDictEqual(g.data.graph[ATTRIBUTE_DEFINITIONS][FACE][0], {
            'name': 'qux',
            'type': 'str',
            'default': 'four',
        })

    def test_save(self):

        # Set up test data.
        g = Graph()
        g.data.graph[ATTRIBUTE_DEFINITIONS][GRAPH].append({
            'name': 'foo',
            'type': bool.__name__,
            'default': True,
        })
        g.data.graph[ATTRIBUTE_DEFINITIONS][NODE].append({
            'name': 'x',
            'type': float.__name__,
            'default': 0.1,
        })
        g.data.graph[ATTRIBUTE_DEFINITIONS][NODE].append({
            'name': 'y',
            'type': float.__name__,
            'default': 0.2,
        })
        g.data.graph[ATTRIBUTE_DEFINITIONS][NODE].append({
            'name': 'bar',
            'type': int.__name__,
            'default': 2,
        })
        g.data.graph[ATTRIBUTE_DEFINITIONS][HEDGE].append({
            'name': 'baz',
            'type': float.__name__,
            'default': 3.0,
        })
        g.data.graph[ATTRIBUTE_DEFINITIONS][FACE].append({
            'name': 'qux',
            'type': str.__name__,
            'default': 'four',
        })

        handle, file_path = tempfile.mkstemp()
        os.close(handle)
        try:

            # Start test.
            g.save(file_path)

            # Assert results.
            with open(file_path, 'r') as f:
                data = json.load(f)
            self.assertDictEqual(data['graph'][ATTRIBUTE_DEFINITIONS][GRAPH][0], {
                'name': 'foo',
                'type': 'bool',
                'default': True,
            })
            self.assertDictEqual(data['graph'][ATTRIBUTE_DEFINITIONS][NODE][0], {
                'name': 'x',
                'type': 'float',
                'default': 0.1,
            })
            self.assertDictEqual(data['graph'][ATTRIBUTE_DEFINITIONS][NODE][1], {
                'name': 'y',
                'type': 'float',
                'default': 0.2,
            })
            self.assertDictEqual(data['graph'][ATTRIBUTE_DEFINITIONS][NODE][2], {
                'name': 'bar',
                'type': 'int',
                'default': 2,
            })
            self.assertDictEqual(data['graph'][ATTRIBUTE_DEFINITIONS][HEDGE][0], {
                'name': 'baz',
                'type': 'float',
                'default': 3.0,
            })
            self.assertDictEqual(data['graph'][ATTRIBUTE_DEFINITIONS][FACE][0], {
                'name': 'qux',
                'type': 'str',
                'default': 'four',
            })
        finally:
            os.remove(file_path)
