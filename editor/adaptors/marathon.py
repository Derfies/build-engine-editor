import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Type

from jjaro.shpA import ShpA

from editor.adaptors.base import AdaptorBase, AdaptorSettingsBase
from editor.graph import Graph


logger = logging.getLogger(__name__)


@dataclass
class MarathonAdaptorSettings(AdaptorSettingsBase):

    exe_path: str = 'Aleph One.exe'
    shapes_path: str = 'Shapes.shpA'


class MarathonAdaptor(AdaptorBase):

    @property
    def name(self) -> str:
        return 'marathon'

    @property
    def settings_cls(self) -> Type[AdaptorSettingsBase]:
        return MarathonAdaptorSettings

    @property
    def icon_name(self) -> str:
        return 'aleph_one'

    def export_temp_map(self, g: Graph, path: Path):
        pass

    @property
    def temp_map_name(self):
        return None

    @property
    def subprocess_args(self):
        return None

    def load_resources(self):
        try:
            shapes = ShpA()
            shapes.load(self.settings.shapes_path)
        except Exception as e:
            logger.error(f'Cannot load shapes: {self.settings.shapes_path}')
            logger.exception(e)
            return

        for i, texture in enumerate(shapes.textures):
            self.textures[str(i)] = texture
            logger.debug(f'Loaded marathon texture: {i}')
