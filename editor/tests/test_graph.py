import json
import os
import tempfile
import unittest

from editor.constants import SETTINGS, DEFAULT_NODE_ATTRIBUTES, \
    DEFAULT_HEDGE_ATTRIBUTES, DEFAULT_FACE_ATTRIBUTES
from editor.graph import Graph


class ContentTestCase(unittest.TestCase):

    def setUp(self):
        super().setUp()

        # Set up test data.
        self.g = Graph()
        self.g.data.graph[SETTINGS][DEFAULT_NODE_ATTRIBUTES].append({
            'name': 'foo',
            'type': 'int',
            'default': 0,
        })
        self.g.data.graph[SETTINGS][DEFAULT_HEDGE_ATTRIBUTES].append({
            'name': 'bar',
            'type': 'float',
            'default': 0.1,
        })
        self.g.data.graph[SETTINGS][DEFAULT_FACE_ATTRIBUTES].append({
            'name': 'baz',
            'type': 'str',
            'default': 'zero',
        })

    def test_get_default_node_data(self):

        # Start test.
        data = self.g.get_default_node_data()

        # Assert results.
        self.assertDictEqual({'foo': 0}, data)

    def test_get_default_hedge_data(self):

        # Start test.
        data = self.g.get_default_hedge_data()

        # Assert results.
        self.assertDictEqual({'bar': 0.1}, data)

    def test_get_default_face_data(self):

        # Start test.
        data = self.g.get_default_face_data()

        # Assert results.
        self.assertDictEqual({'baz': 'zero'}, data)

    def test_load(self):

        # Set up test data.
        data = {
            'directed': True,
            'multigraph': False,
            'graph': {
                'settings': {
                    'default_node_attributes': [{
                        'name': 'quiz',
                        'type': 'int',
                        'default': 1,
                    }],
                    'default_hedge_attributes': [{
                        'name': 'quat',
                        'type': 'int',
                        'default': 1.1,
                    }],
                    'default_face_attributes': [{
                        'name': 'quack',
                        'type': 'int',
                        'default': 'one',
                    }]
                },
                'faces': {}
            },
            'nodes': [],
            'links': [],
        }
        handle, file_path = tempfile.mkstemp()
        with open(handle, 'w') as f:
            json.dump(data, f)

        try:

            # Start test.
            with open(file_path, 'r') as f:
                self.g.load(file_path)

            # Assert results.
            self.assertDictEqual(self.g.data.graph[SETTINGS][DEFAULT_NODE_ATTRIBUTES][0], {
                'name': 'quiz',
                'type': 'int',
                'default': 1,
            })
            self.assertDictEqual(self.g.data.graph[SETTINGS][DEFAULT_HEDGE_ATTRIBUTES][0], {
                'name': 'quat',
                'type': 'int',
                'default': 1.1,
            })
            self.assertDictEqual(self.g.data.graph[SETTINGS][DEFAULT_FACE_ATTRIBUTES][0], {
                'name': 'quack',
                'type': 'int',
                'default': 'one',
            })
        finally:
            os.remove(file_path)

    def test_save(self):
        handle, file_path = tempfile.mkstemp()
        try:

            # Start test.
            with open(handle, 'w') as f:
                self.g.save(file_path)

            # Assert results.
            with open(file_path, 'r') as f:
                data = json.load(f)
                self.assertDictEqual(data['graph'][SETTINGS][DEFAULT_NODE_ATTRIBUTES][0], {
                    'name': 'foo',
                    'type': 'int',
                    'default': 0,
                })
                self.assertDictEqual(data['graph'][SETTINGS][DEFAULT_HEDGE_ATTRIBUTES][0], {
                    'name': 'bar',
                    'type': 'float',
                    'default': 0.1,
                })
                self.assertDictEqual(data['graph'][SETTINGS][DEFAULT_FACE_ATTRIBUTES][0], {
                    'name': 'baz',
                    'type': 'str',
                    'default': 'zero',
                })
        finally:
            os.remove(file_path)
