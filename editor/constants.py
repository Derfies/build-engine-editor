from enum import IntEnum, auto


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
