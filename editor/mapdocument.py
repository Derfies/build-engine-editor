from applicationframework.document import Document


class MapDocument(Document):

    @property
    def selected_elements(self) -> dict[int, dict]:
        return {
            edge
            for edge in self.content.g.nodes | self.content.g.edges | set(self.content.g.polys)
            if edge.is_selected
        }
