from PySide6.QtWidgets import QApplication

from applicationframework.actions import Composite, SetAttribute
from editor.actions import GraphEditBase
from editor.graph import Edge, Node
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
        actions.append(SetAttribute('x', node_item.pos().x(), node_item.element()))
        actions.append(SetAttribute('y', node_item.pos().y(), node_item.element()))
    action = Composite(actions, flags=UpdateFlag.GRAPH)
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
    # nodes = {node for node in face.nodes if node not in graph.nodes}
    # edges = {edge for edge in face.edges if edge not in graph.edges}
    # faces = face if face not in graph.faces else set()

    # TODO: Factory for default data? How else does the next sector get in here?
    action = GraphEditBase(
        nodes,
        tuple(edges),
        (tuple(face),),
        graph,
        **kwargs
        #node_attrs={'sector': Sector()},
        #edge_attrs={edge: Wall() for edge in edges},
        #face_attrs={'sector': Sector()},
    )

    #print('nodes:', nodes)
    #print('edges:', edges)
    #print('faces:', face)
    #print('faces:', faces)
    #action = AddFace(face)
    QApplication.instance().action_manager.push(action)
    QApplication.instance().doc.updated(action(), dirty=True)
