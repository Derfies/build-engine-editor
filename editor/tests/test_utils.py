from parameterized import parameterized
from shapely import Polygon

from editor import utils
from editor.graph import Graph
from editor.tests.testcasebase import TestCaseBase

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


class UtilsTestCase(TestCaseBase):

    @parameterized.expand((0, 1, 2, 3))
    def test_matching(self, offset: int):
        """
        Test that we can match a single quad face to the equivalent shapely
        polygon, even if the polygon's nodes have been rotated.

        """
        # Set up test data.
        g = Graph()
        face = self.create_polygon(g, ((0, 0), (0, 1), (1, 1), (1, 0)))
        positions = [node.pos.to_tuple() for node in face.nodes]
        poly = Polygon(positions[offset:] + positions[:offset])

        # Start test.
        mappings = utils.map(face, (poly,))

        # Assert results.
        self.assertEqual(len(mappings[0]), 4)
        for node_, result_coord in mappings[0].items():
            node = face.graph.get_node(node_)
            expected_coord = round(node.pos.x(), 2), round(node.pos.y(), 2)
            self.assertEqual(result_coord, expected_coord)

    @parameterized.expand((0, 1, 2, 3))
    def test_additional_point(self, offset: int):
        """
        Test that we can match a single quad face to a shapely polygon which has
        an additional point, even if the polygon's nodes have been rotated.

        """
        # Set up test data.
        g = Graph()
        face = self.create_polygon(g, ((0, 0), (0, 1), (1, 1), (1, 0)))
        positions = [node.pos.to_tuple() for node in face.nodes] + [(0.5, 0)]
        poly = Polygon(positions[offset:] + positions[:offset])

        # Start test.
        mappings = utils.map(face, (poly,))

        # Assert results.
        self.assertEqual(len(mappings[0]), 5)
        for node_, result_coord in mappings[0].items():
            if face.graph.has_node(node_):
                node = face.graph.get_node(node_)
                expected_coord = round(node.pos.x(), 2), round(node.pos.y(), 2)
                self.assertEqual(result_coord, expected_coord)
            else:
                expected_coord = (0.5, 0)
                self.assertEqual(result_coord, expected_coord)

    # TODO:
    # Test non contiguous edges... somehow.
    # What does this even mean?
    # I suppose it means that we need to enforce contiguous indexes somehow.
    # Eg at the momemnt we just pull out an index from the original face.
    # There's nothing that stopping this face from bow-tieing, eg if the original
    # indices were (0, 0), (1, 0), (1, 1), (1, 0), (0, 1) then we would just grab
    # the first (1, 0) and get the wrong node back. This isn't terrible because
    # it's a bit of an edge case - rarely would nodes have an identical point
    # but should be catered for.