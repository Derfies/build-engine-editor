from applicationframework.document import Document


class MapDocument(Document):

    @property
    def selected_elements(self) -> dict[int, dict]:
        return {
            edge
            for edge in self.content.nodes | self.content.edges | set(self.content.faces)
            if edge.is_selected
        }
