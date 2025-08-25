import uuid
from itertools import combinations
from typing import Iterable

import numpy as np
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication
from shapely.geometry import LineString, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import split as split_ops

from applicationframework.actions import Composite, SetAttribute, SetKey
from editor.actions import Add, Remove, SetElementAttribute, Tweak
from editor.graph import Edge, Face, Hedge, Node
from editor.maths import lerp, long_line_through, midpoint
from editor.updateflag import UpdateFlag

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


NORMAL_TOLERANCE = 0
MAX_DISTANCE = 10000.0


def select_elements(elements: Iterable[Node] | Iterable[Edge] | Iterable[Hedge] | Iterable[Face]):
    actions = []
    for element in QApplication.instance().doc.selected_elements:
        actions.append(SetAttribute('is_selected', False, element))
    for element in elements:
        actions.append(SetAttribute('is_selected', True, element))
    action = Composite(actions, flags=UpdateFlag.SELECTION)
    QApplication.instance().action_manager.push(action)
    QApplication.instance().doc.updated(action(), dirty=False)


def remove_elements(elements: set[Node] | set[Edge] | set[Face]):

    # TODO: Set selection back.
    # TODO: Need some traversal to add all connected elements.
    tweak = Tweak()
    for element in elements:
        if isinstance(element, Node):
            tweak.nodes.add(element.data)
            tweak.hedges.update([hedge.data for hedge in element.hedges])
            tweak.faces.update([face.data for face in element.faces])
            tweak.node_attrs[element.data]['pos'] = element.pos
        if isinstance(element, Edge):
            tweak.hedges.update([hedge.data for hedge in element.hedges])
            tweak.faces.update([face.data for face in element.faces])
        if isinstance(element, Face):
            tweak.faces.add(element.data)

    action = Remove(tweak, QApplication.instance().doc.content)
    QApplication.instance().action_manager.push(action)
    QApplication.instance().doc.updated(action(), dirty=False)


def transform_node_items(node_items):
    action = Composite([
        SetAttribute('pos', node_item.pos(), node_item.element())
        for node_item in node_items
    ], flags=UpdateFlag.CONTENT)
    QApplication.instance().action_manager.push(action)
    QApplication.instance().doc.updated(action(), dirty=False)


def add_face(points: Iterable[tuple]):

    # Ensure winding order is consistent.
    poly = orient(Polygon(points), sign=1.0)
    coords = poly.exterior.coords[:-1]

    tweak = Tweak()
    nodes = [str(uuid.uuid4()) for _ in range(len(coords))]
    hedges = []
    face = tuple(nodes)
    for i in range(len(nodes)):
        head = nodes[i]
        tail = nodes[(i + 1) % len(nodes)]
        hedges.append((head, tail))
        tweak.node_attrs[nodes[i]]['x'] = coords[i][0]
        tweak.node_attrs[nodes[i]]['y'] = coords[i][1]

    tweak.nodes.update(nodes)
    tweak.hedges.update(hedges)
    tweak.faces.add(face)

    action = Add(tweak, QApplication.instance().doc.content)
    QApplication.instance().action_manager.push(action)
    QApplication.instance().doc.updated(action(), dirty=True)


def split_face(*splits: tuple[Hedge, float]):

    print('\nsplits:')
    for i, split in enumerate(splits):
        hedge, pct = split
        print(i, '->', hedge, pct)

    # Remove those edges to be split.
    add_tweak = Tweak()
    rem_tweak = Tweak()

    content = QApplication.instance().doc.content

    last_cut_point = None
    for i, split in enumerate(splits):
        hedge, pct = split
        cut_point = lerp(hedge.head.pos, hedge.tail.pos, pct)

        rem_tweak.hedges.add(hedge.data)

        if hedge.face is not None:
            rem_tweak.faces.add(hedge.face.data)

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
                    #add_edges.append((h1, t1))
                    #add_edges.append((t1, h1))
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

            # TODO: I think I need to remove the edges that were already here...
            nodes1 = list(face1.keys())
            nodes2 = list(face2.keys())
            add_tweak.nodes.update(nodes1)
            add_tweak.nodes.update(nodes2)
            add_tweak.faces.add(tuple(face1.keys()))
            add_tweak.faces.add(tuple(face2.keys()))
            add_tweak.node_attrs.update(face1)
            add_tweak.node_attrs.update(face2)

            add_tweak.hedges.update([
                (nodes1[i], nodes1[(i + 1) % len(nodes1)]) for i in range(len(nodes1))
            ])
            add_tweak.hedges.update([
                (nodes2[i], nodes2[(i + 1) % len(nodes2)]) for i in
                range(len(nodes2))
            ])

        last_cut_point = cut_point

    print('add tweak:', add_tweak)
    print('rem tweak:', rem_tweak)

    # Face attrs.
    action = Composite([
        Remove(rem_tweak, content),
        Add(add_tweak, content),
    ], flags=UpdateFlag.CONTENT)
    QApplication.instance().action_manager.push(action)
    QApplication.instance().doc.updated(action(), dirty=False)


