import io
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from editor.constants import ATTRIBUTES, MapFormat
from editor.graph import Edge, Face, Graph
from editor.texture import Texture
from gameengines.build.blood import Map as BloodMap, MapReader as BloodMapReader, MapWriter as BloodMapWriter
from gameengines.build.duke3d import Map as Duke3dMap, MapReader as Duke3dMapReader, MapWriter as Duke3dMapWriter
from gameengines.build.map import Sector, Wall


logger = logging.getLogger(__name__)


def get_ring_bounds(m, ring: list[Any]) -> tuple:
    positions = [(m.walls[wall_idx].x, m.walls[wall_idx].y) for wall_idx in ring]
    min_pos = np.amin(positions, axis=0)
    max_pos = np.amax(positions, axis=0)
    return tuple(max_pos - min_pos)


def build_shade_to_brightness(shade: int, mode="dark_only") -> float:
    shade = max(0, min(32, shade))  # clamp
    return 1.0 - (shade / 32.0)


def shade_from_brightness(brightness: float) -> int:
    # Clamp brightness
    brightness = max(0.0, min(1.0, brightness))
    return int(round((1.0 - brightness) * 32))


def map_texture_to_int(tex: Texture):
    value = tex.value
    if not isinstance(value, int):
        value = 0
    return value


def map_wall_to_edge(wall: Wall):
    return {
        'cstat': wall.cstat,
        'pal': wall.pal,
        'shade': build_shade_to_brightness(wall.shade),
        'xrepeat': wall.xrepeat,
        'yrepeat': wall.yrepeat,
        'xpanning': wall.xpanning,
        'ypanning': wall.ypanning,
        'lotag': wall.lotag,
        'hitag': wall.hitag,
        'extra': wall.extra,
        'low_tex': Texture(wall.picnum),
        'mid_tex': Texture(wall.picnum),
        'top_tex': Texture(wall.overpicnum),
    }


def map_sector_to_face(sector: Sector):
    return {
        'ceilingz': sector.ceilingz / -16,
        'floorz': sector.floorz / -16,
        'ceilingstat': sector.ceilingstat,
        'floorstat': sector.floorstat,
        'ceilingheinum': sector.ceilingheinum,
        'ceilingshade': build_shade_to_brightness(sector.ceilingshade),
        'ceilingpal': sector.ceilingpal,
        'ceilingxpanning': sector.ceilingxpanning,
        'ceilingypanning': sector.ceilingypanning,
        'floorheinum': sector.floorheinum,
        'floorshade': build_shade_to_brightness(sector.floorshade),
        'floorpal': sector.floorpal,
        'floorxpanning': sector.floorxpanning,
        'floorypanning': sector.floorypanning,
        'visibility': sector.visibility,
        'filler': sector.filler,
        'lotag': sector.lotag,
        'hitag': sector.hitag,
        'extra': sector.extra,
        'floor_tex': Texture(sector.floorpicnum),
        'ceiling_tex': Texture(sector.ceilingpicnum),
    }


def map_edge_to_wall(edge: Edge):
    attrs = edge.get_attributes()
    return {
        'x': int(edge.head.pos.x()),
        'y': int(edge.head.pos.y()),
        'cstat': attrs['cstat'],
        'picnum': map_texture_to_int(attrs['mid_tex']),
        'overpicnum': map_texture_to_int(attrs['top_tex']),
        'pal': attrs['pal'],
        'shade': shade_from_brightness(attrs['shade']),
        'xrepeat': attrs['xrepeat'],
        'yrepeat': attrs['yrepeat'],
        'xpanning': attrs['xpanning'],
        'ypanning': attrs['ypanning'],
        'lotag': attrs['lotag'],
        'hitag': attrs['hitag'],
        'extra': attrs['extra'],
    }


def map_face_to_sector(face: Face):
    attrs = face.get_attributes()
    return {
        'ceilingz': int(attrs['ceilingz'] * -16),
        'floorz': int(attrs['floorz'] * -16),
        'ceilingstat': attrs['ceilingstat'],
        'floorstat': attrs['floorstat'],
        'ceilingpicnum': map_texture_to_int(attrs['ceiling_tex']),
        'ceilingheinum': attrs['ceilingheinum'],
        'ceilingshade': shade_from_brightness(attrs['ceilingshade']),
        'ceilingpal': attrs['ceilingpal'],
        'ceilingxpanning': attrs['ceilingxpanning'],
        'ceilingypanning': attrs['ceilingypanning'],
        'floorpicnum': map_texture_to_int(attrs['floor_tex']),
        'floorheinum': attrs['floorheinum'],
        'floorshade': shade_from_brightness(attrs['floorshade']),
        'floorpal': attrs['floorpal'],
        'floorxpanning': attrs['floorxpanning'],
        'floorypanning': attrs['floorypanning'],
        'visibility': attrs['visibility'],
        'filler': attrs['filler'],
        'lotag': attrs['lotag'],
        'hitag': attrs['hitag'],
        'extra': attrs['extra'],
    }


