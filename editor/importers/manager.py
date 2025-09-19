import importlib
import inspect
import logging
import pkgutil

from applicationframework.mixins import HasAppMixin
from editor import importers
from editor.importers.base import ImporterBase


logger = logging.getLogger(__name__)


class ImporterManager(HasAppMixin):

    def __init__(self):
        self._importers = {}
        for finder, name, is_pkg in pkgutil.walk_packages(importers.__path__, importers.__name__ + '.'):
            module = importlib.import_module(name)
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, ImporterBase) and obj is not ImporterBase:
                    self._importers[obj.format] = obj
                    logger.info(f'Found importer class: {obj}')

    @property
    def formats(self):
        return tuple(self._importers.keys())

    def get_by_format(self, fmt: str):
        return self._importers[fmt]
