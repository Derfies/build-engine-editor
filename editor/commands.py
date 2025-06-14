import uuid
from collections import defaultdict
from typing import Iterable

import numpy as np
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication
from shapely.geometry import LineString, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import split as split_ops

from applicationframework.actions import Composite, SetAttribute
from editor import maths
from editor.actions import Add, Remove
from editor.graph import Edge, Face, Hedge, Node
from editor.maths import lerp, long_line_through, midpoint
from editor.updateflag import UpdateFlag
from gameengines.build.map import Sector, Wall

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


TOLERANCE = 1e-6


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
    node_attrs = {}
    rem_nodes, rem_edges, rem_faces = set(), set(), set()
    for element in elements:
        if isinstance(element, Node):
            rem_nodes.add(element)
            rem_edges.update(element.hedges)
            rem_faces.update(element.faces)
            node_attrs.setdefault(element, {})['pos'] = element.pos
        if isinstance(element, Edge):
            rem_edges.update(element.hedges)
            rem_faces.update(element.faces)
        if isinstance(element, Face):
            rem_faces.add(element)

    print('rem_nodes:', rem_nodes)
    print('rem_edges:', rem_edges)
    print('rem_faces:', rem_faces)
    print('node_attrs', node_attrs)

    action = Remove(
        QApplication.instance().doc.content,
        nodes=[n.data for n in rem_nodes],
        edges=[n.data for n in rem_edges],
        faces=[n.data for n in rem_faces],
        node_attrs=node_attrs,
    )
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

    # TODO: Factory for default data? How else do walls / sectors get here
    # without knowing the build data requirements?
    node_attrs = defaultdict(dict)
    edge_attrs = defaultdict(dict)
    face_attrs = defaultdict(dict)
    nodes = [str(uuid.uuid4()) for _ in range(len(coords))]
    edges = []
    face = tuple(nodes)
    for i in range(len(nodes)):
        head = nodes[i]
        tail = nodes[(i + 1) % len(nodes)]
        edges.append((head, tail))
        node_attrs[nodes[i]]['pos'] = QPointF(*coords[i])
        edge_attrs[(head, tail)]['wall'] = Wall()
    face_attrs[face]['sector'] = Sector()

    action = Add(
        QApplication.instance().doc.content,
        nodes=nodes,
        edges=edges,
        faces=[face],
        node_attrs=node_attrs,
        edge_attrs=edge_attrs,
        face_attrs=face_attrs,
    )
    QApplication.instance().action_manager.push(action)
    QApplication.instance().doc.updated(action(), dirty=True)


def split_face(*splits: tuple[Hedge, float]):

    print('\nsplits:')
    for i, split in enumerate(splits):
        hedge, pct = split
        print(i, '->', hedge, pct)

    # Remove those edges to be split.
    del_hedges = set()
    del_faces = set()
    add_nodes = set()
    add_edges = set()
    add_faces = []
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
            del_faces.add(hedge.face.data)

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
            add_nodes.update(nodes1)
            add_nodes.update(nodes2)
            add_faces.append(tuple(face1.keys()))
            add_faces.append(tuple(face2.keys()))
            node_attrs.update(face1)
            node_attrs.update(face2)

            add_edges.update([
                (nodes1[i], nodes1[(i + 1) % len(nodes1)]) for i in range(len(nodes1))
            ])
            add_edges.update([
                (nodes2[i], nodes2[(i + 1) % len(nodes2)]) for i in
                range(len(nodes2))
            ])


        last_cut_point = cut_point

    print('\ndel hedges:')
    for hedge in del_hedges:
        print('    ->', hedge)

    print('\nadd_edges:')
    for add_edge in add_edges:
        print('    ->', add_edge)

    print('\nadd_faces:')
    for add_face in add_faces:
        print('    ->', add_face)

    # Face attrs.
    action = Composite([
        Remove(content, edges=del_hedges, faces=del_faces),
        Add(content, nodes=add_nodes, edges=add_edges, faces=add_faces, node_attrs=node_attrs),
    ], flags=UpdateFlag.CONTENT)
    QApplication.instance().action_manager.push(action)
    QApplication.instance().doc.updated(action(), dirty=False)

    #
    # print('\nnodes:')
    # for node in content.nodes:
    #     print('    ->', node)
    # print('\nedges:')
    # for edge in content.edges:
    #     print('    ->', edge)
    # print('\nhedges:')
    # for hedge in content.hedges:
    #     print('    ->', hedge, '->', hedge.face)
    # print('\nfaces:')
    # for face in content.faces:
    #     print('    ->', face)


def join_edges(*edges: Iterable[Edge] | Iterable[Hedge]):

    # TODO: Decide what func sig should look like. Does it take hedges or edges?
    # If this is meant to be a programmer's interface, it should probably not be ambiguous
    # Only joins faces to other faces. Even though the editor techincally supports
    # face-less edges, for the purposes of joining edges that feels like a restriction
    # we can make.

    all_hedges = set()
    for edge in edges:
        if isinstance(edge, Edge):
            all_hedges.update(edge.hedges)
        else:
            all_hedges.add(edge)

    hedges = set()
    for hedge in all_hedges:
        print('hedge:', hedge, '->', hedge.face)
        if hedge.face is not None:
            hedges.add(hedge)

    print('hedges:', hedges)

    unmatched = list(hedges)
    groups = []


    MAX_DISTANCE = 1000.0


    while unmatched:
        base = unmatched.pop()
        n1 = maths.edge_normal(base.head.pos.to_tuple(), base.tail.pos.to_tuple())
        base_mid = LineString((base.head.pos.to_tuple(), base.tail.pos.to_tuple())).interpolate(0.5, normalized=True)

        best_match = None
        best_dist = float("inf")

        for i, other in enumerate(unmatched):
            n2 = maths.edge_normal(other.head.pos.to_tuple(), other.tail.pos.to_tuple())
            if np.dot(n1, n2) < 0:#-1 + TOLERANCE:  # opposing normals
                other_mid = LineString((other.head.pos.to_tuple(), other.tail.pos.to_tuple())).interpolate(0.5, normalized=True)
                dist = base_mid.distance(other_mid)

                print('dist:', dist)

                if dist < best_dist and dist <= MAX_DISTANCE:
                    best_match = (i, other)
                    best_dist = dist

        if best_match:
            i, other = best_match
            groups.append((base, other))
            unmatched.pop(i)

    print('groups:', groups)

    for edge1, edge2 in groups:
        mid = midpoint(edge1.head.pos.to_tuple(), edge2.tail.pos.to_tuple())
        edge1.head.pos = QPointF(*mid)
        edge2.tail.pos = QPointF(*mid)

        mid = midpoint(edge1.tail.pos.to_tuple(), edge2.head.pos.to_tuple())
        edge1.tail.pos = QPointF(*mid)
        edge2.head.pos = QPointF(*mid)

    # Rewar


    QApplication.instance().doc.updated(dirty=True)
