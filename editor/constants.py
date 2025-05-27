from enum import IntEnum


class ModalTool(IntEnum):

    SELECT = 0
    MOVE = 1
    ROTATE = 2
    SCALE = 3
    DRAW_POLY = 4


class SelectionMode(IntEnum):

    NODE = 0
    EDGE = 1
    POLY = 2
