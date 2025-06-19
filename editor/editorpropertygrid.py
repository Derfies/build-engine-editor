import logging

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from applicationframework.document import Document
from editor.graph import Edge, Node, Face
from editor.updateflag import UpdateFlag
from propertygrid.widget import Widget as PropertyGridBase

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


logger = logging.getLogger(__name__)


class PropertyGrid(PropertyGridBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.header().hide()
        self.set_root_is_decorated(False)

        self.app().updated.connect(self.update_event)

    def app(self) -> QCoreApplication:
        return QApplication.instance()

    def update_event(self, doc: Document, flags: UpdateFlag):
        logger.debug(f'Updating property grid: {flags}')
        self.block_signals(True)
        self.model().clear()

        # TODO: Multi-select
        if doc.selected_elements:
            element = list(doc.selected_elements)[0]

            # TODO: Instead of using different key names, just lump it under one key?
            data = None
            if isinstance(element, Node):
                data = element.get_attribute('wall')
            elif isinstance(element, Edge):
                data = element.get_attribute('wall')
            elif isinstance(element, Face):
                data = element.get_attribute('sector')
            if data is not None:
                self.add_object(data)
        self.block_signals(False)
