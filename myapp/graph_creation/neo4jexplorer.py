import pandas as pd
from neo4j import GraphDatabase

import myapp.yml as yml
from myapp.graph_creation import utils


class Neo4jExplorer:
    def __init__(self, uri=None):
        # read settings from config
        self.cfg: dict = yml.get_cfg('neo4j')
        if not uri:
            _uri = self.cfg.get('new_url')
        else:
            _uri = uri
        _user = self.cfg.get('new_user')
        _pass = self.cfg.get('new_password')

        self.driver = GraphDatabase.driver(_uri, auth=(_user, _pass))

    def close(self):
        # Don't forget to close the driver connection when you are finished with it
        self.driver.close()

    def load_historical_graph(self):
        # driver to historical database
        _hist_uri = self.cfg.get('url')
        _hist_user = self.cfg.get('user')
        _hist_pass = self.cfg.get('password')
        _hist_driver = GraphDatabase.driver(_hist_uri, auth=(_hist_user, _hist_pass))

        Q_DATA_OBTAIN = '''
            MATCH (n)-[r]->(m)
            RETURN n.name AS n_name, n.DIN AS n_id, properties(r).weight AS weight, m.name AS m_name, m.DIN AS m_id
            '''
        lnk = self.cfg.get('hist_link')
        Q_CREATE = f'''
            LOAD CSV WITH HEADERS FROM '{lnk}' AS row
            MERGE (n:Work {{DIN: row.n_id, name: row.n_name}})
            MERGE (m:Work {{DIN: row.m_id, name: row.m_name}})
            CREATE (n)-[r:FOLLOWS {{weight: row.weight}}]->(m);
            '''

        # obtaining data
        result = _hist_driver.session().run(Q_DATA_OBTAIN).data()
        _hist_driver.close()

        # to do: cделать нормальную передачу CSV-файла
        df = pd.DataFrame(result)
        save_path = ''
        df.to_csv(save_path + 'data.csv', index=False)
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")  # Предварительная очистка базы данных
            session.run(Q_CREATE)

    def removing_node(self, din: str):
        Q_PRED_OBTAIN = '''
            MATCH (n)-[:FOLLOWS]->(m)
            WHERE m.DIN = $din
            RETURN n.DIN AS din, n.type AS type
            '''
        Q_FLW_OBTAIN = '''
            MATCH (n)-[:FOLLOWS]->(m)
            WHERE n.DIN = $din
            RETURN m.DIN AS din, m.type AS type
            '''
        with self.driver.session() as session:
            in_df = pd.DataFrame(session.run(Q_PRED_OBTAIN, din=din).data())
            out_df = pd.DataFrame(session.run(Q_FLW_OBTAIN, din=din).data())

            for _, pred_row in in_df.iterrows():
                for _, flw_row in out_df.iterrows():
                    session.run(
                        '''
                        MATCH (n)
                        WHERE n.DIN = $din1 AND n.type = $type1
                        MATCH (m)
                        WHERE m.DIN = $din2 AND m.type = $type2
                        MERGE (n)-[r:FOLLOWS]->(m)
                        SET r.weight = coalesce(r.weight, 1);
                        ''',
                        din1=pred_row.din, type1=pred_row.type,
                        din2=flw_row.din, type2=flw_row.type,
                    )
            session.run("MATCH (n) WHERE n.DIN = $din DETACH DELETE n", din=din)

    def get_all_dins(self):
        Q_DATA_OBTAIN = '''
        MATCH (n)
        RETURN n.DIN AS din
        '''
        result = pd.DataFrame(self.driver.session().run(Q_DATA_OBTAIN).data())
        return result.din.unique()

    def create_new_graph_algo(self, target_ids):
        for element in self.get_all_dins():
            if element not in target_ids:
                self.removing_node(element)

    def del_extra_rel(self):
        Q_DELETE = '''
            match (b)<-[r:FOLLOWS]-(a)-[:FOLLOWS]->(c)-[:FOLLOWS]->(b)
            delete r
            '''
        self.driver.session().run(Q_DELETE)

    def restore_graph(self):
        node_df = pd.read_excel('myapp/data/DIN-1.xlsx',
                                dtype=str,
                                usecols=[0, 3],
                                skiprows=[1])
        edge_df = pd.read_excel('myapp/data/DIN-2.xlsx',
                                dtype=str,
                                usecols=[0, 1, 2],
                                skiprows=[1])
        with self.driver.session() as session:
            session.execute_write(utils.clear_database)
            node_df.apply(
                lambda row: session.execute_write(
                    utils.add_double_node,
                    row.task_code, row.task_name
                ),
                axis=1
            )
            edge_df.apply(
                lambda row: session.execute_write(
                    utils.add_typed_edge,
                    row.pred_task_id, row.task_id, row.pred_type
                ),
                axis=1
            )


if __name__ == "__main__":
    app = Neo4jExplorer()
    app.restore_graph()  # Only if you need to restore your graph
    app.create_new_graph_algo(['329', '3421', '369'])
    app.del_extra_rel()
    app.close()
