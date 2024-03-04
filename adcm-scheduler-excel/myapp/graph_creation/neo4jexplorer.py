import logging

import pandas as pd
from neo4j import GraphDatabase

from myapp.gantt.data_collect import calculateDinsDistance, allDins
from myapp.graph_creation import utils, yml

logger = logging.getLogger(__name__)


class Neo4jExplorer:
    def __init__(self, uri=None, pswd="23109900"):
        # read settings from config
        self.cfg: dict = yml.get_cfg("neo4j")
        if uri:
            _uri = uri
        else:
            _uri = self.cfg.get("url")
        if pswd:
            _pswd = pswd
        else:
            _pswd = self.cfg.get("password")

        _user = "neo4j"

        logger.debug(f'Init NEO4J driver: {_uri}')
        self.driver = GraphDatabase.driver(_uri, auth=(_user, _pswd))

    def close(self):
        # Don't forget to close the driver connection when you are finished with it
        self.driver.close()

    def load_historical_graph(self):
        # driver to historical database
        _hist_uri = self.cfg.get("hist_url")
        _hist_user = self.cfg.get("user")
        _hist_pass = self.cfg.get("hist_password")
        logger.debug(f'Loading historical graph: {_hist_uri}')
        _hist_driver = GraphDatabase.driver(_hist_uri, auth=(_hist_user, _hist_pass))

        Q_DATA_OBTAIN = """
            MATCH (n)-[r]->(m)
            RETURN n.name AS n_name, n.DIN AS n_id, properties(r).weight AS weight, m.name AS m_name, m.DIN AS m_id
            """
        lnk = self.cfg.get("hist_url")
        Q_CREATE = f"""
            LOAD CSV WITH HEADERS FROM '{lnk}' AS row
            MERGE (n:Work {{DIN: row.n_id, name: row.n_name}})
            MERGE (m:Work {{DIN: row.m_id, name: row.m_name}})
            CREATE (n)-[r:FOLLOWS {{weight: row.weight}}]->(m);
            """

        # obtaining data
        result = _hist_driver.session().run(Q_DATA_OBTAIN).data()
        _hist_driver.close()

        # to do: cделать нормальную передачу CSV-файла
        df = pd.DataFrame(result)
        save_path = ""
        df.to_csv(save_path + "data.csv", index=False)
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")  # Предварительная очистка базы данных
            session.run(Q_CREATE)

    def single_graph_copy(self, uri=None):
        if uri:
            _hist_uri = uri
        else:
            _hist_uri = self.cfg.get("x2_url")
        _hist_user = "neo4j"
        # _hist_pass = self.cfg.get("hist_password")
        _hist_pass = "23109900"
        logger.debug(f'Historical graph copy: {_hist_uri}')
        _hist_driver = GraphDatabase.driver(_hist_uri, auth=(_hist_user, _hist_pass))
        Q_NODES_OBTAIN = """
        MATCH (n:Work)
        WHERE n.type = 'start'
        RETURN n.name AS n_name, n.DIN AS n_din
        """
        Q_NODES_CREATE = """
        MERGE (s:Work {DIN: $n_din, name: $n_name})
        """
        Q_RELS_OBTAIN = """
        MATCH (n)-[r:FOLLOWS]->(m) 
        RETURN n.DIN AS n_din, m.DIN AS m_din, properties(r).weight AS weight
        """
        Q_RELS_CREATE = """
        MATCH (n:Work)
        WHERE n.DIN = $n_din
        MATCH (m:Work)
        WHERE m.DIN = $m_din
        MERGE (n)-[r:FOLLOWS]->(m)
        SET r.weight = $wght;
        """
        # SET r.weight = coalesce(r.weight, 0) + 1;
        with _hist_driver.session() as in_session:
            node_df = pd.DataFrame(in_session.run(Q_NODES_OBTAIN).data())
            rel_df = pd.DataFrame(in_session.run(Q_RELS_OBTAIN).data())

        with self.driver.session() as session:
            session.execute_write(utils.clear_database)
            logger.debug("local database cleared")
            node_df.apply(
                lambda row: session.run(
                    Q_NODES_CREATE,
                    n_din=row["n_din"],
                    n_name=row["n_name"]
                ), axis=1
            )

            rel_df.apply(
                lambda row: session.run(
                    Q_RELS_CREATE,
                    n_din=row["n_din"],
                    m_din=row["m_din"],
                    wght=row["weight"]
                ), axis=1
            )

        self.del_loops()
        logger.debug("historical db copied to local")
        logger.debug('all dins after copy db')
        logger.debug(len(self.get_all_dins()))

    def removing_node(self, din: str):
        Q_PRED_FLW_OBTAIN = """
        MATCH (pred)-[]->(m) WHERE m.DIN = $din
        MATCH (n)-[]->(flw) WHERE n.DIN = $din
        RETURN pred.DIN AS pred_din, flw.DIN AS flw_din
        """
        with self.driver.session() as session:
            result_df = pd.DataFrame(session.run(Q_PRED_FLW_OBTAIN, din=din).data())
            result_df.apply(
                lambda row: session.run(
                    """
                    MATCH (pred)
                    WHERE pred.DIN = $din1 AND pred.type = 'finish'
                    MATCH (flw)
                    WHERE flw.DIN = $din2 AND flw.type = 'start'
                    MERGE (pred)-[:TRAVERSE]->(flw)
                    """,  # weight of new edges?
                    din1=row.pred_din,
                    din2=row.flw_din,
                ),
                axis=1,
            )
            session.run("MATCH (n) WHERE n.DIN = $din DETACH DELETE n", din=din)

    def get_all_dins(self):
        Q_DATA_OBTAIN = """
        MATCH (n)
        RETURN DISTINCT n.DIN AS din
        """
        result = pd.DataFrame(self.driver.session().run(Q_DATA_OBTAIN).data())
        logger.debug('all dins')
        logger.debug(result)
        return result.din.to_numpy()

    def create_new_graph_algo(self, target_ids):
        # self.del_loops()
        for element in self.get_all_dins():
            if element not in target_ids:
                self.removing_node(element)
        self.del_loops()

    def del_loops(self):
        q_del_isolated_pairs = """
        MATCH (n1)-->(n2)
        WHERE not ()-->(n1) AND not (n2)-->()
        DETACH DELETE n1, n2;
        """
        q_del_isolated_nodes = """
        MATCH (n)
        WHERE NOT ()- -(n)
        DETACH DELETE n;
        """
        q_del_4x_loop = """
        match ()-->(n1)-->(n2)-->(n3)-->(n4)-->(n1)-->()
        detach delete n3, n4
        """
        q_del_3x_loop = """
        match (b)<-[r]-(a)-[]->(c)-[]->(b)
        delete r
        """
        q_del_2x_loop = """
        match (x)-[]->(y)-[]->(x)
        detach delete y
        """
        q_del_1x_loop = """
        match (x)-[r]->(x)
        delete r
        """
        self.driver.session().run(q_del_1x_loop)
        self.driver.session().run(q_del_2x_loop)
        self.driver.session().run(q_del_3x_loop)
        self.driver.session().run(q_del_4x_loop)
        self.driver.session().run(q_del_isolated_pairs)
        self.driver.session().run(q_del_isolated_nodes)

    def get_nodes(self, df: pd.DataFrame = None) -> list[dict]:
        q_nodes = """MATCH 
        (el)-[:FOLLOWS]->(fl) RETURN el.DIN as id, el.name as name
        UNION MATCH 
        (el)-[:FOLLOWS]->(fl) RETURN fl.DIN as id, fl.name as name
        """
        with self.driver.session() as session:
            nodes = session.run(q_nodes).data()
            distances = calculateDinsDistance(session, allDins(session))

        for i in nodes:
            i.update({"distance": distances.get(i.get("id"), 0)})
            if df is not None:
                i.update({
                    "wbs1": df.loc[df['Шифр'] == i.get("id"), 'СПП'].values[0],
                    "wbs2": df.loc[df['Шифр'] == i.get("id"), 'Проект'].values[0],
                    "wbs3": df.loc[df['Шифр'] == i.get("id"), 'Наименование локальной сметы'].values[0],
                })
        nodes.sort(key=lambda el: el["distance"])
        return nodes

    def get_edges(self):
        query = """
        MATCH (el)-[:FOLLOWS]->(flw) 
        RETURN el.DIN as source, flw.DIN as target
        """
        edges = self.driver.session().run(query).data()
        for edge in edges:
            edge.update({"type": "0", "lag": 0})
        return edges


if __name__ == "__main__":
    # cfg: dict = yml.get_cfg("neo4j")

    # URL = cfg.get("url")
    # USER = cfg.get("user")
    # PASS = cfg.get("password")

    # X2_URL = cfg.get("x2_url")
    # X2_PASS = cfg.get("x2_password")

    app = Neo4jExplorer(uri="bolt://localhost:7687", pswd="23109900")
    # app.hist_graph_copy()
    dins = app.get_all_dins()
    print(dins)
    print(dins[dins != None][:-2])
    # app.create_new_graph_algo(['370', '330', '410', '390', '351'])
    app.create_new_graph_algo(dins[dins != None][:-2])
    app.close()
