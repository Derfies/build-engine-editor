import uuid
from collections import defaultdict

from PySide6.QtWidgets import QApplication

from applicationframework.actions import Composite, SetAttribute
from editor.actions import Add, Remove#, GraphEditBase
from editor.graph import Edge, Hedge, Node
from editor.maths import lerp
from editor.updateflag import UpdateFlag

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


def split_face(*splits: tuple[Hedge, float]):
    print('splits:')

    content = QApplication.instance().doc.content

    # Remove those edges to be split.
    del_edges = set()
    del_faces = set()

    for split in splits:
        print('->', split[0])
        hedge, pct = split
        del_edges.add(hedge.data)
        rev_hedge = (hedge.tail.data, hedge.head.data)
        if rev_hedge in content.hedges:
            del_edges.add(rev_hedge)
            #had_reverse.add(hedge)

        if hedge.face is not None:
            del_faces.add(hedge.face.data)

    print('\ndel edges:')
    for del_edge in del_edges:
        print('->', del_edge)

    # Add new edges.
    new_nodes = []
    new_edges = []

    node_attrs = defaultdict(dict)
    for split in splits:
        hedge, pct = split
        new_node = str(uuid.uuid4())
        new_nodes.append(new_node)
        new_edges.extend(((hedge.head.data, new_node), (new_node, hedge.tail.data)))

        node_attrs[new_node]['pos'] = lerp(hedge.head.pos, hedge.tail.pos, pct)

        rev_hedge = (hedge.tail.data, hedge.head.data)
        if rev_hedge in content.hedges:
            new_edges.extend(((hedge.tail.data, new_node), (new_node, hedge.head.data)))

    print('\nnew edges:')
    for new_edge in new_edges:
        print('->', new_edge)

    # The bridge. This is two-sided by definition because we cut through a face.
    print('\nbridges:')
    bridges = []
    for i in range(len(new_nodes) - 1):
        new_edges.append((new_nodes[i], new_nodes[i + 1]))
        print('->', new_edges[-1])
        bridges.append(new_edges[-1])
        new_edges.append((new_nodes[i + 1], new_nodes[i]))
        print('->', new_edges[-1])
        bridges.append(new_edges[-1])


    action = Composite([
        Remove(content, edges=del_edges, faces=del_faces),
        Add(content, edges=new_edges, node_attrs=node_attrs),
    ], flags=UpdateFlag.CONTENT)
    QApplication.instance().action_manager.push(action)
    QApplication.instance().doc.updated(action(), dirty=False)
