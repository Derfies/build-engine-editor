import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Type

from gameengines.build.grp import Grp
from gameengines.build.palette import Palette

from editor.adaptors.base import AdaptorBase, AdaptorSettingsBase
from editor.constants import MapFormat
from editor.graph import Graph
from editor.mapio import build


logger = logging.getLogger(__name__)


@dataclass
class DukeAdaptorSettings(AdaptorSettingsBase):

    exe_path: str = 'eduke32.exe'
    grp_path: str = 'DUKE3D.GRP'
    palette_path: str = 'PALETTE.DAT'


@dataclass
class BloodAdaptorSettings(AdaptorSettingsBase):

    exe_path: str = 'nblood.exe'
    grp_path: str = 'DUKE3D.GRP'
    palette_path: str = 'PALETTE.DAT'


class DukeAdaptor(AdaptorBase):

    """TODO: Split into Duke / Blood / Fury"""

    @property
    def name(self) -> str:
        return 'build'

    @property
    def settings_cls(self) -> Type[AdaptorSettingsBase]:
        return DukeAdaptorSettings

    @property
    def icon_name(self) -> str:
        return 'eduke32'

    def export_temp_map(self, g: Graph, path: Path):
        build.export_build(g, path, MapFormat.DUKE_3D)

    @property
    def temp_map_name(self):
        return 'out.map'

    @property
    def subprocess_args(self):
        return ['-map', 'out.map']

    def load_resources(self):
        try:
            grp = Grp()
            grp.load(self.settings.grp_path)
        except Exception as e:
            logger.error(f'Cannot load group: {self.settings.grp_path}')
            logger.exception(e)
            return

        try:
            palette = Palette()
            palette.load(self.settings.palette_path)
        except Exception as e:
            logger.error(f'Cannot load palette: {self.settings.palette_path}')
            logger.exception(e)
            return

        for i, texture in enumerate(grp.textures):
            self.textures[str(i)] = palette.data[texture]
            logger.debug(f'Loaded build texture: {i}')


class BloodAdaptor(AdaptorBase):

    """TODO: Split into Duke / Blood / Fury"""

    @property
    def name(self) -> str:
        return 'blood'

    @property
    def settings_cls(self) -> Type[AdaptorSettingsBase]:
        return BloodAdaptorSettings

    @property
    def icon_name(self) -> str:
        return 'nblood'

    def export_temp_map(self, g: Graph, path: Path):
        build.export_build(g, path, MapFormat.BLOOD)

    @property
    def temp_map_name(self):
        return 'out.map'

    @property
    def subprocess_args(self):
        return ['-map', 'out.map']

    def load_resources(self):
        try:
            grp = Grp()
            grp.load(self.settings.grp_path)
        except Exception as e:
            logger.error(f'Cannot load group: {self.settings.grp_path}')
            logger.exception(e)
            return

        try:
            palette = Palette()
            palette.load(self.settings.palette_path)
        except Exception as e:
            logger.error(f'Cannot load palette: {self.settings.palette_path}')
            logger.exception(e)
            return

        for i, texture in enumerate(grp.textures):
            self.textures[str(i)] = palette.data[texture]
            logger.debug(f'Loaded build texture: {i}')