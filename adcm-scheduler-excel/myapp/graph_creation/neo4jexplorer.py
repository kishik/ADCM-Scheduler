import pandas as pd
import logging
from neo4j import GraphDatabase

from myapp.graph_creation import utils, yml

logger = logging.getLogger(__name__)


class Neo4jExplorer:
    def __init__(self, uri=None, pswd=None):
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

        _user = self.cfg.get("user")

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

    def hist_graph_copy(self):
        _hist_uri = self.cfg.get("x2_url")
        _hist_user = self.cfg.get("user")
        _hist_pass = self.cfg.get("hist_password")
        logger.debug(f'Historical graph copy: {_hist_uri}')
        _hist_driver = GraphDatabase.driver(_hist_uri, auth=(_hist_user, _hist_pass))
        Q_NODES_OBTAIN = """
        MATCH (n)
        WHERE n.type = 'start'
        RETURN n.name AS n_name, n.DIN AS n_din
        """
        Q_NODES_CREATE = """
        MERGE (s:Work {DIN: $n_din, name: $n_name, type: 'start'})
        MERGE (f:Work {DIN: $n_din, name: $n_name, type: 'finish'})
        MERGE (s)-[r:EXECUTION {weight: 100}]->(f)
        """
        Q_RELS_OBTAIN = """
        MATCH (n)-[r:FOLLOWS]->(m) 
        RETURN n.DIN AS n_din, m.DIN AS m_din, properties(r).weight AS weight
        """
        Q_RELS_CREATE = """
        MATCH (n:Work)
        WHERE n.DIN = $n_din AND n.type = 'finish'
        MATCH (m:Work)
        WHERE m.DIN = $m_din AND m.type = 'start'
        MERGE (n)-[r:FOLLOWS]->(m)
        SET r.weight = coalesce(r.weight, 0) + 1;
        """

        with _hist_driver.session() as in_session:
            node_df = pd.DataFrame(in_session.run(Q_NODES_OBTAIN).data())
            rel_df = pd.DataFrame(in_session.run(Q_RELS_OBTAIN).data())

        with self.driver.session() as session:
            session.execute_write(utils.clear_database)
            logger.debug("local database cleared")
            node_df.apply(
                lambda row: session.run(Q_NODES_CREATE, n_din=row["n_din"], n_name=row["n_name"]),
                axis=1
            )

            rel_df.apply(
                lambda row: session.run(
                    Q_RELS_CREATE,
                    n_din=row["n_din"],
                    m_din=row["m_din"],
                    wght=row["weight"]
                ), axis=1
            )
            logger.debug("historical db copied to local")

    def removing_node(self, din: str):
        Q_PRED_FLW_OBTAIN = """
        MATCH (pred)-[:FOLLOWS]->(m)
            WHERE m.DIN = $din AND pred.type = 'finish'
        MATCH (n)-[:FOLLOWS]->(flw)
            WHERE n.DIN = $din AND flw.type = 'start'
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
                    MERGE (pred)-[r:FOLLOWS]->(flw)
                    SET r.weight = coalesce(r.weight, 1);
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
        RETURN n.DIN AS din
        """
        result = pd.DataFrame(self.driver.session().run(Q_DATA_OBTAIN).data())
        return result.din.unique()

    def create_new_graph_algo(self, target_ids):
        self.del_loops()
        for element in self.get_all_dins():
            if element not in target_ids:
                self.removing_node(element)

    def del_loops(self):
        q_del_4x_loop = """
        match (n1)-->(n2)-->(n3)-->(n4)-->(n1)-->()
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
        logger.debug("4x loops deleted")


if __name__ == "__main__":
    cfg: dict = yml.get_cfg("neo4j")

    # URL = cfg.get("url")
    # USER = cfg.get("user")
    # PASS = cfg.get("password")

    X2_URL = cfg.get("x2_url")
    X2_PASS = cfg.get("x2_password")

    app = Neo4jExplorer(uri=X2_URL, pswd=X2_PASS)
    # app.hist_graph_copy()
    app.create_new_graph_algo(
        ("3.47-3-20", "3.47-5-15", "3.47-3-15", "3.13-11-8", "3.18-20-4",
         "15.2-27-10", "4.8-75-3")
    )
    # print(app.get_all_dins())
    app.close()
