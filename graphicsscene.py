import logging

from PySide6.QtCore import QCoreApplication, QModelIndex, QPointF, Qt
from PySide6.QtGui import QColor, QColorConstants, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QApplication, QGraphicsItem, QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsScene, QGraphicsView, QPushButton, QSplitter, QVBoxLayout, QWidget

from applicationframework.document import Document
from updateflag import UpdateFlag

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


logger = logging.getLogger(__name__)


NODE_RADIUS = 2


class Node(QGraphicsEllipseItem):

    def __init__(self, path, index):
        super(Node, self).__init__(-NODE_RADIUS, -NODE_RADIUS, 2 * NODE_RADIUS, 2 * NODE_RADIUS)

        self.rad = NODE_RADIUS
        self.path = path
        self.index = index

        self.setZValue(1)
        self.set_flag(QGraphicsItem.ItemIsMovable)
        self.set_flag(QGraphicsItem.ItemSendsGeometryChanges)
        self.set_brush(Qt.green)

    def item_change(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            self.path.update_element(self.index, value.to_point())
        return QGraphicsEllipseItem.item_change(self, change, value)


class Path(QGraphicsPathItem):

    def __init__(self, path, scene):
        super(Path, self).__init__(path)

        self.path = path
        for i in range(path.element_count() - 1):
            node = Node(self, i)
            node.set_pos(QPointF(path.element_at(i)))
            scene.add_item(node)
        self.set_pen(QPen(Qt.red, 1.75))

    def update_element(self, index, pos):
        self.path.set_element_position_at(index, pos.x(), pos.y())
        if index == 0 or index == self.path.element_count() - 1:
            self.path.set_element_position_at(0,  pos.x(), pos.y())
            self.path.set_element_position_at(self.path.element_count() - 1, pos.x(), pos.y())
        self.set_path(self.path)


class GraphicsScene(QGraphicsScene):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.app().updated.connect(self.update_event)

    def app(self) -> QCoreApplication:
        return QApplication.instance()

    def update_event(self, doc: Document, flags: UpdateFlag):
        logger.debug(f'Updating graphics scene: {flags}')

        self.clear()
        if doc.content.map is None:
            return
        self.block_signals(True)

        for sector in doc.content.map.sectors:

            # print('')
            # print(sector)

            cells = []
            cell = []
            cell_wallptr = sector.wallptr
            next_point_idx = sector.wallptr
            for i in range(sector.wallnum):

                wall = doc.content.map.walls[next_point_idx]
                # print('    wall:', wall)
                cell.append((wall.x / 100, wall.y / 100))
                next_point_idx = wall.point2

                # HAX
                if next_point_idx < 0:
                    break

                # If the next point returns to the start and we haven't reached the
                # end of the sector's walls then the sector has a hole which we
                # currently can't support.
                # print('next_point_idx:', next_point_idx, 'cell_wallptr:', cell_wallptr)
                if next_point_idx == cell_wallptr:
                    next_point_idx = sector.wallptr + i + 1
                    cell_wallptr = next_point_idx
                    cells.append(cell)
                    cell = []

            for cell in cells:
                # print('cell:', cell)

                # Add a shape.
                path = QPainterPath()
                points = [QPointF(p[0], p[1]) for p in cell]
                points.append(QPointF(cell[0][0], cell[0][1]))
                poly = QPolygonF(points)
                path.add_polygon(poly)

                self.add_item(Path(path, self))

        self.block_signals(False)
