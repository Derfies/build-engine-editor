import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import omg
from omg import WAD, MapEditor
from omg.mapedit import Vertex, Linedef, Sidedef, Sector, Thing

from editor.constants import MapFormat
from editor.graph import Edge, Face, Graph
from editor.texture import Texture


def get_ring_bounds(m, ring: list[Any]) -> tuple:
    positions = [(edge.head.get_attribute('x'), edge.tail.get_attribute('y')) for edge in ring]
    min_pos = np.amin(positions, axis=0)
    max_pos = np.amax(positions, axis=0)
    return tuple(max_pos - min_pos)


def map_wall_to_edge(side: Sidedef, sector: Sector):
    return {
        'low_tex': Texture(side.texturebottom),
        'mid_tex': Texture(side.texturemiddle),
        'top_tex': Texture(side.texturetop),
        'shade': sector.lightlevel / 255 + 0.1,
    }


def map_sector_to_face(sector: Sector, global_scale):
    return {
        'ceilingshade': sector.lightlevel / 255,
        'floorshade': sector.lightlevel / 255,
        'ceilingz': sector.heightceiling * global_scale,
        'floorz': sector.heightfloor * global_scale,
        'floor_tex': Texture(sector.texturefloor),
        'ceiling_tex': Texture(sector.textureceiling),
    }


def map_face_to_sector(face: Face, global_scale: float):
    """
    NOTE: Casting to string in case the textures originally came from an engine
    that used integers to index their textures.

    """
    attrs = face.get_attributes()
    return {
        'z_floor': int(attrs['floorz'] * global_scale),
        'z_ceil': int(attrs['ceilingz'] * global_scale),
        'tx_floor': str(attrs['floor_tex'].value),
        'tx_ceil': str(attrs['ceiling_tex'].value),
    }


def map_edge_to_side(edge: Edge, face_to_index: dict):
    """
    NOTE: Casting to string in case the textures originally came from an engine
    that used integers to index their textures.

    """
    edge_attrs = edge.get_attributes()
    attrs = {
        'off_x': 0,
        'off_y': 0,
        'sector': face_to_index[edge.face],
    }
    if edge.reversed is None:
        attrs['tx_mid'] = str(edge_attrs['mid_tex'].value)
    else:
        attrs['tx_up'] = str(edge_attrs['top_tex'].value)
        attrs['tx_low'] = str(edge_attrs['low_tex'].value)
    return attrs


def order_tuples_into_chains(tuples):
    if not tuples:
        return []

    unused = set(tuples)
    chains = []

    while unused:
        # Pick a starting tuple
        current = unused.pop()
        chain = [current]

        # Extend forward
        while True:
            last = chain[-1]
            next_tuple = None
            for t in list(unused):
                if t.head == last.tail:
                    next_tuple = t
                    break
            if not next_tuple:
                break
            chain.append(next_tuple)
            unused.remove(next_tuple)

            # Loop closed?
            if chain[-1].tail == chain[0].head:
                chain.append(chain[0])
                break

        chains.append(chain)

    return chains


def import_doom(graph: Graph, file_path: str | Path, format: MapFormat):

    global_scale = 14

    # TODO: Support wadded level selection.
    wad = omg.WAD()
    wad.from_file(file_path)
    m = omg.UMapEditor(wad.maps['E1M1'])

    # Nodes.
    nodes = []
    for i, vertex in enumerate(m.vertexes):
        node = graph.add_node(i, x=vertex.x * global_scale, y=vertex.y * global_scale)
        nodes.append(node)

    # Edges.
    # We change the lighting just a bit to make things visible, otherwise apparently
    # there is no per-wall lighting.
    sector_idx_to_edges = defaultdict(list)
    for i, line in enumerate(m.linedefs):
        for reverse, side_idx in enumerate((line.sidefront, line.sideback)):
            if side_idx < 0:
                continue
            head, tail = line.v2, line.v1
            if reverse:
                head, tail = tail, head
            side = m.sidedefs[side_idx]
            sector_idx = side.sector
            sector = m.sectors[sector_idx]
            edge_attrs = map_wall_to_edge(side, sector)
            edge = graph.add_edge((head, tail), **edge_attrs)
            sector_idx_to_edges[sector_idx].append(edge)

    for sector_idx, edges in sector_idx_to_edges.items():
        sector = m.sectors[sector_idx]
        rings = order_tuples_into_chains(edges)
        face_attrs = map_sector_to_face(sector, global_scale)
        sorted_rings = sorted(rings, key=lambda r: get_ring_bounds(m, r), reverse=True)
        graph.add_face(tuple([node.head.data for ring in sorted_rings for node in ring]), **face_attrs)

    graph.update()


def export_doom(graph: Graph, file_path: str | Path, format: MapFormat):

    global_scale = 1/ 14

    # Assign indices.
    node_to_index = {node: i for i, node in enumerate(graph.nodes)}
    edge_to_index = {edge: i for i, edge in enumerate(graph.edges)}
    face_to_index = {face: i for i, face in enumerate(graph.faces)}

    # Create a new map editor instance
    m = MapEditor()

    # Vertices.
    for node in node_to_index:
        vertex = Vertex(int(node.get_attribute('x') * global_scale), int(node.get_attribute('y') * global_scale))
        m.vertexes.append(vertex)
        logging.debug(f'Adding vertex: {vertex}')

    # Sidedefs. One per hedge.
    for edge in edge_to_index:
        if edge.face is None:
            print('No face')
            continue
        side_attrs = map_edge_to_side(edge, face_to_index)
        sidedef = Sidedef(**side_attrs)
        m.sidedefs.append(sidedef)
        logging.debug(f'Adding sidedef: {sidedef}')

    # Linedefs. One per edge only - ie hedges are shared.
    # Watch the winding order...
    linedefs = {}
    for edge in edge_to_index:
        if edge.face is None:
            print('No face')
            continue
        linedef = linedefs.get(edge.reversed)
        if linedef is None:
            linedef = Linedef(
                vx_a=node_to_index[edge.tail],
                vx_b=node_to_index[edge.head],
                front=edge_to_index[edge],
            )
            linedefs[edge] = linedef
        else:
            linedef.back = edge_to_index[edge]
        logging.debug(f'Adding linedef: {linedef}') # TODO: Fix logging
    m.linedefs.extend(linedefs.values())

    # Sectors.
    for face in face_to_index:
        sector = Sector(**map_face_to_sector(face, global_scale))
        m.sectors.append(sector)
        logging.debug(f'Adding sector: {sector}')

    # Things.
    # Player 1 start thing (type 1)
    m.things = [
        Thing(x=0, y=0, angle=0, type=1),
    ]

    # Insert into WAD and save.
    w = WAD()
    w.maps['MAP01'] = m.to_lumps()
    w.to_file(str(file_path))
