import re
import tempfile
from typing import Iterable, Tuple

import ifcopenshell
import networkx as nx
import requests
from ifcopenshell import entity_instance
from tqdm import tqdm

from myapp.loaders import BimModelLoader
from myapp.models import URN, ActiveLink, Storey, Wbs, WorkItem, WorkVolume, Rule
import yaml


class IFCLoader(BimModelLoader):
    def load(self, project: ActiveLink, spec: Wbs, model: URN) -> Iterable[Tuple[WorkItem, WorkVolume]]:
        # Создаем временный файл с расширением .ifc
        with tempfile.NamedTemporaryFile(suffix=".ifc") as file_object:
            # Скачиваем модель во временный файл используя потоковую запись
            with requests.get(model.urn, stream=True) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=8192):
                    file_object.write(chunk)
            # сбрасываем буфер записи и переходим в начало файла
            file_object.flush()
            file_object.seek(0)

            # открываем файл
            ifc_file = ifcopenshell.open(file_object.name)
            specification = Rule.objects.filter(name=spec.specs)
            print(specification)
            agg_keys = ("is_a", "group_type", "ADCM_DIN", "ADCM_Title")

            G, storeys = load_graph(ifc_file, agg_keys)
            yield from aggregate_items(G, storeys, agg_keys)


AGGREGATE_QTOS = {"Area", "NetVolume", "GrossVolume", "Length", "NetArea", "Объем"}


def filter_ifc(element: entity_instance) -> bool:
    return (
        element.is_a("IfcElement") or element.is_a("IfcSpatialStructureElement") or element.is_a("IfcObjectDefinition")
    ) and not (element.is_a("IfcGrid") or element.is_a("IfcAnnotation"))


def traverse(element, parent, filter_fn):
    if filter_fn(element):
        yield parent, element
        parent = element

    # follow Spatial relation
    if element.is_a("IfcSpatialStructureElement"):
        for rel in element.ContainsElements:
            relatedElements = rel.RelatedElements
            for child in relatedElements:
                yield from traverse(child, parent, filter_fn)

    # follow Aggregation Relation
    if element.is_a("IfcObjectDefinition"):
        for rel in element.IsDecomposedBy:
            relatedObjects = rel.RelatedObjects
            for child in relatedObjects:
                yield from traverse(child, parent, filter_fn)


def dict_merge(dct, merge_dct) -> None:
    for k, v in merge_dct.items():
        if k in dct and isinstance(dct[k], dict) and isinstance(merge_dct[k], dict):  # noqa
            dict_merge(dct[k], merge_dct[k])
        elif not dct.get(k):
            dct[k] = merge_dct[k]


LEVEL_RE = re.compile(r"(этаж)?\s*([-]?\d+)\s*(этаж)?", re.IGNORECASE)


def guess_level(G, storeys, index):
    if not storeys or index >= len(storeys) or index < 0:
        return None
    name = storeys[index]
    storey = G.nodes[name]
    level = storey.get("ADCM_Level")
    elevation = storey.get("Elevation", -1000000)
    if level:
        return level
    name = name.strip().lower()
    match = LEVEL_RE.match(name)
    if match:
        level = match.group(2)
        basement = level.startswith("-")
        while level and level.startswith("0"):
            level = level[1:]
        level = int(level)
        return f"L{'-' if basement else ''}{level:02d}"
    else:
        return f"L{int(elevation)}"


def aggregate_items(G, storeys, agg_keys):
    level_map = {s: guess_level(G, storeys, i) for i, s in enumerate(storeys)}

    node_lst = []
    for storey in tqdm(storeys, position=0):
        descendants = nx.descendants(G, storey)
        descendants.add(storey)
        sub = G.subgraph(descendants)  # subgraph
        ag_graph = nx.snap_aggregation(
            sub,
            node_attributes=agg_keys,
            prefix="",
        )
        for key in tqdm(ag_graph.nodes, position=1):
            n = ag_graph.nodes[key]
            if n["is_a"] == "IfcBuildingStorey":
                continue

            attrs = n
            count = 0
            for g in n["group"]:
                parents = G.in_edges(g)
                if len(parents) > 0:
                    lower_storey = next(
                        iter(sorted((G.nodes[p].get("Elevation", -1000000), p) for p, _ in parents if p in storeys)),
                        None,
                    )
                    if lower_storey and lower_storey[1] != storey:
                        continue
                count += 1
                sub_node = G.nodes[g]
                for k in {
                    "ADCM_Level",
                    "ADCM_RD",
                    "ADCM_DIN",
                    "ADCM_Title",
                    "is_a",
                }:
                    if not attrs.get(k):
                        attrs[k] = sub_node.get(k)
                for a in AGGREGATE_QTOS:  # volumes
                    if a in sub_node:
                        attrs[a] = attrs.setdefault(a, 0) + sub_node[a]

            level = attrs.get("ADCM_Level")
            if not level:
                level = level_map.get(storey)
            else:
                level_map["ADCM_Level"] = level

            yield (
                WorkItem(
                    work_type=attrs.get("ADCM_RD"),
                    building=attrs.get("ADCM_Title"),
                    storey=Storey(level, description=storey),
                    din=attrs.get("ADCM_DIN"),
                    name=n.get("group_type"),
                ),
                WorkVolume(
                    count=count,
                    value=attrs.get("Объем", attrs.get("NetVolume", attrs.get("GrossVolume", attrs.get("Area", attrs.get("NetArea"))))),
                ),
            )
    return node_lst


def load_graph(ifc_file, agg_keys):
    G = nx.MultiDiGraph()

    attribute_keys = AGGREGATE_QTOS.union(agg_keys).union({"Идентификация", "group_type", "Elevation"})

    def node(element):
        return element.Name

    def node_attributes(element) -> dict:
        atts = dict(
            global_id=str(element.GlobalId),
            is_a=element.is_a(),
            group_type=element.Name.rpartition(":")[0],
        )
        atts.update(element.get_info(include_identifier=True, recursive=True))
        psets = ifcopenshell.util.element.get_psets(element, qtos_only=True)
        for _, values in psets.items():
            for k, v in values.items():
                if k != "id":
                    atts[k] = v
        atts.update(ifcopenshell.util.element.get_psets(element, psets_only=True))
        for k, v in atts.get("Идентификация", {}).items():
            if k == "id":
                continue
            atts[k] = v
        atts.setdefault("ADCM_DIN", None)
        atts.setdefault("ADCM_Title", None)
        atts.setdefault(
            "Elevation",
            element.Elevation if element.is_a("IfcBuildingStorey") else None,
        )
        return {k: v for k, v in atts.items() if k in attribute_keys}

    storeys = set()
    # k = 0
    for project in ifc_file.by_type("IfcProject"):
        for parent, child in traverse(project, None, filter_ifc):
            attributes = node_attributes(child)
            n = node(child)
            if child.is_a("IfcBuildingStorey"):
                storeys.add(n)

            if G.has_node(n):
                attrs = G.nodes[n]
                dict_merge(attrs, attributes)
            else:
                G.add_node(node(child), **attributes)
            if parent is not None and not G.has_edge(node(parent), n):
                G.add_edge(node(parent), n)
    storeys = sorted(storeys, key=lambda x: G.nodes[x].get("Elevation", -1000000))
    return G, storeys
