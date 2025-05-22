import logging
from dataclasses import dataclass, field

from applicationframework.contentbase import ContentBase
from gameengines.build.duke3d import MapReader as Duke3dMapReader
from gameengines.build.map import Sector, Wall

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


logger = logging.getLogger(__name__)


@dataclass
class EditorWall:

    raw: Wall
    is_selected = False


@dataclass
class EditorSector:

    raw: Sector
    is_selected = False
    walls: list = field(default_factory=list)


class Content(ContentBase):

    def __init__(self):
        self.map = None

        self.walls = []
        self.sectors = []

    def load(self, file_path: str):
        with open(file_path, 'rb') as f:
            self.map = Duke3dMapReader()(f)

        for i, wall in enumerate(self.map.walls):
            edwall = EditorWall(wall)
            self.walls.append(edwall)

        for i, sector in enumerate(self.map.sectors):
            sector = self.map.sectors[i]
            edsector = EditorSector(sector)
            self.sectors.append(edsector)
            next_point_idx = sector.wallptr
            for _ in range(sector.wallnum):

                edwall = self.walls[next_point_idx]
                edsector.walls.append(edwall)

                next_point_idx = edwall.raw.point2

                # If the next point returns to the start and we haven't reached the
                # end of the sector's walls then the sector has a hole which we
                # currently can't support.
                if next_point_idx == sector.wallptr:
                    break

    def save(self, file_path: str):
        raise NotImplementedError()
