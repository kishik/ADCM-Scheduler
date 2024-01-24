import pandas as pd
from neo4j import Session

from myapp.graph_creation import utils

pd.options.mode.chained_assignment = None


def node(session: Session, node_din: str, node_name: str) -> None:
    Q_ADD_NODE = """MERGE (s:Work {DIN: $n_din, name: $n_name, type: 'start'})
    MERGE (f:Work {DIN: $n_din, name: $n_name, type: 'finish'})
    MERGE (s)-[r:EXECUTION {weight: 100}]->(f)
    """
    session.run(Q_ADD_NODE, n_din=node_din, n_name=node_name)


def edge(session: Session, pred_din: str, flw_din: str, weight: int = 1) -> None:
    Q_ADD_REL = """MATCH (n:Work)
    WHERE n.DIN = $din1 AND n.type = 'finish'
    MATCH (m:Work)
    WHERE m.DIN = $din2 AND m.type = 'start'
    MERGE (n)-[r:FOLLOWS]->(m)
    SET r.weight = toInteger(coalesce(r.weight, 0)) + toInteger($wght);
    """
    session.run(Q_ADD_REL, din1=pred_din, din2=flw_din, wght=weight)


def from_one_file(session: Session, path: str) -> None:
    data = pd.read_excel(
        path,
        dtype=str,
        usecols="A,B,E,F,J",
        index_col=0,
    )
    data.drop_duplicates(keep="last", subset=["ADCM_DIN", "ADCM_Level", "Последователи"], inplace=True)
    data.dropna(subset=["ADCM_DIN", "ADCM_Level"], inplace=True)
    din_df = pd.read_excel(
        "myapp/data/DIN.xlsx",
        dtype={"DIN": str},
        usecols=[0, 4],
    )

    # adjusting name to each DIN
    din_df.set_index("DIN", inplace=True)
    din_to_name = din_df.Operation.to_dict()
    data["name"] = data.apply(lambda row: din_to_name.get(row["ADCM_DIN"], "Не задано"), axis=1)

    session.execute_write(utils.clear_database)
    session.execute_write(utils.make_old_graph, data)
    session.execute_write(utils.delete_cycles)

# def from_two_files(session: Session, node_file_path: str, edge_file_path: str) -> None:
#     pass
