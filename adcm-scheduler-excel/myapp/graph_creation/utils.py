import pandas as pd
from neo4j import Transaction

pd.options.mode.chained_assignment = None


def clear_database(tx: Transaction):
    tx.run("MATCH (n) " "DETACH DELETE n;")


def delete_cycles(tx: Transaction):
    tx.run("MATCH (n)-[r]->(m)-[l]->(n) " "DELETE l;")


def make_old_graph(tx: Transaction, data: pd.DataFrame) -> None:
    id_lst = data.index.tolist()
    for wrk_id in id_lst:
        din1 = data.loc[wrk_id, "ADCM_DIN"]
        tx.run("MERGE (a:Work {DIN: $din, name: $name});", din=din1, name=data.loc[wrk_id, "name"])
        s = data.loc[wrk_id, "Последователи"]
        if s == s:  # Проверка на то, что есть Последователи (s != NaN)
            followers = s.split(", ")
            for flw_id in followers:
                if flw_id in id_lst:  # Создаем ребра только к вершинам, описанным в таблице отдельной строкой
                    din2 = data.loc[flw_id, "ADCM_DIN"]
                    if din1 != din2:
                        tx.run(
                            "MATCH (a:Work) WHERE a.DIN = $wrk_din "
                            "MERGE (flw:Work {DIN: $flw_din, name: $flw_name}) "
                            "MERGE (a)-[r:FOLLOWS]->(flw) "
                            "SET r.weight = coalesce(r.weight, 0) + 1",
                            wrk_din=din1,
                            flw_din=din2,
                            flw_name=data.loc[flw_id, "name"],
                        )


def add_double_node(tx: Transaction, din: str, name: str) -> None:
    Q_CREATE_NODE = """
        MERGE (s:Work {DIN: $n_din, name: $n_name, type: 'start'})
        MERGE (f:Work {DIN: $n_din, name: $n_name, type: 'finish'})
        MERGE (s)-[r:EXECUTION {weight: 100}]->(f)
        """
    tx.run(Q_CREATE_NODE, n_din=din, n_name=name)


def add_typed_edge(tx: Transaction, pred_din: str, flw_din: str, rel_type: str) -> None:
    if rel_type == "ФС":
        pred_type = "finish"
        flw_type = "start"
    elif rel_type == "СС":
        pred_type = flw_type = "start"
    elif rel_type == "ФФ":
        pred_type = flw_type = "finish"
    elif rel_type == "СФ":
        pred_type = "start"
        flw_type = "finish"
    Q_CREATE_REL = f"""
        MATCH (n:Work)
        WHERE n.DIN = $din1 AND n.type = $type1
        MATCH (m:Work)
        WHERE m.DIN = $din2 AND m.type = $type2
        MERGE (n)-[r:FOLLOWS {{weight: 1}}]->(m);
        """
    tx.run(Q_CREATE_REL, din1=pred_din, din2=flw_din, type1=pred_type, type2=flw_type)
