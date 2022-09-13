import pandas as pd
from neo4j import GraphDatabase, Transaction
import numpy as np
import datetime
import myapp.yml as yml


class Neo4jExplorer:
    def __init__(self):
        # read settings from config
        self.cfg: dict = yml.get_cfg("neo4j")
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

        q_data_obtain = '''
            MATCH (n)-[r]->(m)
            RETURN n.name AS n_name, n.id AS n_id, properties(r).weight AS weight, m.name AS m_name, m.id AS m_id
            '''
        lnk = self.cfg.get('hist_link')
        q_create = f'''
            LOAD CSV WITH HEADERS FROM '{lnk}' AS row
            MERGE (n:Work {{id: row.n_id, name: row.n_name}})
            MERGE (m:Work {{id: row.m_id, name: row.m_name}})
            CREATE (n)-[r:FOLLOWS {{weight: row.weight}}]->(m);
            '''

        # obtaining data
        result = _hist_driver.session().run(q_data_obtain).data()
        _hist_driver.close()

        # to do: делать нормальную передачу CSV-файла
        df = pd.DataFrame(result)
        save_path = ''
        df.to_csv(save_path + 'data.csv', index=False)
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")  # Предварительная очистка базы данных
            session.run(q_create)

    def removing_node(self, id: str):
        income_data_obtain = '''
            MATCH (n)-[]->(m)
            WHERE m.id = $id
            RETURN n
            '''
        outcome_data_obtain = '''
            MATCH (n)-[]->(m)
            WHERE n.id = $id
            RETURN m
            '''
        with self.driver.session() as session:
            incoming = session.run(income_data_obtain, id=id).data()
            outcoming = session.run(outcome_data_obtain, id=id).data()
            # преобразование результатов запроса в numpy.array
            incoming = np.array([row['n']['id'] for row in incoming])
            outcoming = np.array([row['m']['id'] for row in outcoming])

            for element in incoming:
                for subelement in outcoming:
                    session.run('''
                                        MERGE (n:Work {id: $id1})
                                        MERGE (m:Work {id: $id2})
                                        MERGE (n)-[r:FOLLOWS]->(m)
                                        ''',
                                id1=element,
                                id2=subelement
                                )
            session.run("MATCH (n) WHERE n.id = $id DETACH DELETE n", id=id)

    def get_all_id(self):
        q_data_obtain = '''
            MATCH (n)
            RETURN n
            '''
        result = self.driver.session().run(q_data_obtain).data()
        id_lst = []
        for i in result:
            id_lst.append((i['n']['id']))
        return list(set(id_lst))

    def create_new_graph_algo(self, target_ids: list):
        for element in self.get_all_id():
            if element not in target_ids:
                self.removing_node(element)

    def del_extra_rel(self):
        q_delete = '''
            match (b)<-[r]-(a)-->(c)-->(b)
            delete r
            '''
        self.driver.session().run(q_delete)

    def add_pred_and_flw(self, data_to_order: pd.DataFrame):
        q_data_obtain = '''
        MATCH (n)-[]->(m)
        RETURN n.id AS n_id, m.id AS m_id
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


def main():
    starttime = datetime.datetime.now()

    file_path = 'data/solution_schedule.xlsx'
    workingDF = pd.read_excel(file_path, sheet_name="Состав работ", dtype=str, index_col=0)

    app = Neo4jExplorer()
    resultDF = app.add_pred_and_flw(workingDF)
    print(app.cfg.get('hist_link'))
    app.close()

    with pd.ExcelWriter('data/result_ordered.xlsx', engine='openpyxl') as writer:
        resultDF.to_excel(writer, sheet_name="Упорядоченно")
    print('data ordered', datetime.datetime.now() - starttime)


if __name__ == "__main__":
    main()