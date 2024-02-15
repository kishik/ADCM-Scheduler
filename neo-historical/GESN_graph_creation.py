import os
import logging

import numpy as np
import pandas as pd
from neo4j import GraphDatabase, Transaction

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

pd.options.mode.chained_assignment = None

GROUPS_URI = 'neo4j://neo4j_historical:7687'
# GROUPS_URI = 'neo4j://localhost:7688'


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


def main(location):
    logger.debug('Starting MAIN....')
    df = read_graph_data(location)
    print(df.head())
    logger.debug('Initializing NEO4j Driver....')
    driver = GraphDatabase.driver(
        GROUPS_URI,
        auth=("neo4j", "23109900")
    )
    with driver.session() as session:
        logger.debug('Inside Driver Session....')
        # session.execute_write(clear_database)
        session.execute_write(make_graph, df)
        session.run(
            "MATCH (n1)-[:EXECUTION]->(n2) "
            "WHERE not ()-->(n1) AND not (n2)-->() "
            "DETACH DELETE n1, n2"
        )
        q_del_4x_loop = """
                match (n1:Work)-->(n2:Work)-->(n3:Work)-->(n4:Work)-->(n1:Work)-->()
                detach delete n3, n4
                """
        q_del_3x_loop = """
                match (b:Work)<-[r]-(a:Work)-[]->(c:Work)-[]->(b:Work)
                delete r
                """
        q_del_2x_loop = """
                match (x:Work)-[]->(y:Work)-[]->(x:Work)
                detach delete y
                """
        q_del_1x_loop = """
                match (x:Work)-[r]->(x:Work)
                delete r
                """
        session.run(q_del_1x_loop)
        session.run(q_del_2x_loop)
        session.run(q_del_3x_loop)
        session.run(q_del_4x_loop)
        logger.debug("4x loops deleted")
    driver.close()


if __name__ == "__main__":
    print(os.getcwd())
    main("2022-02-07.xlsx")
