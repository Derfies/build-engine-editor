from __future__ import annotations

from enum import Enum, IntEnum, auto


class ModalTool(IntEnum):

    SELECT = auto()
    MOVE = auto()
    ROTATE = auto()
    SCALE = auto()
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

    DUKE_3D = 'Duke Nukem 3D (*.map)'
    BLOOD = 'Blood (*.map)'


FACES = 'faces'
SETTINGS = 'settings'
DEFAULT_NODE_ATTRIBUTES = 'default_node_attributes'
DEFAULT_HEDGE_ATTRIBUTES = 'default_hedge_attributes'
DEFAULT_FACE_ATTRIBUTES = 'default_face_attributes'
