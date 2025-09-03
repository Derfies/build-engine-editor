import logging
from collections import defaultdict
from pathlib import Path

import omg
from omg import WAD, MapEditor
from omg.mapedit import Vertex, Linedef, Sidedef, Sector, Thing

from editor.constants import MapFormat
from editor.graph import Graph


def order_tuples(tuples):
    if not tuples:
        return []

    # Build a mapping from start -> tuple
    start_map = {t[0]: t for t in tuples}

    # Find a starting tuple (whose start is never an end)
    all_starts = set(t[0] for t in tuples)
    all_ends = set(t[1] for t in tuples)
    start_candidates = all_starts - all_ends
    if start_candidates:
        start_val = start_candidates.pop()
        current = start_map[start_val]
    else:
        # No unique start, just pick the first tuple
        current = tuples[0]

    ordered = [current]
    used = set([current])

    while len(ordered) < len(tuples):
        last = ordered[-1]
        next_tuple = None
        for t in tuples:
            if t in used:
                continue
            if t[0] == last[1]:
                next_tuple = t
                break
        if not next_tuple:
            raise ValueError("Cannot chain all tuples", tuples)
        ordered.append(next_tuple)
        used.add(next_tuple)

    return ordered


def import_doom(graph: Graph, file_path: str | Path, format: MapFormat):

    global_scale = 10

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
    for i, linedef in enumerate(m.linedefs):
        if linedef.sidefront > -1:
            shade = m.sectors[m.sidedefs[linedef.sidefront].sector].lightlevel / 255 + 0.1
            graph.add_edge((nodes[linedef.v2], nodes[linedef.v1]), shade=shade)
        if linedef.sideback > -1:
            shade = m.sectors[m.sidedefs[linedef.sideback].sector].lightlevel / 255 + 0.1
            graph.add_edge((nodes[linedef.v1], nodes[linedef.v2]), shade=shade)

    # Faces.
    # I need to build a face.
    # which means i need the vertices for that face.
    # linedef -> sidedef -> sector

    # Linedefs. One per edge only
    sector_to_linedefs = defaultdict(list)
    for i, linedef in enumerate(m.linedefs):
        front_sector = m.sidedefs[linedef.sidefront].sector
        sector_to_linedefs[front_sector].append((linedef.v2, linedef.v1))
        back_sector = m.sidedefs[linedef.sideback].sector
        sector_to_linedefs[back_sector].append((linedef.v1, linedef.v2))

    #i = 0
    for sector_idx, linedefs in sector_to_linedefs.items():
        #print(sector, '->', linedefs)
        try:
            ordered = order_tuples(linedefs)
        except:
            continue
        #print(k, '->', v, order_tuples(v))
        else:
            print(ordered)
            sector_attrs = {
                'ceilingshade': m.sectors[sector_idx].lightlevel / 255,
                'floorshade': m.sectors[sector_idx].lightlevel / 255,
                'ceilingz': m.sectors[sector_idx].heightceiling * global_scale,
                'floorz': m.sectors[sector_idx].heightfloor * global_scale,
            }
            face = [o[0] for o in ordered] + [ordered[0][0]]
            graph.add_face(tuple(face), **sector_attrs)



    graph.update()


def export_doom(graph: Graph, file_path: str | Path, format: MapFormat):

    global_scale = 0.1

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
            continue
        tx_attrs = {
            'off_x': 0,
            'off_y': 0,
            'sector': face_to_index[edge.face],
        }
        if edge.reversed is None:
            tx_attrs['tx_mid'] = 'STARTAN3'
        else:
            tx_attrs['tx_up'] = 'STARTAN3'
            tx_attrs['tx_low'] = 'STARTAN3'
        sidedef = Sidedef(**tx_attrs)
        m.sidedefs.append(sidedef)
        logging.debug(f'Adding sidedef: {sidedef}')

    # Linedefs. One per edge only - ie hedges are shared.
    # Watch the winding order...
    linedefs = {}
    for edge in edge_to_index:
        linedef = linedefs.get(edge.reversed)
        if linedef is None:
            linedef = Linedef(vx_a=node_to_index[edge.tail], vx_b=node_to_index[edge.head], front=edge_to_index[edge])
            linedefs[edge] = linedef
        else:
            linedef.back = edge_to_index[edge.reversed]
        logging.debug(f'Adding linedef: {linedef}') # TODO: Fix logging
    m.linedefs.extend(linedefs.values())

    # Sectors.
    for face in face_to_index:
        sector = Sector(z_floor=0, z_ceil=128, tx_floor='FLAT1', tx_ceil='FLAT1')
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
