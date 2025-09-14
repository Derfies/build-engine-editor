import copy
import logging
import uuid
from typing import Iterable

from PySide6.QtWidgets import QApplication

from applicationframework.actions import Composite
from editor.actions import Add, Tweak
from editor.graph import Edge, Face, Node
from editor.updateflag import UpdateFlag


logger = logging.getLogger(__name__)


class Clipboard:

    """
    NOTE: We're starting to need to define what standard behaviour is when dealing
    with elements. For instance when drawing maps it may be less intuitive to
    delete a polygon face and have its edges not be deleted with it. However this
    might be desirable when drawing abstract graphs or some other data types.

    That being said, at the moment we're assuming the least and doing the bare
    minimum to keep in line with the users expectations. Eg copying a face should
    include edges and nodes, likewise edges should include nodes.

    TODO: Are these commands? Would a user want to script this behaviour? I suppose
    we can just move the copy() and paste() method calls into the commands module.

    """

    def __init__(self):
        self._tweak = None

    def is_empty(self):
        return self._tweak is None

    def copy(self, elements: Iterable[Node | Edge | Face]):

        # Bucket elements by type.
        nodes = {n for n in elements if isinstance(n, Node)}
        edges = {e for e in elements if isinstance(e, Edge)}
        faces = {f for f in elements if isinstance(f, Face)}

        # Any edge being copied requires its nodes.
        for edge in edges:
            nodes.update(edge.nodes)

        # Any face being copied requires its nodes and edges.
        for face in faces:
            nodes.update(face.nodes)
            edges.update(face.edges)

        # Build the tweak.
        tweak = Tweak()
        tweak.nodes.update([n.data for n in nodes])
        tweak.edges.update([e.data for e in edges])
        tweak.faces.update([f.data for f in faces])
        tweak.node_attrs.update({n.data: copy.deepcopy(n.get_attributes()) for n in nodes})
        tweak.edge_attrs.update({e.data: copy.deepcopy(e.get_attributes()) for e in edges})
        tweak.face_attrs.update({f.data: copy.deepcopy(f.get_attributes()) for f in faces})
        self._tweak = tweak

    def paste(self):

        lookup = {node: str(uuid.uuid4()) for node in self._tweak.nodes}

        # Build the tweak.
        tweak = Tweak()
        tweak.nodes.update([lookup[n] for n in self._tweak.nodes])
        tweak.edges.update([(lookup[e[0]], lookup[e[1]]) for e in self._tweak.edges])
        tweak.faces.update([tuple([lookup[n] for n in f]) for f in self._tweak.faces])
        tweak.node_attrs.update({lookup[n]: copy.deepcopy(attrs) for n, attrs in self._tweak.node_attrs.items()})
        tweak.edge_attrs.update({(lookup[e[0]], lookup[e[1]]): copy.deepcopy(attrs) for e, attrs in self._tweak.edge_attrs.items()})
        tweak.face_attrs.update({tuple([lookup[n] for n in f]): copy.deepcopy(attrs) for f, attrs in self._tweak.face_attrs.items()})

        # Now offset the node positions so the paste is more apparent.
        # TODO: Would be nice to offset this by the camera zoom.
        for node_attr in tweak.node_attrs.values():
            node_attr['x'] = node_attr['x'] + 100
            node_attr['y'] = node_attr['y'] + 100

        # TODO: Select component after pasting it. Which isn't easy to do since
        # the elements don't exist yet!
        action = Composite([
            Add(tweak, QApplication.instance().doc.content),
        ], flags=UpdateFlag.CONTENT)
        QApplication.instance().action_manager.push(action)
        QApplication.instance().doc.updated(action(), dirty=True)
