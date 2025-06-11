import math
import uuid
from collections import defaultdict

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication
from shapely.geometry import LineString, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import split as split_ops

from applicationframework.actions import Composite, SetAttribute
from editor.actions import Add, Remove
from editor.graph import Edge, Hedge, Node
from editor.maths import lerp
from editor.updateflag import UpdateFlag
from gameengines.build.map import Sector, Wall

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


def select_elements(elements: set[Node] | set[Edge]):
    deselect = Composite([
        SetAttribute('is_selected', False, element)
        for element in QApplication.instance().doc.selected_elements
    ])
    select = Composite([
        SetAttribute('is_selected', True, element)
        for element in elements
    ])
    action = Composite([
        deselect,
        select,
        #DeselectElements(QApplication.instance().doc.selected_elements),
        #SelectElements(elements)
    ], flags=UpdateFlag.SELECTION)
    QApplication.instance().action_manager.push(action)
    QApplication.instance().doc.updated(action(), dirty=False)


def transform_node_items(node_items):
    actions = []
    for node_item in node_items:
        actions.append(SetAttribute('pos', node_item.pos(), node_item.element()))
    action = Composite(actions, flags=UpdateFlag.CONTENT)
    QApplication.instance().action_manager.push(action)
    QApplication.instance().doc.updated(action(), dirty=False)


def add_face(nodes: tuple[tuple], **kwargs):
    # TODO: Make func sig a little more sensical

    face = []
    edges = []
    for i in range(len(nodes)):
        head = nodes[i]
        tail = nodes[(i + 1) % len(nodes)]
        edges.append((head, tail))
        face.append(head)

    graph = QApplication.instance().doc.content

    # TODO: Factory for default data? How else does the next sector get in here?
    action = Add(
        graph,
        nodes=nodes,
        edges=tuple(edges),
        faces=(tuple(face),),
        **kwargs
    )
    QApplication.instance().action_manager.push(action)
    QApplication.instance().doc.updated(action(), dirty=True)


def long_line_through(p1, p2, buffer=1000):
    """
    Extend a line between p1 and p2 to a long line that exceeds the given bounds.
    """
    x1, y1 = p1
    x2, y2 = p2
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    dx /= length
    dy /= length

    # Extend well beyond polygon bounds
    extended_p1 = (x1 - dx * buffer, y1 - dy * buffer)
    extended_p2 = (x2 + dx * buffer, y2 + dy * buffer)

    return LineString([extended_p1, extended_p2])


def split_face(*splits: tuple[Hedge, float]):

    print('\nsplits:')
    for i, split in enumerate(splits):
        hedge, pct = split
        print(i, '->', hedge, pct)

    # Remove those edges to be split.
    del_hedges = set()
    del_faces = set()
    new_nodes = []
    new_edges = []
    new_faces = []
    node_attrs = defaultdict(dict)
    edge_attrs = defaultdict(dict)
    face_attrs = defaultdict(dict)

    content = QApplication.instance().doc.content

    last_cut_point = None
    for i, split in enumerate(splits):
        hedge, pct = split
        cut_point = lerp(hedge.head.pos, hedge.tail.pos, pct)

        del_hedges.add(hedge.data)

        if hedge.face is not None:
            del_faces.add(hedge.face)

        #if i > 0:
        if i % 2:

            if hedge.face is None:
                print('skip hedge:', hedge)
                continue

            # Create Shapely cut line and polygon.
            face_nodes = hedge.face.nodes
            x1, y1 = cut_point.to_tuple()
            x2, y2 = last_cut_point.to_tuple()
            #cut_line = LineString(((x1, y1), (x2, y2)))
            cut_line = long_line_through((x1, y1), (x2, y2))
            polygon = Polygon([node.pos.to_tuple() for node in face_nodes])

            print('polygon:', polygon)

            # Do the Shapely split op.
            result = split_ops(polygon, cut_line)
            polys = list(result.geoms)
            if len(polys) != 2:
                print("Unexpected number of polygons", len(polys))
                return

            # TODO: Test data was apparently authored anti-clockwise but Build
            # should only accept clockwise... what gives
            poly1 = orient(polys[0], sign=1.0)
            poly2 = orient(polys[1], sign=1.0)

            print('polys1:', poly1)
            print('polys2:', poly2)

            # Resolve Shapely edges.
            nodes1 = poly1.exterior.coords[:-1]
            print('nodes1:', nodes1)
            edges1 = [(nodes1[i], nodes1[(i + 1) % len(nodes1)]) for i in range(len(nodes1))]
            print('edges1:', edges1)
            nodes2 = poly2.exterior.coords[:-1]
            print('nodes2:', nodes2)
            edges2 = [(nodes2[i], nodes2[(i + 1) % len(nodes2)]) for i in range(len(nodes2))]
            print('edges2:', edges2)

            # Resolve which is the common edge, and offset amount if we need to
            # rotate faces to align.
            for i, (h1, t1) in enumerate(edges1):
                if (t1, h1) in edges2:
                    break

            cut_nodes = edges1[i]
            cut_node_ids = {
                cut_node: str(uuid.uuid4())
                for cut_node in cut_nodes
            }

            face_pos = [node.pos.to_tuple() for node in face_nodes]

            # TODO: This looks ok, I guess. But it doesn't enforce nodes being
            # sequential - ie we should use a loop instead of index as this could
            # allow retrieving nodes in the wrong order.

            print('\nmatch 1')
            face1 = {}
            for node in nodes1:
                if node in cut_nodes:
                    node_id = cut_node_ids[node]
                    pos = QPointF(*node)
                else:
                    idx = face_pos.index(node)
                    node_id = face_nodes[idx].data
                    pos = face_nodes[idx].pos
                    # print(node, node in cut_nodes, idx, face_nodes[idx])
                face1[node_id] = {'pos': pos}

            print('\nmatch 2')
            face2 = {}
            for node in nodes2:
                if node in cut_nodes:
                    node_id = cut_node_ids[node]
                    pos = QPointF(*node)
                else:
                    idx = face_pos.index(node)
                    node_id = face_nodes[idx].data
                    pos = face_nodes[idx].pos
                    #print(node, node in cut_nodes, idx, face_nodes[idx])
                face2[node_id] = {'pos': pos}

            print('\nface 1 mapped')
            for k, v in face1.items():
                print(k, '->', v)
            print('\nface 2 mapped')
            for k, v in face2.items():
                print(k, '->', v)

            new_faces.append(tuple(face1.keys()))
            new_faces.append(tuple(face2.keys()))
            node_attrs.update(face1)
            node_attrs.update(face2)

        last_cut_point = cut_point

    print('\ndel hedges:')
    for hedge in del_hedges:
        print('    ->', hedge)

    action = Composite([
        Remove(content, edges=del_hedges, faces=[f.data for f in del_faces]),
        Add(content, faces=new_faces, node_attrs=node_attrs),
    ], flags=UpdateFlag.CONTENT)
    QApplication.instance().action_manager.push(action)
    QApplication.instance().doc.updated(action(), dirty=False)


    print('\nnodes:')
    for node in content.nodes:
        print('    ->', node)
    print('\nedges:')
    for edge in content.edges:
        print('    ->', edge)
    print('\nhedges:')
    for hedge in content.hedges:
        print('    ->', hedge, '->', hedge.face)
    print('\nfaces:')
    for face in content.faces:
        print('    ->', face)
