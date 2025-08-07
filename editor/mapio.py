import io
from collections import defaultdict

from PySide6.QtCore import QPointF

from editor.constants import MapFormat
from editor.graph import Graph
from gameengines.build.blood import Map as BloodMap, MapReader as BloodMapReader, MapWriter as BloodMapWriter
from gameengines.build.duke3d import Map as Duke3dMap, MapReader as Duke3dMapReader, MapWriter as Duke3dMapWriter
from gameengines.build.map import Sector, Wall


def import_map(graph: Graph, file_path: str, format: MapFormat):
    graph.data.clear()
    graph.faces.clear()

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
            wall_set = wall_to_walls.get(nextwall_data.point2,
                                         wall_to_walls[wall])
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
        # graph.data.nodes[head]['x'] = wall_data.x
        # graph.data.nodes[head]['y'] = wall_data.y
        graph.data.nodes[head]['pos'] = QPointF(wall_data.x, wall_data.y)
        graph.data.edges[(head, tail)]['wall'] = wall_data

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

        graph.graph['faces'][tuple(poly_nodes)] = {'sector': sector_data}

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


def export_map(graph: Graph, file_path: str, format: MapFormat):
    METER = 512
    HEIGHT = 2 * METER

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

        sector_data = face.get_attribute('sector')

        # HAXX. If the face has no sector data, give it some.
        if sector_data is None:
            sector_data = Sector()
            face.set_attribute('sector', sector_data)

        sector_data.floorz = 0
        sector_data.ceilingz = -HEIGHT * 16
        sector_data.wallptr = wallptr
        sector_data.wallnum = len(face.data)

        for i, hedge in enumerate(face.hedges):

            wall_data = hedge.get_attribute('wall')

            # HAXX. If the edge has no wall data, give it some.
            if wall_data is None:
                wall_data = Wall()
                hedge.set_attribute('wall', wall_data)

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