def import_build(graph: Graph, file_path: str | Path, format: MapFormat):
    map_reader_cls = {
        MapFormat.BLOOD: BloodMapReader,
        MapFormat.DUKE_3D: Duke3dMapReader,
    }[format]
    with open(file_path, 'rb') as f:
        m = map_reader_cls()(f)

    print('\nheader')
    print(m.header)

    print('\nwalls')
    for i, wall in enumerate(m.walls):
        print(i, wall)

    print('\nsectors')
    for i, sector in enumerate(m.sectors):
        print(i, sector)

    # Still not sure how this actually works :lol.
    wall_to_walls = defaultdict(set)
    for wall_idx, wall_data in enumerate(m.walls):
        wall_to_walls[wall_idx].add(wall_idx)
        if wall_data.nextwall > -1:
            nextwall_data = m.walls[wall_data.nextwall]
            wall_set = wall_to_walls.get(nextwall_data.point2, wall_to_walls[wall_idx])
            wall_set.add(wall_idx)
            wall_to_walls[wall_idx] = wall_to_walls[nextwall_data.point2] = wall_set

    print('\nwall_to_walls')
    for wall in sorted(wall_to_walls):
        print(wall, '->', wall_to_walls[wall])

    wall_to_node = {}
    nodes = set()
    for wall_dx, other_walls in wall_to_walls.items():
        node = wall_to_node[wall_dx] = frozenset(other_walls)
        nodes.add(node)

    for node in nodes:
        graph.data.add_node(node)

    print('\nwall_to_node')
    for wall in sorted(wall_to_node):
        print(wall, '->', wall_to_node[wall])

    print('\nnodes')
    for node in graph.data.nodes:
        print(node)

    # Add edges.
    for wall, wall_data in enumerate(m.walls):
        head = wall_to_node[wall]
        tail = wall_to_node[wall_data.point2]
        graph.data.add_edge(head, tail)

        # Need to set the head data.
        graph.data.nodes[head].setdefault(ATTRIBUTES, {})['x'] = wall_data.x
        graph.data.nodes[head].setdefault(ATTRIBUTES, {})['y'] = wall_data.y

        graph.data.edges[(head, tail)].setdefault(ATTRIBUTES, {})

        edge_attrs = map_wall_to_edge(wall_data)
        graph.data.edges[(head, tail)][ATTRIBUTES].update(edge_attrs)

    print('\nedges')
    for edge in graph.data.edges:
        print(edge)

    # Add sectors.
    # TODO: Sort based on size.
    for j, sector in enumerate(m.sectors):
        sector_wall_idxs = [[]]
        ring_start_idx = wall_idx = sector.wallptr
        for i in range(sector.wallnum):
            sector_wall_idxs[-1].append(wall_idx)
            wall_idx = m.walls[wall_idx].point2
            if wall_idx == ring_start_idx:
                sector_wall_idxs[-1].append(ring_start_idx)
                ring_start_idx = wall_idx = sector.wallptr + i + 1
                if i < sector.wallnum - 2:
                    sector_wall_idxs.append([])

        sorted_sector_wall_idxs = sorted(sector_wall_idxs, key=lambda x: get_ring_bounds(m, x), reverse=True)
        face_attrs = map_sector_to_face(sector)
        graph.add_face(tuple([wall_to_node[node] for face_ring in sorted_sector_wall_idxs for node in face_ring]), **face_attrs)

    graph.update()

    print('\nnodes:')
    for node in graph.nodes:
        print('    ->', node, node.pos)
    print('\nedges:')
    for edge in graph.edges:
        print('    ->', edge, '->', edge.face)
    print('\nfaces:')
    for face in graph.faces:
        print('    ->', face)


def export_build(graph: Graph, file_path: str, format: MapFormat):

    map_cls = {
        MapFormat.BLOOD: BloodMap,
        MapFormat.DUKE_3D: Duke3dMap,
    }[format]
    m = map_cls()

    edges = []
    edge_to_next_edge = {}

    wallptr = 0
    sector = 0
    faces = list(graph.faces)
    for face in faces:
        sector_attrs = map_face_to_sector(face)
        sector_data = Sector(**sector_attrs)
        sector_data.wallptr = wallptr
        sector_data.wallnum = len(face.edges)
        for ring in face.rings:
            for i, edge in enumerate(ring.edges):
                wall_attrs = map_edge_to_wall(edge)
                wall_data = Wall(**wall_attrs)
                logger.debug(f'Added wall: {wall_data}')
                edges.append(edge)
                m.walls.append(wall_data)
                edge_to_next_edge[edge] = ring.edges[(i + 1) % len(ring.edges)]
        m.sectors.append(sector_data)
        sector += 1
        wallptr += len(face.nodes)

    m.cursectnum = 0

    # print('\nedge_map:')
    # for foo, bar in edge_map.items():
    #     print(foo, '->', bar)

    # Now we have all walls, go back through and fixup the point2.
    for wall, edge in enumerate(edges):
        wall_data = m.walls[wall]
        next_edge = edge_to_next_edge[edge]
        wall_data.point2 = edges.index(next_edge)

    # Do portals.
    for wall, edge in enumerate(edges):
        head, tail = edge.head, edge.tail
        if graph.has_edge(tail, head):
            redge = graph.get_edge(tail, head)
            try:
                next_sector = faces.index(redge.face)
            except:
                continue
            wall_data = m.walls[wall]
            wall_data.nextsector = next_sector
            wall_data.nextwall = edges.index(redge)

    print('\nheader')
    print(m.header)

    print('\nwalls')
    for wall in m.walls:
        print(wall)

    print('\nsectors')
    for sector in m.sectors:
        print(sector)

    output = io.BytesIO()
    map_writer_cls = {
        MapFormat.BLOOD: BloodMapWriter,
        MapFormat.DUKE_3D: Duke3dMapWriter,
    }[format]
    map_writer_cls()(m, output)
    with open(file_path, 'wb') as f:
        f.write(output.getbuffer())
