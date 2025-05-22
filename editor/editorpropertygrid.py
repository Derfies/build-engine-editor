import logging

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from applicationframework.document import Document
from propertygrid.widget import Widget as PropertyGridBase
from updateflag import UpdateFlag

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
        if doc.selected_edges:
            self.add_object(doc.selected_edges[0])
            self.add_object(doc.selected_edges[0].raw)
        self.block_signals(False)
