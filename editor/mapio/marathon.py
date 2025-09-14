from collections import defaultdict
from pathlib import Path

from editor.constants import MapFormat
from editor.graph import Graph
from jjaro.sceA import load


def get_texture_ids(value: int):
    texture_id = value & 0xFF  # masks the lower 8 bits
    collection = (value >> 8) & 0xFF  # shifts right 8 bits and masks
    return texture_id, collection


def import_marathon(graph: Graph, file_path: str | Path, format: MapFormat):
    m = load(file_path)

    # Nodes.
    nodes = []
    for i, point in enumerate(m.points):
        node = graph.add_node(i, x=point.x, y=point.y)
        nodes.append(node)

    # Edges.
    edges = defaultdict(list)
    for i, line in enumerate(m.lines):
        head, tail = line.endpoint_indices[0], line.endpoint_indices[1]
        edge = graph.add_edge((head, tail))
        edges[head].append(tail)

        # HAXX putting ALL rev edges in for the moment.
        graph.add_edge((tail, head))

    # Faces.
    # NOTE: Duke export seems to only handle 1024 polygons?
    for i, polygon in enumerate(m.polygons):#[0:1024]):
        #print('polygon:', polygon)

        #low_byte = polygon.ceiling_height & 0xFF  # masks the lower 8 bits
        #high_byte = (polygon.ceiling_height >> 8) & 0xFF  # shifts right 8 bits and masks

        #print('low:', low_byte, 'high:', high_byte)
        offset = 2785   # gets us into the jjaro marathon texture collection

        #print(low_byte, high_byte)

        # print('polygon.floor_texture:', polygon.floor_texture)
        # print('polygon.ceiling_texture:', polygon.ceiling_texture)
        #
        # print('f:', get_texture_ids(polygon.floor_texture))
        # print('c:', get_texture_ids(polygon.ceiling_texture))


        face_nodes = [e_idx for e_idx in polygon.endpoint_indices if e_idx > -1]
        face_nodes.append(face_nodes[0])
        #print('floor_light:', polygon.floor_light)
        face_attrs = {
            'floorz': polygon.floor_height,
            'ceilingz': polygon.ceiling_height,
            'floorpicnum': str(get_texture_ids(polygon.floor_texture)[0] + offset),
            'ceilingpicnum': str(get_texture_ids(polygon.ceiling_texture)[0] + offset),
            #'floorshade': polygon.floor_light / 255,
            #'ceilingshade': polygon.ceiling_light / 255,
        }
        graph.add_face(tuple(face_nodes), **face_attrs)

    graph.update()
