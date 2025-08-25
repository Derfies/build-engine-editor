import xml.etree.ElementTree as et

from networkx.readwrite.gexf import GEXFWriter as BaseGEXFWriter
from networkx.utils import open_file


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
            attrs_el = et.Element('attributes', attrib={'class': '', 'mode': 'static'})
            self.graph_element.append(attrs_el)
        else:
            attrs_el = attrs_els[0]

        for key, value in G.graph.items():

            # TODO:
            if type(value) not in type_map:
                print('skip:', key)
                continue



        #for attr_name in ['faces']:
            #value = G.graph[key]
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
