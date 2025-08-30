from xml.etree import ElementTree as et

from networkx.readwrite.gexf import GEXFWriter as BaseGEXFWriter
from networkx.utils import open_file

from editor.constants import MapFormat, ATTRIBUTES
from editor.graph import Graph


def export_gexf(graph: Graph, file_path: str, format: MapFormat):
    g = graph.data.copy()

    # Move all attribute dicts to the root of the element so the exporter picks
    # them up. Node coords require special treatment for the GEXF format.
    g.graph.update(g.graph.pop(ATTRIBUTES))
    for node, attrs in g.nodes(data=True):
        attrs.update(attrs.pop(ATTRIBUTES))
        attrs['viz'] = {'position': {'x': attrs.pop('x'), 'y': attrs.pop('y'), 'z': 0}}
    for head, tail, attrs in g.edges(data=True):
        attrs.update(attrs.pop(ATTRIBUTES))

    write_gexf(g, file_path)


type_map = {
    bool: 'boolean',
    int: 'integer',
    float: 'double',
    str: 'string'
}


class GEXFWriter(BaseGEXFWriter):

    def add_graph(self, G):
        super().add_graph(G)

        # HAXXOR to poke in scale.
        attrs_els = self.graph_element.findall('attributes[@class=""][@mode="static"]')
        assert len(attrs_els) < 2, 'Should only be one attributes element'
        if not attrs_els:
            attrs_el = et.Element('attributes', attrib={'mode': 'static', 'class': ''})
            self.graph_element.insert(0, attrs_el)
        else:
            attrs_el = attrs_els[0]

        for key, value in G.graph.items():

            # TODO:
            if type(value) not in type_map:
                print('skip:', key, '->', type(value))
                continue

            attr_el = et.Element('attribute', attrib={'id': key, 'title': key, 'type': type_map[type(value)]})
            attrs_el.append(attr_el)

            value_el = et.Element('default')
            value_el.text = str(value)
            attr_el.append(value_el)


@open_file(1, mode='wb')
def write_gexf(G, path, encoding='utf-8', prettyprint=True, version='1.2draft'):
    """Duplicate from networkx\readwrite\gexf.py"""
    writer = GEXFWriter(encoding=encoding, prettyprint=prettyprint, version=version)
    writer.add_graph(G)
    #writer.add_graph_attributes()
    writer.write(path)
