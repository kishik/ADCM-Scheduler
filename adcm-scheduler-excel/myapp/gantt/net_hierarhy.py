import argparse
import csv
import pathlib
from pathlib import Path
from typing import Dict, List, Union

import ifcopenshell
import networkx as nx
import pandas as pd
from ifcopenshell import entity_instance
from tqdm import tqdm

AGGREGATE_QTOS = {"Area", "NetVolume", "GrossVolume", "Length", "NetArea"}


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


# def ifc_parse(file_names: List[str]):
#     G = nx.MultiDiGraph()
#
#     def node(element):
#         return element.Name
#
#     def node_attributes(element) -> dict:
#         atts = dict(
#             global_id=str(element.GlobalId),
#             is_a=element.is_a(),
#             group_type=element.Name.rpartition(":")[0],
#         )
#         atts.update(element.get_info(include_identifier=True, recursive=True))
#         psets = ifcopenshell.util.element.get_psets(element, qtos_only=True)
#         for _, values in psets.items():
#             for k, v in values.items():
#                 if k != "id":
#                     atts[k] = v
#         atts.update(ifcopenshell.util.element.get_psets(element, psets_only=True))
#         for k, v in atts.get("Идентификация", {}).items():
#             if k == "id":
#                 continue
#             atts[k] = v
#         atts.setdefault("ADCM_DIN", None)
#         atts.setdefault("ADCM_Title", None)
#         atts.setdefault(
#             "Elevation",
#             element.Elevation if element.is_a("IfcBuildingStorey") else None,
#         )
#         return atts
#
#     storeys = set()
#     for file_name in file_names:
#         ifc_file = ifcopenshell.open(file_name)
#         for project in tqdm(ifc_file.by_type("IfcProject"), position=1):
#             for parent, child in tqdm(traverse(project, None, filter_ifc), position=2):
#                 attributes = node_attributes(child)
#                 n = node(child)
#                 if child.is_a("IfcBuildingStorey"):
#                     storeys.add(n)
#
#                 if G.has_node(n):
#                     attrs = G.nodes[n]
#                     dict_merge(attrs, attributes)
#                 else:
#                     G.add_node(node(child), **attributes)
#                 if parent is not None and not G.has_edge(node(parent), n):
#                     G.add_edge(node(parent), n)
#
#     agg_keys = ("is_a", "group_type", "ADCM_DIN", "ADCM_Title")
#     storeys = sorted(storeys, key=lambda x: G.nodes[x].get("Elevation", -1000000))
#     node_lst = []
#
#     for storey in tqdm(storeys, position=0):
#         descendants = nx.descendants(G, storey)
#         descendants.add(storey)
#         sub = G.subgraph(descendants)  # subgraph
#         ag_graph = nx.snap_aggregation(
#             sub,
#             node_attributes=agg_keys,
#             prefix="",
#         )
#         for key in tqdm(ag_graph.nodes, position=1):
#             n = ag_graph.nodes[key]
#             if n["is_a"] == "IfcBuildingStorey":
#                 continue
#
#             attrs = n
#             count = 0
#             for g in n["group"]:
#                 parents = G.in_edges(g)
#                 if len(parents) > 0:
#                     lower_storey = next(
#                         iter(
#                             sorted(
#                                 (G.nodes[p].get("Elevation", -1000000), p)
#                                 for p, _ in parents
#                                 if p in storeys
#                             )
#                         ),
#                         None,
#                     )
#                     if lower_storey and lower_storey[1] != storey:
#                         continue
#                 count += 1
#                 sub_node = G.nodes[g]
#                 for k in {
#                     "ADCM_Level",
#                     "ADCM_RD",
#                     "ADCM_DIN",
#                     "ADCM_Title",
#                     "is_a",
#                 }:
#                     if not attrs.get(k):
#                         attrs[k] = sub_node.get(k)
#                 for a in AGGREGATE_QTOS:  # volumes
#                     if a in sub_node:
#                         attrs[a] = attrs.setdefault(a, 0) + sub_node[a]
#
#             node_lst.append({
#                 # "storey": storey,
#                 "name": n["group_type"],
#                 "wbs3": count,
#                 # "length": attrs.get("Length"),
#                 # "area": attrs.get("Area", attrs.get("NetArea")),
#                 "value": attrs.get("NetVolume", attrs.get("GrossVolume")),
#                 "wbs2": G.nodes[storey].get("ADCM_Level"),
#                 # "rd": attrs.get("ADCM_RD"),
#                 "wbs3_id": attrs.get("ADCM_DIN"),
#                 "wbs1": attrs.get("ADCM_Title"),
#                 # "ifc_type": n["is_a"],
#             })
#
#     return node_lst


def main(files: List[Union[str, Path]]) -> List[Dict[str, str]]:
    G = nx.MultiDiGraph()

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
        return atts

    storeys = set()

    for file_name in tqdm(files, position=0):
        ifc_file = ifcopenshell.open(file_name)
        # k = 0
        for project in tqdm(ifc_file.by_type("IfcProject"), position=1):
            for parent, child in tqdm(traverse(project, None, filter_ifc), position=2):
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

    agg_keys = ("is_a", "group_type", "ADCM_DIN", "ADCM_Title")
    storeys = sorted(storeys, key=lambda x: G.nodes[x].get("Elevation", -1000000))

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

            node_lst.append(
                {
                    # "storey": storey,
                    # "count": count,
                    # "length": attrs.get("Length"),
                    # "area": attrs.get("Area", attrs.get("NetArea")),
                    # "ifc_type": n["is_a"],
                    "wbs1": attrs.get("ADCM_Title", "No title"),
                    "wbs2": G.nodes[storey].get("ADCM_Level", "No level"),
                    "wbs3_id": attrs.get("ADCM_DIN", "No DIN"),
                    "wbs3": attrs.get("ADCM_RD", "No RD"),
                    "name": n.get("group_type", "No type"),
                    "value": attrs.get(
                        "NetVolume", attrs.get("GrossVolume", attrs.get("Area", attrs.get("NetArea", "No volume")))
                    ),
                    "wbs": "".join(filter(None, [attrs.get("ADCM_Title"), attrs.get("ADCM_DIN")])),
                }
            )

    return node_lst


# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(
#         prog="net_hierarchy.py",
#         description="Aggregates IFC model to the list of construction elements",
#     )
#     parser.add_argument(
#         "output",
#         metavar="output_csv_file",
#         type=pathlib.Path,
#     )
#     parser.add_argument(
#         "files",
#         metavar="ifc_file",
#         type=pathlib.Path,
#         nargs="+",
#         help="an IFC model file",
#     )
#     args = parser.parse_args()
#
#     with open(args.output, "w", encoding="utf-8", newline="") as out:
#         writer = csv.DictWriter(
#             out,
#             fieldnames=[
#                 'wbs1',
#                 'wbs2',
#                 'wbs3',
#                 'wbs3_id',
#                 'name',
#                 'value',
#                 'count'
#             ],
#         )
#         writer.writeheader()
#         for record in main(args.files):
#             writer.writerow(record)
#             print(record)
