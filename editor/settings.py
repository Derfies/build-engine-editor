from dataclasses import dataclass, field

from PySide6.QtGui import QColor
from marshmallow import fields
from marshmallow_dataclass import NewType


class QColorField(fields.Field):

    def _serialize(self, value: QColor, attr, obj, **kwargs):
        return value.red(), value.green(), value.blue(), value.alpha()

    def _deserialize(self, value, attr, data, **kwargs):
        return QColor(*value)


QColourType = NewType('QColour', QColor, QColorField)


@dataclass
class ColourSettings:

    node: QColourType = field(default_factory=lambda: QColor(127, 127, 127, 255))
    selected_node: QColourType = field(default_factory=lambda: QColor(255, 255, 127, 255))
    edge: QColourType = field(default_factory=lambda: QColor(127, 127, 127, 255))
    selected_edge: QColourType = field(default_factory=lambda: QColor(255, 255, 127, 255))
    poly: QColourType = field(default_factory=lambda: QColor(0, 0, 127, 127))
    selected_poly: QColourType = field(default_factory=lambda: QColor(255, 255, 127, 127))


@dataclass
class GridSettings:

    visible: bool = True
    snap: bool = False
    zoom_threshold: float = 0.02
    minor_spacing: int = 64
    minor_colour: QColourType = field(default_factory=lambda: QColor(50, 50, 50))
    major_spacing: int = 512
    major_colour: QColourType = field(default_factory=lambda: QColor(100, 100, 100))
    axes_colour: QColourType = field(default_factory=lambda: QColor(150, 150, 150))


@dataclass
class HotkeySettings:

    select: str = 'Q'
    move: str = 'W'
    rotate: str = 'E'
    scale: str = 'R'
    frame_selection: str = 'F'
    grid_snap: str = 'X'
    vertex_snap: str = 'V'


@dataclass
class PlaySettings:

    eduke32_path: str = ''
