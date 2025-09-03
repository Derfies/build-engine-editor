import logging
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from editor.constants import MapFormat
from editor.graph import Graph


logger = logging.getLogger(__name__)


GLOBAL_SCALE = 1000


class BlockType(Enum):

    GLOBAL = 'Global'
    LAYER_INFO = 'LayerInfo'
    GLOBAL_TEXTURE_INFO = 'GlobalTextureInfo'
    EVENT = 'Event'
    TAG = 'Tag'
    VERTEX = 'Vertex'
    LINE = 'Line'
    SIDE = 'Side'
    SECTOR = 'Sector'
    THING = 'Thing'


class ThingDefinition(Enum):

    MIKE = 13484


@dataclass
class Block:

    # Do blocks etc own their own ID? If it's implied from order maybe it should
    # be owned by the map.

    type: BlockType
    #id: Any | None


@dataclass
class Vertex(Block):

    x: float
    z: float


@dataclass
class Side(Block):

    line: str
    sector: str
    side_plane: str | None = None
    side_texture: str | None = None
    brightness_offset: str | None = None


@dataclass
class Line(Block):

    v1: int
    v2: int
    line_opposite: int | None = None
    side_upper: int | None = None
    side_middle: int | None = None
    side_lower: int | None = None


class Map:

    def __init__(self):
        self.vertices = []
        self.lines = []
        self.sides = []


def import_fallen_aces(graph: Graph, file_path: str | Path, format: MapFormat):
    import re

    with open(file_path, 'r') as f:
        data = f.readlines()

    m = Map()
    curr_block_type = None
    curr_block_attrs = None
    for line in data:

        # Drop comment and skip empty lines.
        line = line.split('//')[0].strip()
        if not line:
            continue

        # Not currently inside a block, attempt to resolve one.
        if curr_block_type is None:
            curr_block_type = BlockType(line)

        elif line == '{':
            curr_block_attrs = {}

        elif line == '}':

            if curr_block_type == BlockType.VERTEX:
                m.vertices.append(Vertex(curr_block_type, **curr_block_attrs))
            elif curr_block_type == BlockType.LINE:
                m.lines.append(Line(curr_block_type, **curr_block_attrs))
            elif curr_block_type == BlockType.SIDE:
                m.sides.append(Side(curr_block_type, **curr_block_attrs))

            curr_block_type = None
            curr_block_attrs = None

        else:
            try:
                key, value = line.split('=')
                key = key.strip()
                key = key.split('(')[0].strip()
                #key, value = re.split('= | (', line)
            except:
                #print('bad line:', line)
                continue
            try:
                curr_block_attrs[key.strip()] = json.loads(value.split(';')[0])
            except:
                #print(key, f'[{value}]')
                continue



    for idx, vertex in enumerate(m.vertices):
        graph.add_node(idx, x=vertex.x * GLOBAL_SCALE, y=vertex.z * GLOBAL_SCALE)

    for idx, line in enumerate(m.lines):
        graph.add_edge((line.v1, line.v2))

    # for idx, side in enumerate(m.sides):
    #     print(side)

    graph.update()


def write_block(f, type_: BlockType, id_: Any, attrs: dict):

    # TODO: Use marshmallow...?
    f.write(f'{type_.value}')
    if id_ is not None:
        f.write(f' // {id_}')
    f.write(f'\n')
    f.write('{\n')
    for key, value in attrs.items():
        if isinstance(value, dict):
            subvalues = []
            for subkey, subvalue in value.items():
                if isinstance(subvalue, str):
                    subvalue = f'"{subvalue}"'
                elif isinstance(subvalue, tuple):
                    subvalue = ','.join([str(v) for v in subvalue])
                subvalues.append(f'{subkey} = {subvalue}')
            value_str = '; '.join(subvalues)
            if subvalues:
                value_str += ';'
            f.write(f'  {key} ( {value_str} )\n')
        else:
            f.write(f'  {key} = {value};\n')
    f.write('}\n\n')


def export_fallen_aces(graph: Graph, file_path: str | Path, format: MapFormat):

    # Assign indices.
    node_to_index = {node: i for i, node in enumerate(graph.nodes)}
    edge_to_index = {edge: i for i, edge in enumerate(graph.edges)}
    face_to_index = {face: i for i, face in enumerate(graph.faces)}

    # Write file.
    with open(file_path, "w") as f:

        # Global header (simplified).
        write_block(f, BlockType.GLOBAL, None, {
            'map_version_major': 1,
            'map_version_minor': 0,
        })

        # Vertices.
        for node, idx in node_to_index.items():
            vertex = {
                'x': node.get_attribute('x') * 1 / GLOBAL_SCALE,
                'z': node.get_attribute('y') * 1 / GLOBAL_SCALE,
            }
            write_block(f, BlockType.VERTEX, f'{idx} - {node}', vertex)
            logging.debug(f'Adding vertex: {vertex}')

        # Lines. One per hedge.
        # Watch the winding order...
        for edge, idx in edge_to_index.items():
            line = {
                'v1': node_to_index[edge.tail],
                'v2': node_to_index[edge.head],
            }
            if edge.reversed is None:
                line['side_middle'] = idx
            else:
                line['is_portal'] = True
                line['line_opposite'] = edge_to_index.get(edge.reversed)
            write_block(f, BlockType.LINE, f'{idx} - {edge}', line)
            logging.debug(f'Adding vertex: {vertex}')

        # Sides.
        # TODO: Need upper / lower etc for height difference.
        for edge, i in edge_to_index.items():
            side = {
                'line': edge_to_index[edge],    # This is wrong...
                'sector': face_to_index[edge.face],
                'side_plane': {},
                'side_texture': {
                    'path': 'Editor/Default.png',
                    'scale': (0.2, 0.2),
                },
            }
            write_block(f, BlockType.SIDE, i, side)

        # Sectors.
        for face, i in face_to_index.items():
            v_str = ', '.join([str(node_to_index[node]) for node in reversed(face.nodes)])
            l_str = ', '.join([str(edge_to_index[edge]) for edge in reversed(face.edges)])
            write_block(f, BlockType.SECTOR, i, {
                'layer': 0,
                'vertices': v_str,
                'lines': l_str,
                'height_ceiling': 3,
                'floor_slope': {},
                'nceiling_slope': {},
                'floor_texture': {
                    'path': 'Editor/Default.png',
                    'scale': (0.2, 0.2),
                },
                'ceiling_texture': {
                    'path': 'Editor/Default.png',
                    'scale': (0.2, 0.2),
                },
                'floor_plane': {},
                'ceiling_plane': {},
            })

        # Player start.
        write_block(f, BlockType.THING, 0, {
            'layer': 0,
            'x': 0,
            'y': 0,
            'z': 0,
            'definition_id': ThingDefinition.MIKE.value,
            'height': 0,
        })
