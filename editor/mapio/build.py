import io
from typing import Any
from collections import defaultdict
from dataclasses import fields
from pathlib import Path

import numpy as np

from editor.constants import ATTRIBUTES
from editor.constants import MapFormat
from editor.graph import Graph
from gameengines.build.blood import Map as BloodMap, MapReader as BloodMapReader, MapWriter as BloodMapWriter
from gameengines.build.duke3d import Map as Duke3dMap, MapReader as Duke3dMapReader, MapWriter as Duke3dMapWriter
from gameengines.build.map import Sector, Wall


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
        for field in fields(wall_data):
            graph.data.edges[(head, tail)][ATTRIBUTES][field.name] = getattr(wall_data, field.name)

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
        face_attrs = {
            field.name: getattr(sector, field.name)
            for field in fields(sector)
        }
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

    # HAXXOR
    # Map attributes to some sensible internal values.
    for edge in graph.edges:
        edge.set_attribute('shade', build_shade_to_brightness(edge.get_attribute('shade')))
    for face in graph.faces:
        face.set_attribute('floorshade', build_shade_to_brightness(face.get_attribute('floorshade')))
        face.set_attribute('ceilingshade', build_shade_to_brightness(face.get_attribute('ceilingshade')))
        face.set_attribute('floorz', face.get_attribute('floorz') / -16)
        face.set_attribute('ceilingz', face.get_attribute('ceilingz') / -16)


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
        sector_data = Sector(**face.get_attributes())
        sector_data.wallptr = wallptr
        sector_data.wallnum = len(face.edges)
        for i, edge in enumerate(face.edges):
            wall_data = Wall(**edge.get_attributes())
            wall_data.x = int(edge.head.pos.x())
            wall_data.y = int(edge.head.pos.y())
            edges.append(edge)
            m.walls.append(wall_data)
            edge_to_next_edge[edge] = face.edges[(i + 1) % len(face.edges)]
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

    # HAXXOR
    # Map *from* internal values.
    for wall in m.walls:
        wall.shade = int(shade_from_brightness(wall.shade))
    for sector in m.sectors:
        sector.floorshade = int(shade_from_brightness(sector.floorshade))
        sector.ceilingshade = int(shade_from_brightness(sector.ceilingshade))
        sector.floorz = int(sector.floorz * -16)
        sector.ceilingz = int(sector.ceilingz * -16)

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