def find_all_candidate_matches(hedges: Iterable[Hedge], max_distance: float = 50.0, normal_tolerance: float = 0.0):
    candidates = []
    for i, (hedge1, hedge2) in enumerate(combinations(hedges, 2)):

        # Don't attempt to match hedges that belong to the same face.
        if hedge1.face == hedge2.face:
            continue

        # Ignore when edge normals aren't pointed roughly towards each other.
        n1 = hedge1.normal
        n2 = hedge2.normal
        if np.dot(n1, n2) > normal_tolerance:
            continue

        # Don't merge if edge midpoints are too far apart.
        mid1 = LineString((hedge1.head.pos.to_tuple(), hedge1.tail.pos.to_tuple())).interpolate(0.5, normalized=True)
        mid2 = LineString((hedge2.head.pos.to_tuple(), hedge2.tail.pos.to_tuple())).interpolate(0.5, normalized=True)
        dist = mid1.distance(mid2)
        if dist > max_distance:
            continue

        candidates.append((dist, hedge1, hedge2))

    # Sort all valid candidates by score.
    candidates.sort(key=lambda c: c[0])
    return candidates


def join_edges(*edges: Iterable[Edge] | Iterable[Hedge]) -> tuple[Tweak, Tweak]:

    # TODO: Decide what func sig should look like. Does it take hedges or edges?
    # If this is meant to be a programmer's interface, it should probably not be ambiguous
    # Only joins faces to other faces. Even though the editor techincally supports
    # face-less edges, for the purposes of joining edges that feels like a restriction
    # we can make.
    hedges = set()
    for edge in edges:
        if isinstance(edge, Edge):
            hedges.update(edge.hedges)
        else:
            hedges.add(edge)


    print('hedges:', hedges)
    groups = find_all_candidate_matches(hedges, MAX_DISTANCE, NORMAL_TOLERANCE)
    print('\ngroups:')
    for _, hedge1, hedge2 in groups:
        print('    hedge1, hedge2:', hedge1, hedge2)

    # Create maps for new node names and positions.
    matched = set()
    node_to_new_node = {}
    node_to_new_pos = {}
    for _, hedge1, hedge2 in groups:

        if hedge1 in matched or hedge2 in matched:
            continue
        matched.add(hedge1)
        matched.add(hedge2)

        print('\nhedge1, hedge2:', hedge1, hedge2)
        new_node1 = node_to_new_node.get(hedge1.head, node_to_new_node.get(hedge2.tail))#, str(uuid.uuid4()))
        new_node2 = node_to_new_node.get(hedge1.tail, node_to_new_node.get(hedge2.head))#, str(uuid.uuid4()))

        print('    hedge1.head:', hedge1.head)
        print('    hedge2.tail:', hedge2.tail)
        print('    new_node1:', new_node1)

        # Do we need to search for the equivalent hedge2 head / tail if the above
        # cannot be found?
        if new_node1 is None:
            new_node1 = str(uuid.uuid4())
            print('    create new_node1:', new_node1)

        print('')
        print('    hedge1.tail:', hedge1.tail)
        print('    hedge2.head:', hedge2.head)
        print('    new_node2:', new_node2)

        if new_node2 is None:
            new_node2 = str(uuid.uuid4())
            print('    create new_node2:', new_node2)
        node_to_new_node[hedge1.head] = node_to_new_node[hedge2.tail] = new_node1
        node_to_new_node[hedge1.tail] = node_to_new_node[hedge2.head] = new_node2
        midpoint1 = midpoint(hedge1.head.pos.to_tuple(), hedge2.tail.pos.to_tuple())
        midpoint2 = midpoint(hedge1.tail.pos.to_tuple(), hedge2.head.pos.to_tuple())
        node_to_new_pos[new_node1] = midpoint1#QPointF(*)
        node_to_new_pos[new_node2] = midpoint2#QPointF(*)

        print('')
        print('    mapping:')
        for k, v in node_to_new_node.items():
            print('   ', k, '->', v)

    # Create add / remove tweaks.
    add_tweak = Tweak()
    rem_tweak = Tweak()
    for node, new_node in node_to_new_node.items():

        # Nodes.
        rem_tweak.nodes.add(node.data)
        add_tweak.nodes.add(new_node)
        rem_tweak.node_attrs[node.data]['x'] = node.get_attribute('x')
        rem_tweak.node_attrs[node.data]['y'] = node.get_attribute('y')
        add_tweak.node_attrs[new_node]['x'] = node_to_new_pos[new_node][0]#.x()
        add_tweak.node_attrs[new_node]['y'] = node_to_new_pos[new_node][1]#.y()

        # Edges.
        for in_hedge in node.in_hedges:
            rem_tweak.hedges.add(in_hedge.data)
            new_in_hedge = (node_to_new_node.get(in_hedge.head, in_hedge.head.data), node_to_new_node[in_hedge.tail])
            add_tweak.hedges.add(new_in_hedge)
        for out_hedge in node.out_hedges:
            rem_tweak.hedges.add(out_hedge.data)
            new_out_hedge = (node_to_new_node[out_hedge.head], node_to_new_node.get(out_hedge.tail, out_hedge.tail.data))
            add_tweak.hedges.add(new_out_hedge)

        # Faces.
        rem_tweak.faces.update({face.data for face in node.faces})
        for face in node.faces:
            face_nodes = tuple([node_to_new_node.get(node, node.data) for node in face.nodes])
            add_tweak.faces.add(face_nodes)

    print('\nrem tweak:')
    print(rem_tweak)
    print('\nadd tweak:')
    print(add_tweak)

    content = QApplication.instance().doc.content
    action = Composite([
        Remove(rem_tweak, content),
        Add(add_tweak, content),
    ], flags=UpdateFlag.CONTENT)
    QApplication.instance().action_manager.push(action)
    QApplication.instance().doc.updated(action(), dirty=False)

    return add_tweak, rem_tweak


def set_attribute(obj: object, name: str, value: object):
    action = SetElementAttribute(name, value, obj)
    QApplication.instance().action_manager.push(action)
    QApplication.instance().doc.updated(action())
