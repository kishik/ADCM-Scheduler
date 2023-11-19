import os

import ifcopenshell
import networkx as nx
from ifcopenshell import entity_instance


class IfcToNxConverter:
    """
    Класс для создания networkx графа из ifc файла
    """

    def __init__(self):
        self.G = nx.MultiDiGraph()

    @staticmethod
    def _filter_ifc(element: entity_instance) -> bool:
        return (
                element.is_a("IfcElement")
                or element.is_a("IfcSpatialStructureElement")
                or element.is_a("IfcObjectDefinition")
        ) and not (element.is_a("IfcGrid") or element.is_a("IfcAnnotation"))

    @staticmethod
    def _traverse(element, parent, filter_fn):
        if filter_fn(element):
            yield parent, element
            parent = element

        # follow Spatial relation
        if element.is_a('IfcSpatialStructureElement'):
            # session.execute_write(graph.node, str(element.id()), element.Name)
            for rel in element.ContainsElements:
                relatedElements = rel.RelatedElements
                for child in relatedElements:
                    yield from IfcToNxConverter._traverse(child, parent, filter_fn)

        # follow Aggregation Relation
        if element.is_a('IfcObjectDefinition'):
            for rel in element.IsDecomposedBy:
                relatedObjects = rel.RelatedObjects
                for child in relatedObjects:
                    yield from IfcToNxConverter._traverse(child, parent, filter_fn)

    @staticmethod
    def _dict_merge(dct, merge_dct) -> None:
        for k, v in merge_dct.items():
            if k in dct and isinstance(dct[k], dict) and isinstance(merge_dct[k], dict):  # noqa
                IfcToNxConverter._dict_merge(dct[k], merge_dct[k])
            elif not dct.get(k):
                dct[k] = merge_dct[k]

    @staticmethod
    def node_attributes(elem) -> dict:
        atts = dict(
            global_id=str(elem.GlobalId),
            name=elem.Name,
            is_a=elem.is_a(),
            group_type=elem.Name.rpartition(":")[0],
        )
        psets = ifcopenshell.util.element.get_psets(elem, psets_only=True)
        if "ADCM" in psets.keys():
            # delete unnecessary key "id" from ADCM
            psets["ADCM"].pop('id')
            atts.update(psets["ADCM"])

        atts.setdefault("ADCM_Title", None)
        atts.setdefault("ADCM_Level", None)
        atts.setdefault("ADCM_DIN", None)
        atts.setdefault("ADCM_RD", None)
        atts.setdefault("ADCM_JobType", None)
        atts.setdefault("ADCM_Part", None)

        atts.setdefault(
            "Elevation",
            elem.Elevation if elem.is_a("IfcBuildingStorey") else None,
        )

        def get_coordinates(el):
            if not hasattr(el, "ObjectPlacement"):
                return 0.0, 0.0, 0.0
            return el.ObjectPlacement.RelativePlacement.Location.Coordinates
            # return None if coords == (0.0, 0.0, 0.0) else coords

        atts["coordinates"] = get_coordinates(elem)
        return atts

    def create_net_graph(self, root: str):
        """
        Создает граф в поле self.G
        :param path: путь до директории с IFC файлами
        """

        def node(element):
            """
            :param element: IFC entity
            :return: element id
            """
            return element.id()

        file_list = []
        for path, subdirs, files in os.walk(root):
            for name in files:
                if name.endswith('.ifc'):
                    file_list.append(os.path.join(path, name))
        for ifc_path in file_list:
            print(ifc_path)
            ifc_file = ifcopenshell.open(ifc_path)
            for project in ifc_file.by_type("IfcProject"):
                for parent, child in IfcToNxConverter._traverse(project, None, IfcToNxConverter._filter_ifc):
                    attributes = IfcToNxConverter.node_attributes(child)
                    n = node(child)
                    if self.G.has_node(n):
                        attrs = self.G.nodes[n]
                        IfcToNxConverter._dict_merge(attrs, attributes)
                    else:
                        self.G.add_node(n, **attributes)
                    if parent is not None and not self.G.has_edge(node(parent), n):
                        self.G.add_edge(node(parent), n)

    def get_net_graph(self):
        """
        Возвращает созданный граф
        :return: networkx.MultiDiGraph
        """
        return self.G
    