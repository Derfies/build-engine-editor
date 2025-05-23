import logging
from dataclasses import dataclass, field

from applicationframework.contentbase import ContentBase
from editor.graph import Graph
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

        self.g = Graph()

        """
        In this example, i would expect 6 nodes and 7 edges.
        nodes (walls) 1 and 4(?) are the same.
        nodes (walls) 2 and 7(?) are the same.
        
        To get from 1 to 4, I take the nextwall's point2.
        This makes sense because the next wall is the tail of this head for the 
        opposing sector, so that tail would be the equivalent of this point.
        
        To get from 7 to 2, I take the nextwall's point2.
        
        """

        for i, wall in enumerate(self.map.walls):
            edwall = EditorWall(wall)
            self.walls.append(edwall)

            # First attempt at finding common nodes / walls.
            node_idx = i
            attrs = {'x': wall.x, 'y': wall.y, 'walls': {i}}
            if wall.nextwall > -1:
                nextwall = self.map.walls[wall.nextwall]
                node_idx = nextwall.point2
                attrs['walls'].add(nextwall.point2)
            if node_idx in self.g.nodes:
                self.g.nodes[node_idx]['walls'].update(attrs['walls'])
            else:
                self.g.add_node(node_idx, **attrs)


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

        print(self.g)

    def save(self, file_path: str):
        raise NotImplementedError()


if __name__ == '__main__':
    c = Content()
    c.load(r'C:\Program Files (x86)\Steam\steamapps\common\Duke Nukem 3D\gameroot\maps\1.MAP')