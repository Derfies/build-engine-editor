from dataclasses import dataclass, field

from PySide6.QtGui import QColor
from marshmallow import fields
from marshmallow_dataclass import NewType


class QColorField(fields.Field):

    def _serialize(self, value: QColor, attr, obj, **kwargs):
        return value.name()

    def _deserialize(self, value, attr, data, **kwargs):
        return QColor(value)


QColourType = NewType('QColour', QColor, QColorField)


@dataclass
class GridSettings:

    visible: bool = True
    snap: bool = False
    zoom_threshold: float = 0.02
    minor_spacing: int = 64
    minor_colour: QColourType = field(default_factory=lambda: QColor(50, 50, 50))
    major_spacing: int = 512
    major_colour: QColourType = field(default_factory=lambda: QColor(100, 100, 100))


@dataclass
class HotkeySettings:

    select: str = 'Q'
    move: str = 'W'
    rotate: str = 'E'
    scale: str = 'R'
    frame_selection: str = 'F'
