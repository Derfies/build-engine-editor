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
    edit = omg.UMapEditor(wad.maps['E1M1'])

    node_map = {}
    for i, vertex in enumerate(edit.vertexes):
        node = graph.add_node(i, x=vertex.x * global_scale, y=vertex.y * global_scale)
        node_map[i] = node

    for i, linedef in enumerate(edit.linedefs):
        if linedef.sidefront >= 0:
            graph.add_edge((node_map[linedef.v2], node_map[linedef.v1]))
        if linedef.sideback >= 0:
            graph.add_edge((node_map[linedef.v1], node_map[linedef.v2]))


    faces = {}
    for i, linedef in enumerate(edit.linedefs):

        front_sector = edit.sidedefs[linedef.sidefront].sector
        faces.setdefault(front_sector, []).append((linedef.v1, linedef.v2))

        back_sector = edit.sidedefs[linedef.sideback].sector
        faces.setdefault(back_sector, []).append((linedef.v2, linedef.v1))

    for k, v in faces.items():
        try:
            ordered = order_tuples(v)
        except:
            continue
        #print(k, '->', v, order_tuples(v))
        else:
            print(ordered)
            graph.add_face(tuple(reversed([o[0] for o in ordered])))
    graph.update()


def export_doom(graph: Graph, file_path: str | Path, format: MapFormat):
    global_scale = 0.1

    MAP_NAME = 'MAP01'

    # Create a new WAD
    w = WAD()

    # Create a new map editor instance
    m = MapEditor()

    # Assign indices.
    node_to_index = {node: i for i, node in enumerate(graph.nodes)}

    # Vertices for a square room
    m.vertexes = [
        Vertex(int(node.get_attribute('x') * global_scale), int(node.get_attribute('y') * global_scale))
        for node in node_to_index
    ]

    for v in m.vertexes:
        print(v.x, v.y)

    # One sector (floor = 0, ceil = 128, flats are FLOOR0_1 and CEIL1_1)
    m.sectors = [
        Sector(z_floor=0, z_ceil=128, tx_floor="FLAT1", tx_ceil="FLAT1")
    ]

    # Linedefs around the square
    m.sidedefs = []
    m.linedefs = []
    for face in graph.faces:
        for i, edge in enumerate(face.edges):
            m.sidedefs.append(Sidedef(off_x=0, off_y=0, tx_mid="STARTAN3", sector=0))
            m.linedefs.append(Linedef(vx_a=node_to_index[edge.tail], vx_b=node_to_index[edge.head], front=i))

    # Player 1 start thing (type 1)
    m.things = [
        Thing(x=0, y=0, angle=0, type=1)
    ]

    # Insert into WAD
    w.maps[MAP_NAME] = m.to_lumps()

    w.to_file(str(file_path))
