import numpy as np
from neo4j import GraphDatabase, Transaction
import pandas as pd


def read_graph_data(file_name: str) -> pd.DataFrame:
    df = pd.read_excel(file_name)
    df.drop_duplicates(keep='first', inplace=True)
    graph_data = df[['Идентификатор операции', 'ADCM_шифрГЭСН', 'Последователи']]
    graph_data.loc[:, 'Идентификатор операции'] = graph_data['Идентификатор операции'].apply(str.strip)
    graph_data = graph_data[graph_data['Идентификатор операции'].str.startswith('A')]
    graph_data.set_index('Идентификатор операции', inplace=True)  # Update indeces
    return graph_data


def make_graph(tx: Transaction, data: pd.DataFrame):
    id_lst = data.index.to_numpy()
    for wrk_id in id_lst:
        wrk_gesn = data.loc[wrk_id, 'ADCM_шифрГЭСН']
        tx.run("MERGE (a:Work {id: $id, name: $name})", id=wrk_gesn,
               name=wrk_gesn
               )
        s = data.loc[wrk_id, 'Последователи']
        if s == s:  # Проверка на то, что есть Последователи (s != NaN)
            followers = np.array(s.split(', '))
            for flw_id in np.intersect1d(followers, id_lst):
                # print(data.loc[flw_id])
                # print()
                flw_gesn = data.loc[flw_id, 'ADCM_шифрГЭСН']
                print(wrk_id, wrk_gesn)
                print(flw_id, flw_gesn)
                print()
                if flw_gesn != wrk_gesn:
                    tx.run('''MATCH (a:Work) WHERE a.id = $wrk_id
                           MERGE (f:Work {id: $flw_id, name: $flw_name})
                           MERGE (a)-[r:FOLLOWS]->(f)
                           SET r.weight = coalesce(r.weight, 0) + 1''',
                           wrk_id=wrk_gesn,
                           flw_id=flw_gesn,
                           flw_name=flw_gesn
                           )


def clear_database(tx: Transaction):
    tx.run('''MATCH (n)
           DETACH DELETE n''')


def main():
    df = read_graph_data("../data/2022-02-07 МОЭК_ЕКС график по смете.xlsx")
    df.drop_duplicates(keep='first', inplace=True)
    # gesn = df['ADCM_шифрГЭСН'].unique()
    # df1 = df[df['ADCM_шифрГЭСН'] == gesn[0]]
    # print(df1)
    # print(type(gesn))
    # driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "2310"))
    # driver = GraphDatabase.driver("neo4j+s://174cd36c.databases.neo4j.io:7687", auth=("neo4j", "w21V4bw-6kTp9hceHMbnlt5L9X1M4upuuq2nD7tD_xU"))
    driver = GraphDatabase.driver("neo4j://127.0.0.1:7688", auth=("neo4j", "23109900"))
    with driver.session() as session:
        session.write_transaction(clear_database)
        session.write_transaction(make_graph, df)
    driver.close()