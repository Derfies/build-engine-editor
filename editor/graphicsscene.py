import logging
import math
from collections import defaultdict

from PySide6.QtCore import QCoreApplication, QRectF
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtWidgets import QApplication, QGraphicsScene

from applicationframework.document import Document
from editor.constants import ModalTool, SelectionMode
from editor.graphicsitems import EdgeGraphicsItem, NodeGraphicsItem, FaceGraphicsItem
from editor.graphicsscenetools import (
    CreatePolygonTool,
    CreateFreeformPolygonTool,
    MoveGraphicsSceneTool,
    SelectGraphicsSceneTool,
)
from editor.updateflag import UpdateFlag

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


logger = logging.getLogger(__name__)


class Grid:

    def __init__(
        self,
        minor_spacing: int,
        major_spacing: int,
        minor_colour: QColor | None = None,
        major_colour: QColor | None = None,
        axes_colour: QColor | None = None,
        zoom_threshold: float = 0.02,
    ):
        self.minor_spacing = minor_spacing
        self.major_spacing = major_spacing
        minor_colour = minor_colour or QColor(50, 50, 50)
        major_colour = major_colour or QColor(100, 100, 100)
        axes_colour = axes_colour or QColor(255, 255, 255)
        self.minor_pen = QPen(minor_colour, 1)
        self.minor_pen.set_cosmetic(True)
        self.major_pen = QPen(major_colour, 1)
        self.major_pen.set_cosmetic(True)
        self.axes_pen = QPen(axes_colour, 1)
        self.axes_pen.set_cosmetic(True)
        self.zoom_threshold = zoom_threshold

    def draw(self, painter: QPainter, rect: QRectF):

        # Skip drawing when zoomed too far out.
        scale = painter.transform().m11()
        if scale < self.zoom_threshold:
            return

        left = math.floor(rect.left() / self.minor_spacing) * self.minor_spacing
        top = math.floor(rect.top() / self.minor_spacing) * self.minor_spacing

        # Draw vertical lines.
        x = left
        while x < rect.right():
            if int(x) == 0:
                painter.set_pen(self.axes_pen)
            elif int(x) % self.major_spacing == 0:
                painter.set_pen(self.major_pen)
            else:
                painter.set_pen(self.minor_pen)
            painter.draw_line(x, rect.top(), x, rect.bottom())
            x += self.minor_spacing

        # Draw horizontal lines.
        y = top
        while y < rect.bottom():
            if int(y) == 0:
                painter.set_pen(self.axes_pen)
            elif int(y) % self.major_spacing == 0:
                painter.set_pen(self.major_pen)
            else:
                painter.set_pen(self.minor_pen)
            painter.draw_line(rect.left(), y, rect.right(), y)
            y += self.minor_spacing


class GraphicsScene(QGraphicsScene):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.grid = None
        self._node_to_items = defaultdict(set)
        self._node_to_node_item = {}
        self._item_to_nodes = {}

        self.current_tool = None
        self.app().updated.connect(self.update_event)

    def update_grid(self):
        self.grid = Grid(
            self.app().grid_settings.minor_spacing,
            self.app().grid_settings.major_spacing,
            self.app().grid_settings.minor_colour,
            self.app().grid_settings.major_colour,
            self.app().grid_settings.axes_colour,
            self.app().grid_settings.zoom_threshold,
        )

    def draw_background(self, painter: QPainter, rect: QRectF):
        if not self.app().grid_settings.visible:
            return
        self.grid.draw(painter, rect)

    def app(self) -> QCoreApplication:
        return QApplication.instance()

    def set_modal_tool(self, modal_tool: ModalTool):
        tool_cls = {
            ModalTool.SELECT: SelectGraphicsSceneTool,
            ModalTool.MOVE: MoveGraphicsSceneTool,
            ModalTool.CREATE_POLY: CreatePolygonTool,
            ModalTool.CREATE_FREEFORM_POLY: CreateFreeformPolygonTool,
        }[modal_tool]
        self.current_tool = tool_cls(self)

    def set_selection_mode(self, select_mode: SelectionMode):
        self.selection_mode = select_mode

    def mouse_press_event(self, event):
        super().mouse_press_event(event)

        self.current_tool.mouse_press_event(event)

    def mouse_double_click_event(self, event):
        self.mouse_press_event(event)

    def mouse_move_event(self, event):
        super().mouse_move_event(event)

        self.current_tool.mouse_move_event(event)

    def mouse_release_event(self, event):
        super().mouse_release_event(event)

        self.current_tool.mouse_release_event(event)

    def update_event(self, doc: Document, flags: UpdateFlag):
        logger.debug(f'update_event: {flags}')
        self.block_signals(True)
        if flags != UpdateFlag.SELECTION and flags != UpdateFlag.SETTINGS:

            self.clear()

            self._item_to_nodes.clear()
            self._node_to_items.clear()
            self._node_to_node_item.clear()

            #if doc.content.g is not None:
            logger.debug(f'full reDRAW: {flags}')
            for node in doc.content.nodes:
                logger.debug(f'Adding node: {node}')
                node_item = NodeGraphicsItem(node)
                self.add_item(node_item)
                self._node_to_node_item[node] = node_item
            for edge in doc.content.edges:
                logger.debug(f'Adding edge: {edge}')
                edge_item = EdgeGraphicsItem(edge)
                self.add_item(edge_item)
            for face in doc.content.faces:
                logger.debug(f'Adding face: {face}')
                face_item = FaceGraphicsItem(face)
                self.add_item(face_item)

            # Build node -> item map.
            # TODO: Put in scene object and update only on doc update.
            # self._node_to_items.clear()
            # self._node_to_node_item.clear()
            for item in self.items():
                item_nodes = item.element().nodes
                self._item_to_nodes[item] = set(item_nodes)
                for node in item_nodes:
                    self._node_to_items[node].add(item)

                #if isinstance(item, NodeGraphicsItem):
                   # self._node_to_node_item[node] = item
        else:

            # Update selected pen.
            for item in self.items():
                item.update_pen()

        # TODO: Think this logic through again
        if UpdateFlag.SETTINGS in flags:
            self.update_grid()

        self.block_signals(False)
