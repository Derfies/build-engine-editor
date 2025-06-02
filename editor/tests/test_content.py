import unittest
from pathlib import Path

from editor.content import Content


class ContentTestCase(unittest.TestCase):

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
        c = Content()

        # Start test.
        c.load(self.test_data_dir_path.joinpath('1_squares.map'))

        # Assert results.
        self.assertEqual(len(c.g.nodes), 4)
        self.assertEqual(len(c.g.edges), 4)
        self.assertEqual(len(c.g.polys), 1)

    def test_load_2_squares(self):
        """
        +---+---+
        |   |   |
        +---+---+

        """
        # Set up test data.
        c = Content()

        # Start test.
        c.load(self.test_data_dir_path.joinpath('2_squares.map'))

        # Assert results.
        self.assertEqual(len(c.g.nodes), 6)
        self.assertEqual(len(c.g.edges), 7)
        self.assertEqual(len(c.g.polys), 2)

    def test_load_3_squares(self):
        """
        +---+---+
        |   |   |
        +---+---+
        |   |
        +---+

        """
        # Set up test data.
        c = Content()

        # Start test.
        c.load(self.test_data_dir_path.joinpath('3_squares.map'))

        # Assert results.
        self.assertEqual(len(c.g.nodes), 8)
        self.assertEqual(len(c.g.edges), 10)
        self.assertEqual(len(c.g.polys), 3)

    def test_load_4_squares(self):
        """
        +---+---+
        |   |   |
        +---+---+
        |   |   |
        +---+---+

        """
        # Set up test data.
        c = Content()

        # Start test.
        c.load(self.test_data_dir_path.joinpath('4_squares.map'))

        # Assert results.
        self.assertEqual(len(c.g.nodes), 9)
        self.assertEqual(len(c.g.edges), 12)
        self.assertEqual(len(c.g.polys), 4)
