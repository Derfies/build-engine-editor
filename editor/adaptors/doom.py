import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Type

import numpy as np
import omg

from editor.adaptors.base import AdaptorBase, AdaptorSettingsBase
from editor.constants import MapFormat
from editor.graph import Graph
from editor.mapio import doom


logger = logging.getLogger(__name__)


@dataclass
class DoomAdaptorSettings(AdaptorSettingsBase):

    exe_path: str = 'gzdoom.exe'
    doom_wad_path: str = 'DOOM.WAD'


class DoomAdaptor(AdaptorBase):

    @property
    def name(self) -> str:
        return 'doom'

    @property
    def settings_cls(self) -> Type[AdaptorSettingsBase]:
        return DoomAdaptorSettings

    @property
    def icon_name(self) -> str:
        return 'gzdoom'

    def export_temp_map(self, g: Graph, path: Path):
        doom.export_doom(g, path, MapFormat.DOOM)

    @property
    def temp_map_name(self):
        return 'out.wad'

    @property
    def subprocess_args(self):
        return ['-iwad', "DOOM.WAD", '-file', 'out.wad', '+map', 'MAP01']

    def load_resources(self):
        try:
            wad = omg.WAD(self.settings.doom_wad_path)
        except Exception as e:
            logger.error(f'Cannot load wad: {self.settings.doom_wad_path}')
            logger.exception(e)
            return
        palette = np.array(wad.palette.colors, dtype=np.uint8)
        all_gfx = dict(wad.patches) | dict(wad.flats)
        for k, patch in all_gfx.items():
            try:
                pixels = patch.to_raw()
            except Exception as e:
                print(k, e)
                continue
            bitmap = np.array([p if p is not None else 0 for p in pixels], dtype=np.uint8)
            array = palette[bitmap]
            w, h = patch.get_dimensions()
            array.shape = (h, w, 3)
            self.textures[k] = array
            logger.debug(f'Loaded doom texture: {k}')
