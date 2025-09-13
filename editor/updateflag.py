from enum import Flag, auto


class UpdateFlag(Flag):

    CONTENT = auto()
    SELECTION = auto()
    SETTINGS = auto()
    ADAPTOR_TEXTURES = auto()
