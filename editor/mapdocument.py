from applicationframework.document import Document

from editor.graph import Element


class MapDocument(Document):

    @property
    def selected_nodes(self) -> set[Element]:
        return set([node for node in self.content.nodes if node.is_selected])

    @property
    def selected_edges(self) -> set[Element]:
        return set([edge for edge in self.content.edges if edge.is_selected])

    @property
    def selected_hedges(self) -> set[Element]:
        return set([hedge for hedge in self.content.hedges if hedge.is_selected])

    @property
    def selected_faces(self) -> set[Element]:
        return set([hedge for hedge in self.content.faces if hedge.is_selected])

    @property
    def selected_elements(self) -> set[Element]:
        return {
            element
            for element in self.content.nodes | self.content.edges | self.content.hedges | self.content.faces
            if element.is_selected
        }
