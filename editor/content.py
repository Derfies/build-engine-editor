import logging

from applicationframework.contentbase import ContentBase
from editor.graph import MapGraph
from gameengines.build.duke3d import MapReader as Duke3dMapReader


logger = logging.getLogger(__name__)


class Content(ContentBase):

    # TODO: Combine the map class with this.

    def __init__(self):
        self.g = None


    def load(self, file_path: str):
        with open(file_path, 'rb') as f:
            m = Duke3dMapReader()(f)

        self.g = MapGraph(m)

        """
        In this example, i would expect 6 nodes and 7 edges.
        nodes (walls) 1 and 4(?) are the same.
        nodes (walls) 2 and 7(?) are the same.
        
        To get from 1 to 4, I take the nextwall's point2.
        This makes sense because the next wall is the tail of this head for the 
        opposing sector, so that tail would be the equivalent of this point.
        
        To get from 7 to 2, I take the nextwall's point2.
        
        walls 1 and 7 are the same...
        
        """

        # TODO: Can add_wall and add_wall_edge be collapsed into a single fn?
        for i, wall in enumerate(m.walls):
           self.g.add_wall_node(i)
        for i, wall in enumerate(m.walls):
            self.g.add_wall_edge(i)
        for i, sector in enumerate(m.sectors):
            self.g.add_sector(i)

    def save(self, file_path: str):
        raise NotImplementedError()


if __name__ == '__main__':
    c = Content()
    c.load(r'C:\Program Files (x86)\Steam\steamapps\common\Duke Nukem 3D\gameroot\maps\1.MAP')
