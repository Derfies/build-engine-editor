import os
import tempfile
from pathlib import Path

from editor import mapio
from editor.constants import MapFormat
from editor.graph import Graph
from editor.tests.testcasebase import TestCaseBase


class MapioTestCase(TestCaseBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_data_dir_path = Path(__file__).parent.joinpath('data')

    def test_load_1_squares(self):
        """
        +---+
        |   |
        +---+

        """
        # Set up test data.
        g = Graph()

        # Start test.
        mapio.import_map(g, self.test_data_dir_path.joinpath('1_squares.map'), MapFormat.DUKE_3D)

        # Assert results.
        self.assertEqual(len(g.nodes), 4)
        self.assertEqual(len(g.edges), 4)
        self.assertEqual(len(g.hedges), 4)
        self.assertEqual(len(g.faces), 1)

    def test_load_2_squares(self):
        """
        +---+---+
        |   |   |
        +---+---+

        """
        # Set up test data.
        g = Graph()

        # Start test.
        mapio.import_map(g, self.test_data_dir_path.joinpath('2_squares.map'), MapFormat.DUKE_3D)

        # Assert results.
        self.assertEqual(len(g.nodes), 6)
        self.assertEqual(len(g.edges), 7)
        self.assertEqual(len(g.hedges), 8)
        self.assertEqual(len(g.faces), 2)

    def test_load_3_squares(self):
        """
        +---+---+
        |   |   |
        +---+---+
        |   |
        +---+

        """
        # Set up test data.
        g = Graph()

        # Start test.
        mapio.import_map(g, self.test_data_dir_path.joinpath('3_squares.map'), MapFormat.DUKE_3D)

        # Assert results.
        self.assertEqual(len(g.nodes), 8)
        self.assertEqual(len(g.edges), 10)
        self.assertEqual(len(g.hedges), 12)
        self.assertEqual(len(g.faces), 3)

    def test_load_4_squares(self):
        """
        +---+---+
        |   |   |
        +---+---+
        |   |   |
        +---+---+

        """
        # Set up test data.
        g = Graph()

        # Start test.
        mapio.import_map(g, self.test_data_dir_path.joinpath('4_squares.map'), MapFormat.DUKE_3D)

        # Assert results.
        self.assertEqual(len(g.nodes), 9)
        self.assertEqual(len(g.edges), 12)
        self.assertEqual(len(g.hedges), 16)
        self.assertEqual(len(g.faces), 4)

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
        g.add_hedge_attribute_definition('baz', 3.0)
        g.add_face_attribute_definition('qux', 'four')
        self.create_polygon(g, (0, 0), (100, 0), (100, 100), (0, 100))

        handle, file_path = tempfile.mkstemp()
        os.close(handle)
        try:

            # Start test.
            mapio.export_gexf(g, file_path, None)

            # Assert results.
            with open(file_path, 'r') as f:
                data = f.read()

            print(data)


        finally:
            os.remove(file_path)
