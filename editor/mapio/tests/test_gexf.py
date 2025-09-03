import os
import tempfile
from pathlib import Path

import editor.mapio.gexf
from editor.graph import Graph
from editor.tests.testcasebase import TestCaseBase


class GexfTestCase(TestCaseBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_data_dir_path = Path(__file__).parent.joinpath('data')

    def test_export_gexf(self):
        """
        +---+
        |   |
        +---+

        """

        # TODO: Assert results.

        # Set up test data.
        g = Graph(foo=True)
        g.add_node_attribute_definition('bar', 2)
        g.add_edge_attribute_definition('baz', 3.0)
        g.add_face_attribute_definition('qux', 'four')
        self.create_polygon(g, ((0, 0), (100, 0), (100, 100), (0, 100)))

        handle, file_path = tempfile.mkstemp()
        os.close(handle)
        try:

            # Start test.
            editor.mapio.gexf.export_gexf(g, file_path, None)

            # Assert results.
            with open(file_path, 'r') as f:
                data = f.read()

            print(data)

        finally:
            os.remove(file_path)
