import pandas as pd
import pickle
import math
from neo4j import GraphDatabase, Transaction

# GROUPS_URI = "neo4j://neo4j_groups:7687"
GROUPS_URI = "bolt://neo4j_user:7474"
ELEMENTS_URI = "neo4j://neo4j_user:7687"
USER = "neo4j"
PSWD = "23109900"


class NxToNeo4jExplorer:
    def __init__(self):
        self.group_driver = GraphDatabase.driver(GROUPS_URI, auth=(USER, PSWD))
        self.driver = GraphDatabase.driver(ELEMENTS_URI, auth=(USER, PSWD))

    def close(self):
        self.driver.close()
        self.group_driver.close()

    @staticmethod
    def add_node(tx: Transaction, id_, type_, name, coords):
        q_create = "CREATE (a:Element {id: $id, type: $type, name: $name, coordinates: $crd})"
        tx.run(q_create, id=str(id_), type=type_, name=name, crd=coords)

    @staticmethod
    def add_edge(tx: Transaction, n, m):
        q_edge = '''
        MATCH (a:Element) WHERE a.id = $id1
        MATCH (b:Element) WHERE b.id = $id2
        MERGE (a)-[r:CONTAINS]->(b)
        '''
        tx.run(q_edge, id1=str(n), id2=str(m))

    @staticmethod
    def add_ifc_class(tx: Transaction, storey_id, class_id, class_name):
        q_class = '''
        MATCH (s:Element) WHERE s.id = $s_id
        MERGE (s)-[r:CONTAINS]->(:IfcClass {id: $id, name: $name})
        '''
        tx.run(q_class, s_id=str(storey_id), id=str(class_id), name=class_name)

    @staticmethod
    def add_class(tx: Transaction, class_name: str):
        q_class = '''
        MERGE (n:IfcClass {name: $name})
        '''
        tx.run(q_class, name=class_name)

    @staticmethod
    def add_el_to_class(tx: Transaction, class_id, element_id):
        q_cls_el = '''
        MATCH (c:IfcClass) WHERE c.id = $cls_id
        MATCH (e:Element) WHERE e.id = $el_id
        MERGE (c)-[:CONSISTS_OF]->(e)
        '''
        tx.run(q_cls_el, cls_id=str(class_id), el_id=str(element_id))

    @staticmethod
    def traverse(tx: Transaction, id1, id2):
        q_traverse = '''
        MATCH (a:Element) WHERE a.id = $id1
        MATCH (b:Element) WHERE b.id = $id2
        MERGE (a)-[:TRAVERSE]->(b)
        '''
        tx.run(q_traverse, id1=str(id1), id2=str(id2))

    @staticmethod
    def add_class_rel(tx: Transaction, pred_name: str, flw_name: str):
        q_rel = '''
        MATCH (a:IfcClass) WHERE a.name = $name1
        MATCH (b:IfcClass) WHERE b.name = $name2
        MERGE (a)-[r:FOLLOWS]->(b)
        '''
        tx.run(q_rel, name1=pred_name, name2=flw_name)

    def create_neo4j(self, G) -> None:
        """
        Создает граф в neo4j по объекту networkx.Graph
        :param G: networkx.Graph, сформированный по IFC модели
        """
        with self.driver.session() as session:
            session.run('MATCH (n) DETACH DELETE n')

            build_id = [node for node, data in G.nodes(data=True) if data.get('is_a') == 'IfcBuilding'][0]
            session.execute_write(
                NxToNeo4jExplorer.add_node, build_id, G.nodes[build_id]['is_a'],
                G.nodes[build_id]['name'], G.nodes[build_id]["coordinates"]
            )
            print(build_id, G.nodes[build_id]['is_a'], G.nodes[build_id]['name'], G.nodes[build_id]["coordinates"])

            # for stor_id in G.successors(build_id):
            for stor_id in [111, ]:
                data = G.nodes[stor_id]
                if data.get('is_a') != 'IfcBuildingStorey':
                    continue

                session.execute_write(NxToNeo4jExplorer.add_node, stor_id, data['is_a'], data['name'], data['coordinates'])
                session.execute_write(NxToNeo4jExplorer.add_edge, build_id, stor_id)

                contained_classes = set(G.nodes[i]['is_a'] for i in list(filter(
                    lambda el_id: G.nodes[el_id]["coordinates"],
                    G.successors(stor_id))
                ))
                cls_to_id = dict()
                for j, cls_name in enumerate(contained_classes):
                    cls_to_id[cls_name] = str(stor_id) + '_' + str(j)
                    session.execute_write(NxToNeo4jExplorer.add_ifc_class, stor_id, cls_to_id[cls_name], cls_name)

                for cls in contained_classes:
                    elements = list(filter(
                        lambda el_id: G.nodes[el_id]["is_a"] == cls and G.nodes[el_id]["coordinates"],
                        G.successors(stor_id))
                    )
                    # print(cls, len(elements))

                    start_point = (0, 0)

                    def compute_angle(el_id):
                        coordinates = G.nodes[el_id]["coordinates"]
                        x, y, z = coordinates[0], coordinates[1], coordinates[2]
                        angle = math.atan2(y - start_point[1], x - start_point[0])
                        return z, angle

                    # prev_id = 0
                    for j, i in enumerate(sorted(elements, key=compute_angle)):
                        s_data = G.nodes[i]
                        if s_data["coordinates"]:
                            session.execute_write(NxToNeo4jExplorer.add_node, i, s_data['is_a'], s_data['name'], s_data["coordinates"])
                            session.execute_write(NxToNeo4jExplorer.add_el_to_class, cls_to_id[cls], i)
                            if j > 0:
                                session.execute_write(NxToNeo4jExplorer.traverse, prev_id, i)
                            prev_id = i
                            if j == 4:
                                break
                break

    def connect_chains(self):
        def get_edge_elements(type1: str, type2: str):
            q_get_last = f'''MATCH (s:Element {{type: '{type1}' }})
            WHERE NOT (s)-[]->(:Element {{type: '{type1}' }})
            RETURN s.id AS id
            LIMIT 1'''
            last_id = self.driver.session().run(q_get_last).data()[0]['id']

            q_get_first = f'''MATCH (s:Element {{type: '{type2}' }})
            WHERE NOT (:Element {{type: '{type2}' }})-[]->(s)
            RETURN s.id AS id
            LIMIT 1'''
            first_id = self.driver.session().run(q_get_first).data()[0]['id']
            print(last_id, first_id)

            q_rel = f'''
            MATCH (a:Element) WHERE a.id = '{last_id}'
            MATCH (b:Element) WHERE b.id = '{first_id}'
            MERGE (a)-[r:TRAVERSE]->(b)
            '''
            self.driver.session().run(q_rel)
            return last_id, first_id

        with self.group_driver.session() as session:
            q_rel = '''
            MATCH (a:IfcClass)-[r:FOLLOWS]->(b:IfcClass)
            RETURN a.name AS type1, b.name AS type2
            '''
            result = pd.DataFrame(session.run(q_rel).data())
            result.apply(
                lambda row: get_edge_elements(row.type1, row.type2),
                axis=1
            )
            print(result)
