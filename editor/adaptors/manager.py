import importlib
import inspect
import logging
import pkgutil
from dataclasses import dataclass
from types import ModuleType

from applicationframework.document import Document
from applicationframework.mixins import HasAppMixin
from editor import adaptors
from editor.adaptors.base import AdaptorBase
from editor.updateflag import UpdateFlag


logger = logging.getLogger(__name__)


@dataclass
class AdaptorSettings:

    current_adaptor: str | None = None


class AdaptorManager(HasAppMixin):

    def __init__(self):
        self._settings = AdaptorSettings()
        self.adaptors = {}
        for cls in self._find_adaptor_classes(adaptors):
            adaptor = cls()
            self.adaptors[adaptor.name] = adaptor
        self.app().updated.connect(self.update_event)

    @property
    def settings(self):
        return self._settings

    @property
    def current_adaptor(self):
        return self.adaptors.get(self.settings.current_adaptor)

    @staticmethod
    def _find_adaptor_classes(package: ModuleType):
        adaptors = []
        for finder, name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + '.'):
            module = importlib.import_module(name)
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, AdaptorBase) and obj is not AdaptorBase:
                    adaptors.append(obj)
                    logger.info(f'Found adaptor class: {obj}')
        return tuple(adaptors)

    def update_event(self, doc: Document, flags: UpdateFlag):
        if UpdateFlag.ADAPTOR_TEXTURES in flags and self.current_adaptor is not None:
            self.current_adaptor.build_resources()
