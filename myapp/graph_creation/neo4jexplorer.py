import pandas as pd
from neo4j import GraphDatabase

from myapp.graph_creation import utils, yml


class Neo4jExplorer:
    def __init__(self, uri=None):
        # read settings from config
        self.cfg: dict = yml.get_cfg("neo4j")
        if not uri:
            _uri = self.cfg.get("new_url")
        else:
            _uri = uri
        _user = self.cfg.get("new_user")
        _pswd = self.cfg.get("new_password")

        self.driver = GraphDatabase.driver(_uri, auth=(_user, _pswd))

    def close(self):
        # Don't forget to close the driver connection when you are finished with it
        self.driver.close()

    def load_historical_graph(self):
        # driver to historical database
        _hist_uri = self.cfg.get("url")
        _hist_user = self.cfg.get("user")
        _hist_pass = self.cfg.get("password")
        _hist_driver = GraphDatabase.driver(_hist_uri, auth=(_hist_user, _hist_pass))

        Q_DATA_OBTAIN = """
            MATCH (n)-[r]->(m)
            RETURN n.name AS n_name, n.DIN AS n_id, properties(r).weight AS weight, m.name AS m_name, m.DIN AS m_id
            """
        lnk = self.cfg.get("hist_link")
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

    def removing_node(self, din: str):
        Q_PRED_FLW_OBTAIN = """
        MATCH (pred)-[:FOLLOWS]->(m)
            WHERE m.DIN = $din
        MATCH (n)-[:FOLLOWS]->(flw)
            WHERE n.DIN = $din
        RETURN pred.DIN AS pred_din, pred.type AS pred_type, 
            flw.DIN AS flw_din, flw.type AS flw_type
        """
        with self.driver.session() as session:
            result_df = pd.DataFrame(session.run(Q_PRED_FLW_OBTAIN, din=din).data())
            result_df.apply(
                lambda row: session.run(
                    """
                    MATCH (n)
                    WHERE n.DIN = $din1 AND n.type = $type1
                    MATCH (m)
                    WHERE m.DIN = $din2 AND m.type = $type2
                    MERGE (n)-[r:FOLLOWS]->(m)
                    SET r.weight = coalesce(r.weight, 1);
                    """,
                    din1=row.pred_din,
                    type1=row.pred_type,
                    din2=row.flw_din,
                    type2=row.flw_type,
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
        for element in self.get_all_dins():
            if element not in target_ids:
                self.removing_node(element)
        # self.del_extra_rel()

    def del_extra_rel(self):
        Q_DELETE = """
            match (b)<-[r:FOLLOWS]-(a)-[:FOLLOWS]->(c)-[:FOLLOWS]->(b)
            delete r
            """
        self.driver.session().run(Q_DELETE)

    def restore_graph(self):
        LNK_NODES = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQvNoXaiLn2YlT_LFi0NUmA-Igumgoi5Puh-gXvBgaOeNoaoFAWwqjt-G6zMUvrhTNcndUmTdP7qpaT/pub?output=csv"
        Q_CREATE_NODES = f"""
        LOAD CSV WITH HEADERS FROM '{LNK_NODES}' AS row
        MERGE (s:Work {{DIN: row.din, name: row.name, type: 'start'}})
        MERGE (f:Work {{DIN: row.din, name: row.name, type: 'finish'}})
        MERGE (s)-[r:EXCECUTION {{weight: 100}}]->(f);
        """
        LNK_EDGES = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR4ki-Hhz8IAostBONk2eAMW-lL3uLlvwF174w9qeQ420RBTDy2B4QJqkF9cILahG_ufTeZMVlndBde/pub?output=csv"
        Q_CREATE_RELS = f"""
        LOAD CSV WITH HEADERS FROM '{LNK_EDGES}' AS row
        MERGE (n:Work {{DIN: row.n_din, type: row.n_type}})
        MERGE (m:Work {{DIN: row.m_din, type: row.m_type}})
        MERGE (n)-[r:FOLLOWS {{weight: row.weight}}]->(m);
        """
        with self.driver.session() as session:
            session.execute_write(utils.clear_database)
            session.run(Q_CREATE_NODES)
            session.run(Q_CREATE_RELS)


if __name__ == "__main__":
    app = Neo4jExplorer()
    app.restore_graph()  # Only if you need to restore your graph
    app.create_new_graph_algo(["329", "3421", "369"])
    app.close()
