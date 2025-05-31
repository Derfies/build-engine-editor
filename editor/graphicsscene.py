import logging
from collections import defaultdict

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication, QGraphicsScene

from applicationframework.document import Document
from editor.constants import ModalTool, SelectionMode
from editor.graphicsitems import EdgeGraphicsItem, NodeGraphicsItem, PolyGraphicsItem
from editor.graphicsscenetools import DrawSectorGraphicsSceneTool, MoveGraphicsSceneTool, SelectGraphicsSceneTool
from editor.updateflag import UpdateFlag

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


logger = logging.getLogger(__name__)


class GraphicsScene(QGraphicsScene):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._node_to_items = defaultdict(set)
        self._item_to_nodes = {}

        self.current_tool = None
        self.app().updated.connect(self.update_event)

        self.grid_spacing = 20
        self.major_every = 5
        #self.set_background_brush(Qt.white)
        #self.draw_grid()


    # def draw_grid(self):
    #     minor_pen = QPen(QColor(200, 200, 200), 0)  # Light gray, thin line
    #     major_pen = QPen(QColor(100, 100, 100), 0)  # Dark gray, thin line
    #
    #     left = int(self.scene_rect().left())
    #     right = int(self.scene_rect().right())
    #     top = int(self.scene_rect().top())
    #     bottom = int(self.scene_rect().bottom())
    #
    #     for x in range(left, right + 1, self.grid_spacing):
    #         if (x - left) // self.grid_spacing % self.major_every == 0:
    #             self.add_line(x, top, x, bottom, major_pen)
    #         else:
    #             self.add_line(x, top, x, bottom, minor_pen)
    #
    #     for y in range(top, bottom + 1, self.grid_spacing):
    #         if (y - top) // self.grid_spacing % self.major_every == 0:
    #             self.add_line(left, y, right, y, major_pen)
    #         else:
    #             self.add_line(left, y, right, y, minor_pen)

    def app(self) -> QCoreApplication:
        return QApplication.instance()

    def set_modal_tool(self, modal_tool: ModalTool):
        tool_cls = {
            ModalTool.SELECT: SelectGraphicsSceneTool,
            ModalTool.MOVE: MoveGraphicsSceneTool,
            ModalTool.DRAW_POLY: DrawSectorGraphicsSceneTool,
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
        if flags != UpdateFlag.SELECTION:

            self.clear()
            if doc.content.g is not None:
                logger.debug(f'full reDRAW: {flags}')
                for node in doc.content.g.nodes:
                    node_item = NodeGraphicsItem(node)
                    self.add_item(node_item)
                for edge in doc.content.g.edges:
                    edge_item = EdgeGraphicsItem(edge)
                    self.add_item(edge_item)
                for poly in doc.content.g.polys:
                    poly_item = PolyGraphicsItem(poly)
                    self.add_item(poly_item)

                # Build node -> item map.
                # TODO: Put in scene object and update only on doc update.
                for item in self.items():
                    item_nodes = item.element().nodes
                    self._item_to_nodes[item] = item_nodes
                    for node in item_nodes:
                        self._node_to_items[node].add(item)
        else:

            # Update selected pen.
            for item in self.items():
                item.update_pen()

        self.block_signals(False)
