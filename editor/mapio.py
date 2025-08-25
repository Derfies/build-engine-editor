import io
from collections import defaultdict
from dataclasses import fields
from pathlib import Path

from editor.constants import ATTRIBUTES, ATTRIBUTE_DEFINITIONS, FACE, FACES, GRAPH, HEDGE, NODE
from editor.constants import MapFormat
from editor.graph import Graph
from editor.readwrite import write_gexf
from gameengines.build.blood import Map as BloodMap, MapReader as BloodMapReader, MapWriter as BloodMapWriter
from gameengines.build.duke3d import Map as Duke3dMap, MapReader as Duke3dMapReader, MapWriter as Duke3dMapWriter
from gameengines.build.map import Sector, Wall


def import_map(graph: Graph, file_path: str | Path, format: MapFormat):

    # TODO: Pass the graph in or just create a new one? I suppose we want to support
    # merging via imports.
    # Also need to init graph default attrs.
    #graph.data.clear()
    #graph.data.graph[FACES] = {}

    # Add default attribute definitions.
    for field in fields(Wall):
        graph.add_hedge_attribute_definition(field.name, field.type, field.default)
    for field in fields(Sector):
        graph.add_face_attribute_definition(field.name, field.type, field.default)

    # TODO: Move this into an import function and let this serialize the native
    # map format.
    map_reader_cls = {
        MapFormat.BLOOD: BloodMapReader,
        MapFormat.DUKE_3D: Duke3dMapReader,
    }[format]
    with open(file_path, 'rb') as f:
        m = map_reader_cls()(f)

    print('\nheader')
    print(m.header)

    print('\nwalls')
    for wall in m.walls:
        print(wall)

    print('\nsectors')
    for sector in m.sectors:
        print(sector)

    # Still not sure how this actually works :lol.
    wall_to_walls = defaultdict(set)
    for wall, wall_data in enumerate(m.walls):
        wall_to_walls[wall].add(wall)
        if wall_data.nextwall > -1:
            nextwall_data = m.walls[wall_data.nextwall]
            wall_set = wall_to_walls.get(nextwall_data.point2, wall_to_walls[wall])
            wall_set.add(wall)
            wall_to_walls[wall] = wall_to_walls[nextwall_data.point2] = wall_set

    print('\nwall_to_walls')
    for wall in sorted(wall_to_walls):
        print(wall, '->', wall_to_walls[wall])

    wall_to_node = {}
    nodes = set()
    for wall, other_walls in wall_to_walls.items():
        node = wall_to_node[wall] = frozenset(other_walls)
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
        # print('CREATE:', head, '->', tail)
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

    # TODO: Change to edges to define polygon.
    for i, sector_data in enumerate(m.sectors):
        poly_nodes = []

        # This might not be right. I think this works on the assumption that
        # all sectors walls are written in order, which they're not guaranteed
        # to be.
        start_wall = wall = sector_data.wallptr
        for _ in range(sector_data.wallnum):
            wall_data = m.walls[wall]
            poly_nodes.append(wall_to_node[wall])
            wall = wall_data.point2

            if wall == start_wall:
                # print('break')
                break

        graph.data.graph[FACES].setdefault(tuple(poly_nodes), {}).setdefault(ATTRIBUTES, {})
        for field in fields(sector_data):
           graph.data.graph[FACES][tuple(poly_nodes)][ATTRIBUTES][field.name] = getattr(sector_data, field.name)

    graph.update()

    print('\nnodes:')
    for node in graph.nodes:
        print('    ->', node, node.pos)
    print('\nedges:')
    for edge in graph.edges:
        print('    ->', edge)
    print('\nhedges:')
    for hedge in graph.hedges:
        print('    ->', hedge, '->', hedge.face)
    print('\nfaces:')
    for face in graph.faces:
        print('    ->', face)


def export_gexf(graph: Graph, file_path: str, format: MapFormat):

    # TODO: Comment.
    g = graph.data.copy()

    for node, attrs in g.nodes(data=True):
        attrs.update(attrs.pop(ATTRIBUTES))
        attrs['viz'] = {'position': {'x': attrs.pop('x'), 'y': attrs.pop('y'), 'z': 0}}

        # TODO: Move this attr
        attrs.pop('is_selected', None)

    for head, tail, attrs in g.edges(data=True):
        attrs.update(attrs.pop(ATTRIBUTES))

        attrs.pop('is_selected', None)

    # Flatten settings data?
    for attr_dict in g.graph[ATTRIBUTE_DEFINITIONS][GRAPH]:
        g.graph[attr_dict['name']] = attr_dict['default']

    g.graph['node_default'] = graph.get_default_node_data()
    g.graph['edge_default'] = graph.get_default_hedge_data()
    del g.graph[ATTRIBUTE_DEFINITIONS]

    write_gexf(g, file_path)


def export_map(graph: Graph, file_path: str, format: MapFormat):

    map_cls = {
        MapFormat.BLOOD: BloodMap,
        MapFormat.DUKE_3D: Duke3dMap,
    }[format]
    m = map_cls()

    hedges = []
    edge_to_next_edge = {}

    wallptr = 0
    sector = 0
    faces = list(graph.faces)
    for face in faces:

        sector_data = Sector(**face.get_attributes())
        sector_data.wallptr = wallptr
        sector_data.wallnum = len(face.data)

        for i, hedge in enumerate(face.hedges):
            wall_data = Wall(**hedge.get_attributes())
            wall_data.x = int(hedge.head.pos.x())
            wall_data.y = int(hedge.head.pos.y())
            hedges.append(hedge)
            m.walls.append(wall_data)

            edge_to_next_edge[hedge] = face.hedges[(i + 1) % len(face.hedges)]

        m.sectors.append(sector_data)
        sector += 1
        wallptr += len(face.nodes)

    m.cursectnum = 0

    # print('\nedge_map:')
    # for foo, bar in edge_map.items():
    #     print(foo, '->', bar)

    # Now we have all walls, go back through and fixup the point2.
    for wall, hedge in enumerate(hedges):
        wall_data = m.walls[wall]
        next_edge = edge_to_next_edge[hedge]
        wall_data.point2 = hedges.index(next_edge)

    # Do portals.
    for wall, hedge in enumerate(hedges):

        head, tail = hedge.head, hedge.tail
        if graph.has_hedge(tail, head):
            rhedge = graph.get_hedge(tail, head)
            next_sector = faces.index(rhedge.face)

            wall_data = m.walls[wall]
            wall_data.nextsector = next_sector
            wall_data.nextwall = hedges.index(rhedge)

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
