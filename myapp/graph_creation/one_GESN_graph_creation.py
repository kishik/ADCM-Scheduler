import numpy as np
from neo4j import GraphDatabase, Transaction
import pandas as pd

from myapp.graph_creation import yml

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
    DIN_lst = data.index.to_numpy()
    for wrk_DIN in DIN_lst:
        wrk_gesn = data.loc[wrk_DIN, 'ADCM_шифрГЭСН']
        tx.run("MERGE (a:Work {DIN: $DIN, name: $name})", DIN=wrk_gesn,
               name=wrk_gesn
               )
        s = data.loc[wrk_DIN, 'Последователи']
        if s == s:  # Проверка на то, что есть Последователи (s != NaN)
            followers = np.array(s.split(', '))
            for flw_DIN in np.intersect1d(followers, DIN_lst):
                flw_gesn = data.loc[flw_DIN, 'ADCM_шифрГЭСН']
                if flw_gesn != wrk_gesn:
                    tx.run('''MATCH (a:Work) WHERE a.DIN = $wrk_DIN
                           MERGE (f:Work {DIN: $flw_DIN, name: $flw_name})
                           MERGE (a)-[r:FOLLOWS]->(f)
                           SET r.weight = coalesce(r.weight, 0) + 1''',
                           wrk_DIN=wrk_gesn,
                           flw_DIN=flw_gesn,
                           flw_name=flw_gesn
                           )


def clear_database(tx: Transaction):
    tx.run('''MATCH (n)
           DETACH DELETE n''')


def main():
    df = read_graph_data("../data/2022-02-07 МОЭК_ЕКС график по смете.xlsx")
    df.drop_duplicates(keep='first', inplace=True)
    cfg = yml.get_cfg('neo4j')
    driver = GraphDatabase.driver(cfg.get('side_url'), auth=("neo4j", "231099"))
    with driver.session() as session:
        session.execute_write(clear_database)
        session.execute_write(make_graph, df)
    driver.close()


if __name__ == "__main__":
    main()
