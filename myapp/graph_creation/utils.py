import pandas as pd
from neo4j import Transaction
pd.options.mode.chained_assignment = None


def clear_database(tx: Transaction):
    tx.run("MATCH (n) "
           "DETACH DELETE n;"
           )


def delete_cycles(tx: Transaction):
    tx.run("MATCH (n)-[r]->(m)-[l]->(n) "
           "DELETE l;"
           )


def make_graph(tx: Transaction, data: pd.DataFrame) -> None:
    id_lst = data.index.tolist()
    for wrk_id in id_lst:
        din1 = data.loc[wrk_id, 'ADCM_DIN']
        tx.run("MERGE (a:Work {DIN: $din, name: $name});",
               din=din1,
               name=data.loc[wrk_id, 'name']
               )
        s = data.loc[wrk_id, 'Последователи']
        if s == s:  # Проверка на то, что есть Последователи (s != NaN)
            followers = s.split(', ')
            for flw_id in followers:
                if flw_id in id_lst:  # Создаем ребра только к вершинам, описанным в таблице отдельной строкой
                    din2 = data.loc[flw_id, 'ADCM_DIN']
                    if din1 != din2:
                        tx.run("MATCH (a:Work) WHERE a.DIN = $wrk_din "
                               "MERGE (flw:Work {DIN: $flw_din, name: $flw_name}) "
                               "MERGE (a)-[r:FOLLOWS]->(flw) "
                               "SET r.weight = coalesce(r.weight, 0) + 1",
                               wrk_din=din1,
                               flw_din=din2,
                               flw_name=data.loc[flw_id, 'name']
                               )

