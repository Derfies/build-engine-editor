import logging

from PySide6.QtCore import QCoreApplication, QPointF
from PySide6.QtWidgets import QApplication, QGraphicsScene

from applicationframework.document import Document
from editor.constants import ModalTool
from editor.graphicsitems import NodeGraphicsItem, SectorGraphicsItem, WallGraphicsItem
from editor.graphicsscenetools import SelectGraphicsSceneTool, DrawSectorGraphicsSceneTool
from updateflag import UpdateFlag

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


logger = logging.getLogger(__name__)


class GraphicsScene(QGraphicsScene):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.current_tool = None
        self.app().updated.connect(self.update_event)

    def app(self) -> QCoreApplication:
        return QApplication.instance()

    def set_modal_tool(self, modal_tool: ModalTool):
        tool_cls = {
            ModalTool.SELECT: SelectGraphicsSceneTool,
            ModalTool.DRAW_SECTOR: DrawSectorGraphicsSceneTool,
        }[modal_tool]
        self.current_tool = tool_cls(self)

    def mouse_press_event(self, event):
        super().mouse_press_event(event)

        self.current_tool.mouse_press_event(event)

    def mouse_move_event(self, event):
        super().mouse_move_event(event)

        self.current_tool.mouse_move_event(event)

    def mouse_release_event(self, event):
        super().mouse_release_event(event)

        self.current_tool.mouse_release_event(event)

    def update_event(self, doc: Document, flags: UpdateFlag):
        self.block_signals(True)
        if flags != UpdateFlag.SELECTION:

            logger.debug(f'Updating graphics scene: {flags}')

            self.clear()
            if doc.content.map is not None:

                edges = {}
                for wall_idx in range(len(doc.content.map.walls)):
                    head = doc.content.map.walls[wall_idx]
                    if head.nextwall > -1 and head.nextwall in edges:
                        #print('next wall found')
                        continue
                    tail = doc.content.map.walls[head.point2]
                    p1 = QPointF(head.x, head.y)
                    p2 = QPointF(tail.x, tail.y)
                    edge = WallGraphicsItem(doc.content.walls[wall_idx], p1, p2)
                    edge.setZValue(100)
                    self.add_item(edge)
                    edges[wall_idx] = edge

            for sector in doc.content.sectors:
                self.add_item(SectorGraphicsItem(sector))

            for node in doc.content.g.nodes:
                node_item = NodeGraphicsItem(node)
                node_item.set_pos(QPointF(doc.content.g.nodes[node]['x'], doc.content.g.nodes[node]['y']))
                self.add_item(node_item)

        else:
            for item in self.items():
                wall = getattr(item, 'wall', None)
                if wall is not None:
                    item.update_pen()

        self.block_signals(False)
