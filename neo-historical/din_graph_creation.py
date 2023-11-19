from neo4j import GraphDatabase, Transaction, Session
import pandas as pd

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
        if din1 == din1:
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
                    if din1 != din2 and din1 == din1 and din2 == din2:
                        tx.run("MATCH (a:Work) WHERE a.DIN = $wrk_din "
                               "MERGE (flw:Work {DIN: $flw_din, name: $flw_name}) "
                               "MERGE (a)-[r:FOLLOWS]->(flw) "
                               "SET r.weight = coalesce(r.weight, 0) + 1",
                               wrk_din=din1,
                               flw_din=din2,
                               flw_name=data.loc[flw_id, 'name']
                               )


def din_graph_cgeation():
    data = pd.read_excel(
        'Sinara.xlsx',
        dtype=str,
        usecols='A,B,E,F,J',
        index_col=0,
    )
    level_df = data.drop_duplicates(
        keep='last',
        subset=['ADCM_DIN', 'ADCM_Level', 'Последователи']
    )

    din_df = pd.read_excel('DIN.xlsx',
                           dtype={'DIN': str},
                           usecols=[0, 4],
                           )
    din_df.set_index('DIN', inplace=True)
    din_to_name: dict = din_df.Operation.to_dict()

    level_df['name'] = level_df.apply(
        lambda row: din_to_name.get(row['ADCM_DIN'], 'Не задано'),
        axis=1
    )

    driver = GraphDatabase.driver(
        "bolt://neo4j_historical:7687",
        auth=("neo4j", "23109900")
    )
    with driver.session() as session:
        session.execute_write(clear_database)
        session.execute_write(make_graph, level_df)
        session.execute_write(delete_cycles)
    driver.close()


if __name__ == "__main__":
    din_graph_cgeation()
