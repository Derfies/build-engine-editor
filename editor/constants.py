from enum import IntEnum, auto


class ModalTool(IntEnum):

    SELECT = auto()
    MOVE = auto()
    ROTATE = auto()
    SCALE = auto()
    CREATE_POLY = auto()
    CREATE_FREEFORM_POLY = auto()
    SPLIT_FACE = auto()


class SelectionMode(IntEnum):

    NODE = auto()
    EDGE = auto()
    POLY = auto()
