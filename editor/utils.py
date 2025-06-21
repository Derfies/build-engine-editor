import uuid
from typing import Any, Callable, Iterable, Optional

from shapely import Polygon

from editor.graph import Face

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


def edges(nodes: tuple[Any, ...]):
    return [(nodes[i], nodes[(i + 1) % len(nodes)]) for i in range(len(nodes))]


def map(face: Face, polys: Iterable[Polygon]):
    """
    Return a mapping for each polygon back to the input face.

    - Some nodes in the given polys may not exist in the input face
    - Vice versa is also true
    - So how can I tell what is correct?

    Can we:
    - Add additional nodes that were expected, ie from a cut? This isn't guaranteed
      to be easy, some bool ops would be difficult to count nodes for.


    """
    node_positions = [(round(node.pos.x(), 2), round(node.pos.y(), 2)) for node in face.nodes]
    poly_mappings = []
    for poly in polys:
        poly_mapping = {}
        for coord in poly.exterior.coords[:-1]:
            coord = round(coord[0], 2), round(coord[1], 2)

            # If the coord was in the original list of node positions, use that
            # node.
            if coord in node_positions:
                idx = node_positions.index(coord)
                poly_mapping[face.nodes[idx].data] = coord

            # Otherwise create a new node for this new coord.
            else:
                new_node = str(uuid.uuid4())
                poly_mapping[new_node] = coord

        poly_mappings.append(poly_mapping)
    return poly_mappings
