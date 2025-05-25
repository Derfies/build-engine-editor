from applicationframework.document import Document


class MapDocument(Document):

    @property
    def selected_elements(self) -> dict[int, dict]:
        return {
            edge
            for edge in self.content.g.nodes | self.content.g.edges
            if edge.is_selected
        }
