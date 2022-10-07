import numpy as np
import pandas as pd
from neo4j import GraphDatabase

import myapp.yml as yml


class Neo4jExplorer:
    def __init__(self):
        # read settings from config
        self.cfg: dict = yml.get_cfg('neo4j')
        _uri = self.cfg.get('new_url')
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
        q_delete = '''
            match (b)<-[r:FOLLOWS]-(a)-[:FOLLOWS]->(c)-[:FOLLOWS]->(b)
            delete r
            '''
        self.driver.session().run(q_delete)

    def add_pred_and_flw(self, data_to_order: pd.DataFrame):
        q_data_obtain = '''
        MATCH (n)-[]->(m)
        RETURN n.DIN AS n_id, m.DIN AS m_id
        '''
        data_to_order.drop(['Unnamed: 0'], axis=1, errors='ignore', inplace=True)
        data_to_order = data_to_order.astype('str')
        data_to_order['predecessors'] = ''
        data_to_order['followers'] = ''
        data_to_order['pred_vend'] = ''
        data_to_order['fol_vend'] = ''
        wbs2_arr = data_to_order.wbs2.unique()

        for i_wbs2 in wbs2_arr:
            wbs_df = data_to_order[data_to_order.wbs2 == i_wbs2]
            vendors = wbs_df.vendor_code.to_numpy()
            self.load_historical_graph()
            self.create_new_graph_algo(vendors)
            self.del_extra_rel()

            result = self.driver.session().run(q_data_obtain).data()
            df = pd.DataFrame(result)
            for vend in vendors:
                ind2 = wbs_df.index[wbs_df.vendor_code == vend].tolist()[0]
                flwDF = df.loc[df.n_id == vend]
                if not flwDF.empty:
                    flw_vends = flwDF.m_id.to_numpy()
                    flws = np.array([str(wbs_df.index[wbs_df.vendor_code == i].tolist()[0]) for i in flw_vends])
                    data_to_order.at[ind2, 'followers'] = ', '.join(flws)
                    data_to_order.at[ind2, 'fol_vend'] = ', '.join(flw_vends)

                predDF = df.loc[df.m_id == vend]
                if not predDF.empty:
                    pred_vends = predDF.n_id.to_numpy()
                    preds = np.array([str(wbs_df.index[wbs_df.vendor_code == i].tolist()[0]) for i in pred_vends])
                    data_to_order.at[ind2, 'predecessors'] = ', '.join(preds)
                    data_to_order.at[ind2, 'pred_vend'] = ', '.join(pred_vends)

        return data_to_order

