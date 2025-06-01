from enum import IntEnum


class ModalTool(IntEnum):

    SELECT = 0
    MOVE = 1
    ROTATE = 2
    SCALE = 3
    CREATE_POLY = 4
    CREATE_FREEFORM_POLY = 5


class SelectionMode(IntEnum):

    NODE = 0
    EDGE = 1
    POLY = 2
