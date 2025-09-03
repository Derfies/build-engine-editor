from pathlib import Path

from editor.constants import MapFormat
from editor.graph import Graph
from editor.mapio import build
from editor.tests.testcasebase import TestCaseBase


class BuildTestCase(TestCaseBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_data_dir_path = Path(__file__).parent.joinpath('data')

    def test_import_build_1_squares(self):
        """
        +---+
        |   |
        +---+

        """
        # Set up test data.
        g = Graph()

        # Start test.
        build.import_build(g, self.test_data_dir_path.joinpath('1_squares.map'), MapFormat.DUKE_3D)

        # Assert results.
        self.assertEqual(len(g.nodes), 4)
        self.assertEqual(len(g.edges), 4)
        self.assertEqual(len(g.faces), 1)

    def test_import_build_2_squares(self):
        """
        +---+---+
        |   |   |
        +---+---+

        """
        # Set up test data.
        g = Graph()

        # Start test.
        build.import_build(g, self.test_data_dir_path.joinpath('2_squares.map'), MapFormat.DUKE_3D)

        # Assert results.
        self.assertEqual(len(g.nodes), 6)
        self.assertEqual(len(g.edges), 8)
        self.assertEqual(len(g.faces), 2)

    def test_import_build_3_squares(self):
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
        build.import_build(g, self.test_data_dir_path.joinpath('3_squares.map'), MapFormat.DUKE_3D)

        # Assert results.
        self.assertEqual(len(g.nodes), 8)
        self.assertEqual(len(g.edges), 12)
        self.assertEqual(len(g.faces), 3)

    def test_import_build_4_squares(self):
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
        build.import_build(g, self.test_data_dir_path.joinpath('4_squares.map'), MapFormat.DUKE_3D)

        # Assert results.
        self.assertEqual(len(g.nodes), 9)
        self.assertEqual(len(g.edges), 16)
        self.assertEqual(len(g.faces), 4)
