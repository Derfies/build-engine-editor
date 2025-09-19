import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Type

import numpy as np
import omg
from omg.txdef import Textures

from editor.adaptors.base import AdaptorBase, AdaptorSettingsBase
from editor.constants import MapFormat
from editor.graph import Graph
from editor.mapio import doom


logger = logging.getLogger(__name__)


# noinspection PyUnresolvedReferences
from __feature__ import snake_case



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

    def _build_flats(self, wad: omg.WAD, palette: np.ndarray):
        for name, flat in wad.flats.items():
            indices = np.array([p if p is not None else 0 for p in flat.to_raw()], dtype=np.uint8)
            w, h = flat.get_dimensions()
            self.textures[name] = palette[indices].reshape((h, w, 3))
            logger.debug(f'Loaded doom flat: {name}')

    def _build_txdefs(self, wad: omg.WAD, palette: np.ndarray):
        for name, texture in Textures(wad.txdefs).items():
            indices = np.zeros((texture.height, texture.width), dtype=np.uint8)
            for patch_def in texture.patches:
                patch = wad.patches[patch_def.name]
                patch_indices = np.array([p if p is not None else 0 for p in patch.to_pixels()], dtype=np.uint8)
                patch_indices.shape = (patch.height, patch.width)

                # Blit the patch into the texture, making sure we don't attempt
                # to blit past the edge of the canvas.
                x_offset = patch_def.x
                y_offset = patch_def.y
                w = patch_indices.shape[1]
                h = patch_indices.shape[0]
                space_x = min(w, indices.shape[1] - x_offset)
                space_y = min(h, indices.shape[0] - y_offset)
                try:
                    indices[y_offset:min(y_offset + h, indices.shape[0]), x_offset:min(x_offset + w, indices.shape[1])] = patch_indices[0:space_y, 0:space_x]
                except Exception as e:
                    print(e)
                    continue

                self.textures[texture.name] = palette[indices]
                logger.debug(f'Built doom patch def: {texture.name}')

    def build_textures(self):
        try:
            wad = omg.WAD(self.settings.doom_wad_path)
        except Exception as e:
            logger.error(f'Cannot load wad: {self.settings.doom_wad_path}')
            logger.exception(e)
            return
        palette = np.array(wad.palette.colors, dtype=np.uint8)
        self._build_flats(wad, palette)
        self._build_txdefs(wad, palette)
