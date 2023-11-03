import ifcopenshell
import networkx as nx
from ifcopenshell import entity_instance


class IfcToNxExplorer:
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
                    yield from IfcToNxExplorer._traverse(child, parent, filter_fn)

        # follow Aggregation Relation
        if element.is_a('IfcObjectDefinition'):
            for rel in element.IsDecomposedBy:
                relatedObjects = rel.RelatedObjects
                for child in relatedObjects:
                    yield from IfcToNxExplorer._traverse(child, parent, filter_fn)

    def create_net_graph(self, ifc_path: str):
        """
        Создает граф в поле self.G
        :param ifc_path: путь до ifc файла
        """
        ifc_file = ifcopenshell.open(ifc_path)

        def node(element):
            return element.id()

        def get_coordinates(element):
            if not hasattr(element, "ObjectPlacement"):
                return None
            if not element.ObjectPlacement.RelativePlacement.Axis:
                return None
            coords = element.ObjectPlacement.RelativePlacement.Location.Coordinates
            return None if coords == (0.0, 0.0, 0.0) else coords

        for project in ifc_file.by_type("IfcProject"):
            for parent, child in IfcToNxExplorer._traverse(project, None, IfcToNxExplorer._filter_ifc):
                self.G.add_node(node(child),
                                global_id=str(child.GlobalId),
                                is_a=child.is_a(),
                                name=child.Name,
                                coordinates=get_coordinates(child)
                                )
                if parent is not None:
                    self.G.add_edge(node(parent), node(child))

    def get_net_graph(self):
        """
        Возвращает созданный граф
        :return: networkx.MultiDiGraph
        """
        return self.G
    

    def get_dict(self):
        # TODO Возвращать граф в виде словаря
        myJson = {
            # "data": [
            #     {

            #         "wbs1": item.building or "None",
            #         "wbs2": item.storey.name if item.storey else "",
            #         "wbs3_id": item.din or "None",
            #         "wbs3": item.work_type or "None",

            #         "name": item.name or "None",
            #         "value": volume.value if volume.value is not None else volume.count,
            #         "wbs": f"{item.building}{item.din}",
            #         # "wbs3_id": ''.join((item.building or "", item.storey.name if item.storey else "", item.name)),

            #     }
            #     for item, volume in data.items()
            #     for key, value in self.G.nodes.items()
            # ]
        }
        return myJson

    # TODO sdr фильтрация и несколько файлов на вход(папку)
