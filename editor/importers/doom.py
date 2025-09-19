from collections import defaultdict
from typing import Any

import numpy as np
import omg
from omg.mapedit import Sidedef, Sector
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QVBoxLayout

from editor.graph import Edge, Face, Graph
from editor.importers.base import ImporterBase, ImporterDialogBase
from editor.texture import Texture


def get_ring_bounds(m, ring: list[Any]) -> tuple:
    positions = [(edge.head.get_attribute('x'), edge.tail.get_attribute('y')) for edge in ring]
    min_pos = np.amin(positions, axis=0)
    max_pos = np.amax(positions, axis=0)
    return tuple(max_pos - min_pos)


def map_wall_to_edge(side: Sidedef, sector: Sector):
    return {
        'low_tex': Texture(side.texturebottom),
        'mid_tex': Texture(side.texturemiddle),
        'top_tex': Texture(side.texturetop),
        'shade': sector.lightlevel / 255 + 0.1,
    }


def map_sector_to_face(sector: Sector, global_scale):
    return {
        'ceilingshade': sector.lightlevel / 255,
        'floorshade': sector.lightlevel / 255,
        'ceilingz': sector.heightceiling * global_scale,
        'floorz': sector.heightfloor * global_scale,
        'floor_tex': Texture(sector.texturefloor),
        'ceiling_tex': Texture(sector.textureceiling),
    }


def map_face_to_sector(face: Face, global_scale: float):
    """
    NOTE: Casting to string in case the textures originally came from an engine
    that used integers to index their textures.

    """
    attrs = face.get_attributes()
    return {
        'z_floor': int(attrs['floorz'] * global_scale),
        'z_ceil': int(attrs['ceilingz'] * global_scale),
        'tx_floor': str(attrs['floor_tex'].value),
        'tx_ceil': str(attrs['ceiling_tex'].value),
    }


def map_edge_to_side(edge: Edge, face_to_index: dict):
    """
    NOTE: Casting to string in case the textures originally came from an engine
    that used integers to index their textures.

    """
    edge_attrs = edge.get_attributes()
    attrs = {
        'off_x': 0,
        'off_y': 0,
        'sector': face_to_index[edge.face],
    }
    if edge.reversed is None:
        attrs['tx_mid'] = str(edge_attrs['mid_tex'].value)
    else:
        attrs['tx_up'] = str(edge_attrs['top_tex'].value)
        attrs['tx_low'] = str(edge_attrs['low_tex'].value)
    return attrs


def order_tuples_into_chains(tuples):
    if not tuples:
        return []

    unused = set(tuples)
    chains = []

    while unused:
        # Pick a starting tuple
        current = unused.pop()
        chain = [current]

        # Extend forward
        while True:
            last = chain[-1]
            next_tuple = None
            for t in list(unused):
                if t.head == last.tail:
                    next_tuple = t
                    break
            if not next_tuple:
                break
            chain.append(next_tuple)
            unused.remove(next_tuple)

            # Loop closed?
            if chain[-1].tail == chain[0].head:
                chain.append(chain[0])
                break

        chains.append(chain)

    return chains


class DoomImporterDialog(ImporterDialogBase):

    def __init__(self, items: list[str], *args, **kwargs):
        super().__init__(*args, **kwargs)

        main_layout = QVBoxLayout(self)
        self.combo = QComboBox(self)
        self.combo.add_items(items)
        main_layout.add_widget(self.combo)

        # Add OK and Cancel buttons.
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.add_widget(buttons)

    def get_options(self):
        return {'map_name': self.combo.current_text()}


class DoomImporter(ImporterBase):

    format = 'Doom WAD (*.wad)'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._wad = omg.WAD(self.file_path)

    def create_dialog(self) -> QDialog:
        return DoomImporterDialog(list(self._wad.maps))

    def run(self, graph: Graph, **kwargs):

        global_scale = 14

        m = omg.UMapEditor(self._wad.maps[kwargs['map_name']])

        # Nodes.
        nodes = []
        for i, vertex in enumerate(m.vertexes):
            node = graph.add_node(i, x=vertex.x * global_scale, y=vertex.y * global_scale)
            nodes.append(node)

        # Edges.
        # We change the lighting just a bit to make things visible, otherwise apparently
        # there is no per-wall lighting.
        sector_idx_to_edges = defaultdict(list)
        for i, line in enumerate(m.linedefs):
            for reverse, side_idx in enumerate((line.sidefront, line.sideback)):
                if side_idx < 0:
                    continue
                head, tail = line.v2, line.v1
                if reverse:
                    head, tail = tail, head
                side = m.sidedefs[side_idx]
                sector_idx = side.sector
                sector = m.sectors[sector_idx]
                edge_attrs = map_wall_to_edge(side, sector)
                edge = graph.add_edge((head, tail), **edge_attrs)
                sector_idx_to_edges[sector_idx].append(edge)

        for sector_idx, edges in sector_idx_to_edges.items():
            sector = m.sectors[sector_idx]
            rings = order_tuples_into_chains(edges)
            face_attrs = map_sector_to_face(sector, global_scale)
            sorted_rings = sorted(rings, key=lambda r: get_ring_bounds(m, r), reverse=True)
            graph.add_face(tuple([node.head.data for ring in sorted_rings for node in ring]), **face_attrs)

        graph.update()
