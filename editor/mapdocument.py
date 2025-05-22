from applicationframework.document import Document


class MapDocument(Document):

    @property
    def selected_edges(self):
        selected_edges = []
        for wall_idx, wall in enumerate(self.content.walls):
            if wall.is_selected:
                selected_edges.append(wall)
        return selected_edges
