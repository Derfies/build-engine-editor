import logging
import time
from typing import Any

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication, QWidget

from applicationframework.document import Document
from applicationframework.mixins import HasAppMixin
from editor.texture import Texture
from editor.texturepicker import TextureComboBox
from editor.updateflag import UpdateFlag
from propertygrid.constants import Undefined
from propertygrid.model import Model
from propertygrid.properties import PropertyBase
from propertygrid.widget import Widget as PropertyGridBase

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


logger = logging.getLogger(__name__)


class UndefinedTexture(Undefined): pass


class TextureProperty(PropertyBase, HasAppMixin):

    modal_editor = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._editor = None

    def create_editor(self, parent) -> QWidget | None:

        # This is no longer called on every paint call, but some caching is still
        # required as this gets called quite frequently and creating a combo box
        # with 100s of textures is really expensive!
        if self._editor is None:
            self._editor = TextureComboBox(self.app().adaptor_manager.current_adaptor.icons, parent)
        return self._editor

    def get_editor_data(self, editor: TextureComboBox):
        return Texture(editor.get_current_icon())

    def set_editor_data(self, editor: TextureComboBox):
        if not isinstance(self.value(), UndefinedTexture):
            editor.set_current_icon(self.value().value)
        else:
            editor.set_current_index(-1)

    def changed(self, editor: TextureComboBox):
        return editor.currentIndexChanged


class CustomModel(Model):

    """
    TODO: Still don't like these overrides. Can we make something pluggable?

    """

    def get_undefined_value(self, value):
        uvalue = super().get_undefined_value(value)
        if isinstance(value, Texture):
            uvalue = UndefinedTexture()
        return uvalue

    def get_property_class(self, value: Any):
        property_cls = super().get_property_class(value)
        if isinstance(value, Texture) or isinstance(value, UndefinedTexture):
            property_cls = TextureProperty
        return property_cls


class PropertyGrid(PropertyGridBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.header().hide()
        self.set_root_is_decorated(False)

        self.app().updated.connect(self.update_event)

    def app(self) -> QCoreApplication:
        return QApplication.instance()

    def get_model_class(self):
        return CustomModel

    def update_event(self, doc: Document, flags: UpdateFlag):
        logger.info('Rebuilding property grid...')
        start = time.time()
        self.block_signals(True)
        self.model().clear()

        # TODO: Multi-select
        # TODO: How do we display both sets of hedge data for each edge?
        if doc.selected_elements:
            properties = [e.get_attributes() for e in doc.selected_elements]
            self.set_concurrent_dicts(properties, owner=doc.selected_elements)
        self.block_signals(False)
        logger.info(f'Rebuilt property grid in {time.time() - start}s')