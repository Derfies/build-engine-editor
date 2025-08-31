from __future__ import annotations

from enum import Enum, IntEnum, auto


class ModalTool(IntEnum):

    SELECT = auto()
    MOVE = auto()
    ROTATE = auto()
    SCALE = auto()
    CREATE_NODE = auto()
    CREATE_POLYGON = auto()
    CREATE_FREEFORM_POLYGON = auto()
    SPLIT_FACES = auto()
    SLICE_FACES = auto()


class SelectionMode(IntEnum):

    ALL = auto()
    NODE = auto()
    EDGE = auto()
    FACE = auto()


class MapFormat(Enum):

    # TODO: Do all build versions get lumped here with other non-game types?

    DUKE_3D = 'Duke Nukem 3D (*.map)'
    BLOOD = 'Blood (*.map)'
    GEXF = 'Graph Exchange XML (*.gexf)'
    DOOM = 'Doom WAD (*.map)'


ATTRIBUTES = 'attributes'
NODE_DEFAULT = 'node_default'
EDGE_DEFAULT = 'edge_default'
FACE_DEFAULT = 'face_default'
FACES = 'faces'
FACE = 'face'
IS_SELECTED = 'is_selected'