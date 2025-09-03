import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from editor.constants import MapFormat
from editor.graph import Graph


logger = logging.getLogger(__name__)


class Type(Enum):

    GLOBAL= 'Global'
    VERTEX = 'Vertex'
    LINE = 'Line'
    SIDE = 'Side'
    SECTOR = 'Sector'
    THING = 'Thing'


class ThingDefinition(Enum):

    MIKE = 13484


@dataclass
class Block:

    type: Type
    id: Any | None
    attrs: dict


def write_block(f, type_: Type, id_: Any, attrs: dict):

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

    global_scale = 0.001

    # Assign indices.
    node_to_index = {node: i for i, node in enumerate(graph.nodes)}
    edge_to_index = {edge: i for i, edge in enumerate(graph.edges)}
    face_to_index = {face: i for i, face in enumerate(graph.faces)}

    # Write file.
    with open(file_path, "w") as f:

        # Global header (simplified).
        write_block(f, Type.GLOBAL, None, {
            'map_version_major': 1,
            'map_version_minor': 0,
        })

        # Vertices.
        for node, idx in node_to_index.items():
            vertex = {
                'x': node.get_attribute('x') * global_scale,
                'z': node.get_attribute('y') * global_scale,
            }
            write_block(f, Type.VERTEX, f'{idx} - {node}', vertex)
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
            write_block(f, Type.LINE, f'{idx} - {edge}', line)
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
            write_block(f, Type.SIDE, i, side)

        # Sectors.
        for face, i in face_to_index.items():
            v_str = ', '.join([str(node_to_index[node]) for node in reversed(face.nodes)])
            l_str = ', '.join([str(edge_to_index[edge]) for edge in reversed(face.edges)])
            write_block(f, Type.SECTOR, i, {
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
        write_block(f, Type.THING, 0, {
            'layer': 0,
            'x': 0,
            'y': 0,
            'z': 0,
            'definition_id': ThingDefinition.MIKE.value,
            'height': 0,
        })
