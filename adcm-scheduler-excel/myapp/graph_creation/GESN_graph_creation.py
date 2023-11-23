import os

import numpy as np
from neo4j import GraphDatabase, Transaction
import pandas as pd

from myapp.graph_creation import yml
from myapp.graph_creation.graph_copy import graph_copy
from myapp.graph_creation.neo4jexplorer import Neo4jExplorer

pd.options.mode.chained_assignment = None
cfg = yml.get_cfg("neo4j")


def read_graph_data(file_name: str) -> pd.DataFrame:
    df = pd.read_excel(file_name)
    df.drop_duplicates(inplace=True)
    graph_data = df[['Идентификатор операции', 'Наименование', 'ADCM_шифрГЭСН', 'Последователи']]
    graph_data.loc[:, 'Идентификатор операции'] = graph_data['Идентификатор операции'].apply(str.strip)
    graph_data = graph_data[graph_data['Идентификатор операции'].str.startswith('A')]
    graph_data.set_index('Идентификатор операции', inplace=True)  # Update indeces
    graph_data.drop_duplicates(inplace=True)
    return graph_data


def make_graph(tx: Transaction, data: pd.DataFrame):
    id_lst = data.index.to_numpy()
    for wrk_id in id_lst:
        wrk_gesn = data.loc[wrk_id, 'ADCM_шифрГЭСН']
        wrk_name = data.loc[wrk_id, 'Наименование']
        add_node(tx, wrk_gesn, wrk_name)

        s = data.loc[wrk_id, 'Последователи']
        if s == s:  # Проверка на то, что есть Последователи (s != NaN)
            followers = np.array(s.split(', '))
            for flw_id in np.intersect1d(followers, id_lst):
                flw_gesn = data.loc[flw_id, 'ADCM_шифрГЭСН']

                if flw_gesn != wrk_gesn:
                    add_edge(tx, wrk_gesn, flw_gesn, 'ФС')


def add_node(tx: Transaction, din: str, name: str) -> None:
    Q_CREATE_NODE = '''
        MERGE (s:Work {DIN: $n_din, name: $n_name, type: 'start'})
        MERGE (f:Work {DIN: $n_din, name: $n_name, type: 'finish'})
        MERGE (s)-[r:EXECUTION {weight: 100}]->(f)
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
    tx.run("MATCH (n) DETACH DELETE n;")


def gesn_upload(file):
    df1 = pd.read_excel(file)
    df1.rename(
        columns={"Проект": "wbs1", "Смета": "wbs2", "Шифр": "wbs3_id", "Наименование": "name"},
        inplace=True
    )
    df1 = df1[["wbs1", "wbs2", "wbs3_id", "name"]]
    df1.dropna(subset=["wbs3_id"], inplace=True)
    df1.drop_duplicates(inplace=True)

    HIST_URI = cfg.get("x2_url")
    LOCAL_URI = cfg.get("url")
    USER = cfg.get("user")
    PSWD = cfg.get("password")
    hist_driver = GraphDatabase.driver(HIST_URI, auth=(USER, PSWD))
    local_driver = GraphDatabase.driver(LOCAL_URI, auth=(USER, cfg.get("password")))
    graph_copy(hist_driver.session(), local_driver.session())

    app = Neo4jExplorer(uri=LOCAL_URI)
    hist_gesns = app.get_all_dins()
    input_gesns = df1.wbs3_id.unique()
    targ_gesns = np.intersect1d(hist_gesns, input_gesns)
    app.create_new_graph_algo(targ_gesns)


def main(location):
    df = read_graph_data(location)
    driver = GraphDatabase.driver(cfg.get("x2_url"), auth=(cfg.get("user"), cfg.get("password")))
    with driver.session() as session:
        session.execute_write(clear_database)
        session.execute_write(make_graph, df)
        session.run(
            "MATCH (n1)-[:EXECUTION]->(n2) "
            "WHERE size(()-->(n1))=0 AND size((n2)-->())=0 "
            "DETACH DELETE n1, n2"
        )
    driver.close()


if __name__ == "__main__":
    main("../data/2022-02-07 МОЭК_ЕКС график по смете.xlsx")
