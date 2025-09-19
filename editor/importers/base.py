import logging
from abc import abstractmethod, ABCMeta

from PySide6.QtWidgets import QDialog

from editor.graph import Graph

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


logger = logging.getLogger(__name__)


class ImporterDialogBase(QDialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_window_title('Import Options')

    def get_options(self):
        raise NotImplementedError


class ImporterBase(metaclass=ABCMeta):

    """
    Yes yes yes, I know - it's a class with a single method named 'run'. Sue me.

    But we still need to establish a contract that exposes the format as well as
    the method, and subclassing from this class gives the manager something to
    scan for.

    """

    required_attrs = ('format', )

    def __init__(self, file_path: str):
        self.file_path = file_path

    # TODO: Turn this into a nice decorator.
    def __init_subclass__(cls, *args, **kwargs):
        super().__init_subclass__(*args, **kwargs)
        missing_attrs = [
            attr
            for attr in cls.required_attrs
            if not hasattr(cls, attr)
        ]
        if missing_attrs:
            raise TypeError(f"Can't instantiate abstract type {cls.__name__} with abstract method {', '.join(missing_attrs)}")

    @abstractmethod
    def create_dialog(self):
        ...

    @abstractmethod
    def run(self, graph: Graph, **kwargs):
        ...
