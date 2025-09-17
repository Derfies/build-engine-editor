from applicationframework.document import Document as DocumentBase
from editor.graph import Element
from editor.updateflag import UpdateFlag


class Document(DocumentBase):

    @property
    def new_flags(self):
        return self.default_flags & ~UpdateFlag.ADAPTOR_TEXTURES

    @property
    def load_flags(self):
        return self.default_flags & ~UpdateFlag.ADAPTOR_TEXTURES

    @property
    def selected_nodes(self) -> set[Element]:
        return set([node for node in self.content.nodes if node.is_selected])

    @property
    def selected_edges(self) -> set[Element]:
        return set([edge for edge in self.content.edges if edge.is_selected])

    @property
    def selected_faces(self) -> set[Element]:
        return set([edge for edge in self.content.faces if edge.is_selected])

    @property
    def selected_elements(self) -> set[Element]:
        return {
            element
            for element in self.content.nodes | self.content.edges | self.content.faces
            if element.is_selected
        }
