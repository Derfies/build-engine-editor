import math
import uuid
from typing import Any, Iterable

import mapbox_earcut as earcut
import numpy as np
from shapely import Polygon

from editor.graph import Face

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


def edges(nodes: tuple[Any, ...]):

    # TODO: Remove.
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


def triangulate_polygon(polygon: Polygon):
    if not polygon.is_valid:
        from shapely.validation import explain_validity
        print(polygon)
        print(explain_validity(polygon))
        raise ValueError("Invalid polygon")

    rings = []

    # Exterior ring (drop closing point)
    ext_coords = list(polygon.exterior.coords)[:-1]
    if len(ext_coords) >= 3:
        rings.append(ext_coords)
    else:
        raise ValueError("Exterior ring has fewer than 3 points")

    # Holes
    for h in polygon.interiors:
        hole_coords = list(h.coords)[:-1]
        if len(hole_coords) >= 3:
            rings.append(hole_coords)
        else:
            # skip degenerate hole
            print("Skipping degenerate hole:", hole_coords)

    # Flatten vertices
    vertices = np.array([pt for ring in rings for pt in ring], dtype=np.float32)

    # Compute cumulative end indices
    counts = [len(r) for r in rings]
    ring_end_indices = np.cumsum(counts).astype(np.uint32)

    # Check monotonicity
    if not np.all(np.diff(ring_end_indices) > 0):
        raise ValueError("ring_end_indices is not strictly increasing!")

    # Triangulate
    triangles = earcut.triangulate_float32(vertices, ring_end_indices)

    # Build Shapely polygons
    shapely_tris = []
    for i in range(0, len(triangles), 3):
        pts = [tuple(vertices[j]) for j in triangles[i:i+3]]
        shapely_tris.append(Polygon(pts))

    return shapely_tris


def compute_bounding_sphere(vertices):
    center = np.mean(vertices, axis=0)
    radius = np.max(np.linalg.norm(vertices - center, axis=1))
    return center, radius


def camera_distance(radius, fov_deg):
    fov_rad = math.radians(fov_deg)
    return radius / math.sin(fov_rad / 2)