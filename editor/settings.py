from dataclasses import dataclass, field
from decimal import Decimal

from PySide6.QtGui import QColor
from marshmallow import fields
from marshmallow_dataclass import NewType


QColourType = NewType('QColour', QColor, fields.Field)


@dataclass
class GeneralSettings:

    snap_tolerance: int = 16
    rubberband_drag_tolerance: int = 4
    node_selectable_thickness: int = 6
    edge_selectable_thickness: int = 10


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
    zoom_threshold: Decimal = 0.02
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
    join_edges: str = 'J'
    split_edges: str = 'K'
    frame_selection: str = 'F'
    remove: str = 'Backspace'
    grid_snap: str = 'X'
    vertex_snap: str = 'V'
