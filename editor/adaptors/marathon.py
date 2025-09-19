import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Type

from jjaro.shpA import ShpA

from editor.adaptors.base import AdaptorBase, AdaptorSettingsBase
from editor.graph import Graph

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


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

    def build_textures(self):

        def make_value(collection: int, texture_id: int) -> int:

            # TODO: Inline
            return (collection << 8) | (texture_id & 0xFF)

        try:
            shapes = ShpA()
            shapes.load(self.settings.shapes_path)
        except Exception as e:
            logger.error(f'Cannot load shapes: {self.settings.shapes_path}')
            logger.exception(e)
            return

        # First texture collection is in slot 17.
        for coll_idx in range(17, 22):
            for tex_idx, tex in enumerate(shapes.collections[coll_idx].textures):
                key = make_value(coll_idx, tex_idx)
                self.textures[key] = shapes.collections[coll_idx].textures[tex_idx]
                logger.debug(f'Loaded marathon texture: {key}')
