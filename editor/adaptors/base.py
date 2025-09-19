import logging
import subprocess
import time
from abc import abstractmethod, ABCMeta
from dataclasses import dataclass
from pathlib import Path
from typing import Type

from PySide6.QtGui import QIcon, QImage, QPixmap

from applicationframework.mixins import HasAppMixin
from editor.graph import Graph

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


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

        # NOTE: If we want to adhere to the pub/sub paradigm these wouldn't be
        # settings and they would be updated via an event.
        self._settings = self.settings_cls()

        self.textures = {}
        self.images = {}
        self.pixmaps = {}
        self.icons = {}

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
    def build_textures(self):
        ...

    def build_images(self):
        for id_, texture in self.textures.items():
            img = QImage(texture, texture.shape[1], texture.shape[0], 3 * texture.shape[1], QImage.Format_RGB888)
            self.images[id_] = img

    def build_pixmaps(self):
        for id_, img in self.images.items():
            self.pixmaps[id_] = QPixmap.from_image(img)

    def build_icons(self):
        for id_, pixmap in self.pixmaps.items():
            self.icons[id_] = QIcon(pixmap.scaled(32, 32))

    def build_resources(self):
        logger.info('Rebuilding adaptor resources...')
        start = time.time()
        self.textures.clear()
        self.images.clear()
        self.pixmaps.clear()
        self.icons.clear()
        self.build_textures()
        self.build_images()
        self.build_pixmaps()
        self.build_icons()
        logger.info(f'Rebuilt adaptor resources in : {time.time() - start}')

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
