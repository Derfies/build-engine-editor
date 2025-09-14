import logging
import subprocess
from abc import abstractmethod, ABCMeta
from dataclasses import dataclass
from pathlib import Path
from typing import Type

from applicationframework.mixins import HasAppMixin
from editor.graph import Graph


logger = logging.getLogger(__name__)


@dataclass
class AdaptorSettingsBase:

    exe_path: str


class AdaptorBase(HasAppMixin, metaclass=ABCMeta):

    """
    NOTE: At the moment we're conflating the idea of an engine's data with the
    executable that will run it - eg Doom data can be run with more than just
    gzdoom. Should be easy enough to decouple in the future.

    NOTE: Also not exactly happy with the concept of 'Adaptor'. Is an exporter
    an adaptor? What about an importer? So the definition is still a bit nebulous.
    At least this keeps all the code out of main.py.

    """

    def __init__(self):
        self.textures = {}
        self._settings = self.settings_cls()

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def settings_cls(self) -> Type[AdaptorSettingsBase]:
        ...

    @property
    @abstractmethod
    def icon_name(self) -> str:
        ...

    @property
    def settings(self) -> AdaptorSettingsBase:
        return self._settings

    @abstractmethod
    def load_resources(self):
        ...

    @abstractmethod
    def export_temp_map(self, g: Graph, path: Path):
        ...

    @property
    @abstractmethod
    def temp_map_name(self):
        ...

    @property
    @abstractmethod
    def subprocess_args(self):
        ...

    def play(self):
        exe_path = Path(self.settings.exe_path)
        if not exe_path.exists():
            raise Exception(f'Cannot find executable: {self.settings.exe_path}')

        # Export temp map to engine directory.
        temp_map_path = exe_path.parent.joinpath(self.temp_map_name)
        self.export_temp_map(self.app().doc.content, temp_map_path)
        logger.debug(f'Exported temp map: {temp_map_path}')

        # Launch game executable.
        logger.debug(f'Running: {exe_path}')
        process = subprocess.Popen(
            [exe_path] + self.subprocess_args,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,  # ensures output is in string format instead of bytes
            cwd=exe_path.parent,
        )

        # Read and print stderr.
        stderr_output, stdout_output = process.communicate()

        print('STDERR:')
        print(stderr_output)

        print('STDOUT:')
        print(stdout_output)

    def import_event(self):
        print('IMPORT')