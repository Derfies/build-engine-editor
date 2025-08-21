import unittest
from pathlib import Path

from editor import mapio
from editor.constants import MapFormat
from editor.graph import Graph


class MapioTestCase(unittest.TestCase):

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
        c = Graph()

        # Start test.
        mapio.import_map(c, self.test_data_dir_path.joinpath('1_squares.map'), MapFormat.DUKE_3D)

        # Assert results.
        self.assertEqual(len(c.nodes), 4)
        self.assertEqual(len(c.edges), 4)
        self.assertEqual(len(c.hedges), 4)
        self.assertEqual(len(c.faces), 1)

    def test_load_2_squares(self):
        """
        +---+---+
        |   |   |
        +---+---+

        """
        # Set up test data.
        c = Graph()

        # Start test.
        mapio.import_map(c, self.test_data_dir_path.joinpath('2_squares.map'), MapFormat.DUKE_3D)

        # Assert results.
        self.assertEqual(len(c.nodes), 6)
        self.assertEqual(len(c.edges), 7)
        self.assertEqual(len(c.hedges), 8)
        self.assertEqual(len(c.faces), 2)

    def test_load_3_squares(self):
        """
        +---+---+
        |   |   |
        +---+---+
        |   |
        +---+

        """
        # Set up test data.
        c = Graph()

        # Start test.
        mapio.import_map(c, self.test_data_dir_path.joinpath('3_squares.map'), MapFormat.DUKE_3D)

        # Assert results.
        self.assertEqual(len(c.nodes), 8)
        self.assertEqual(len(c.edges), 10)
        self.assertEqual(len(c.hedges), 12)
        self.assertEqual(len(c.faces), 3)

    def test_load_4_squares(self):
        """
        +---+---+
        |   |   |
        +---+---+
        |   |   |
        +---+---+

        """
        # Set up test data.
        c = Graph()

        # Start test.
        mapio.import_map(c, self.test_data_dir_path.joinpath('4_squares.map'), MapFormat.DUKE_3D)

        # Assert results.
        self.assertEqual(len(c.nodes), 9)
        self.assertEqual(len(c.edges), 12)
        self.assertEqual(len(c.hedges), 16)
        self.assertEqual(len(c.faces), 4)
