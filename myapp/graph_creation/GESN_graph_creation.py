import numpy as np
from neo4j import GraphDatabase, Transaction
import pandas as pd
pd.options.mode.chained_assignment = None


def read_graph_data(file_name: str) -> pd.DataFrame:
    df = pd.read_excel(file_name)
    df.drop_duplicates(keep='first', inplace=True)
    graph_data = df[['Идентификатор операции', 'Наименование', 'ADCM_шифрГЭСН', 'Последователи']]
    graph_data.loc[:, 'Идентификатор операции'] = graph_data['Идентификатор операции'].apply(str.strip)
    graph_data = graph_data[graph_data['Идентификатор операции'].str.startswith('A')]
    graph_data.set_index('Идентификатор операции', inplace=True)  # Update indeces
    return graph_data


def make_graph(tx: Transaction, data: pd.DataFrame):
    id_lst = data.index.to_numpy()
    for wrk_id in id_lst:
        wrk_gesn = data.loc[wrk_id, 'ADCM_шифрГЭСН']
        wrk_name = data.loc[wrk_id, 'Наименование']
        add_node(tx, wrk_gesn, wrk_name)

        f = wrk_gesn == '2.1-3-38'
        if f:
            print(wrk_gesn)

        s = data.loc[wrk_id, 'Последователи']
        if s == s:  # Проверка на то, что есть Последователи (s != NaN)
            followers = np.array(s.split(', '))
            for flw_id in np.intersect1d(followers, id_lst):
                flw_gesn = data.loc[flw_id, 'ADCM_шифрГЭСН']
                if f:
                    print(flw_gesn)
                if flw_gesn != wrk_gesn:
                    add_edge(tx, wrk_gesn, flw_gesn, 'ФС')


def add_node(tx: Transaction, din: str, name: str) -> None:
    Q_CREATE_NODE = '''
        MERGE (s:Work {DIN: $n_din, name: $n_name, type: 'start'})
        MERGE (f:Work {DIN: $n_din, name: $n_name, type: 'finish'})
        MERGE (s)-[r:EXCECUTION {weight: 100}]->(f)
        '''
    tx.run(Q_CREATE_NODE, n_din=din, n_name=name)


def add_edge(tx: Transaction, pred_din: str, flw_din: str, rel_type: str) -> None:
    if rel_type == 'ФС':
        pred_type = 'finish'
        flw_type = 'start'
    elif rel_type == 'СС':
        pred_type = flw_type = 'start'
    elif rel_type == 'ФФ':
        pred_type = flw_type = 'finish'
    else:
        pred_type = 'start'
        flw_type = 'finish'
    Q_CREATE_REL = '''
    MATCH (n:Work)
    WHERE n.DIN = $din1 AND n.type = $type1
    MATCH (m:Work)
    WHERE m.DIN = $din2 AND m.type = $type2
    MERGE (n)-[r:FOLLOWS]->(m)
    SET r.weight = coalesce(r.weight, 0) + 1;
        '''
    tx.run(Q_CREATE_REL, din1=pred_din, din2=flw_din, type1=pred_type, type2=flw_type)


def clear_database(tx: Transaction):
    tx.run('''MATCH (n)
           DETACH DELETE n''')


def main():
    df = read_graph_data("../data/2022-02-07 МОЭК_ЕКС график по смете.xlsx")
    df.drop_duplicates(keep='first', inplace=True)

    driver = GraphDatabase.driver("neo4j+s://99c1a702.databases.neo4j.io", auth=("neo4j", "231099"))
    with driver.session() as session:
        session.write_transaction(clear_database)
        session.write_transaction(make_graph, df)
    driver.close()


if __name__ == "__main__":
    main()
