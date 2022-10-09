from myapp.graph_creation import utils
from neo4j import Session
import pandas as pd
pd.options.mode.chained_assignment = None


def node(session: Session, node_din: str, node_name: str) -> None:
    Q_ADD_NODE = "MERGE (a:Work {DIN: $din, name: $name});"
    session.run(Q_ADD_NODE, din=node_din, name=node_name)


def edge(session: Session, pred_din: str, flw_din: str, weight: int) -> None:
    Q_ADD_REL = '''
        MATCH (a:Work) WHERE a.DIN = $din1 
        MATCH (b:Work) WHERE b.DIN = $din2
        MERGE (a)-[r:FOLLOWS {weight: $wght}]->(b);
        '''
    session.run(Q_ADD_REL, din1=pred_din, din2=flw_din, wght=weight)


def from_one_file(session: Session, path: str) -> None:
    data = pd.read_excel(path,
                         dtype=str,
                         usecols='A,B,E,F,J',
                         index_col=0,
                         )
    data.drop_duplicates(keep='last',
                         subset=['ADCM_DIN', 'ADCM_Level', 'Последователи'],
                         inplace=True
                         )
    data.dropna(subset=['ADCM_DIN', 'ADCM_Level'], inplace=True)
    din_df = pd.read_excel("myapp/data/DIN.xlsx",
                           dtype={'DIN': str},
                           usecols=[0, 4],
                           )

    # adjusting name to each DIN
    din_df.set_index('DIN', inplace=True)
    din_to_name = din_df.Operation.to_dict()
    data['name'] = data.apply(
        lambda row: din_to_name.get(row['ADCM_DIN'], 'Не задано'),
        axis=1
    )

    session.execute_write(utils.clear_database)
    session.execute_write(utils.make_old_graph, data)
    session.execute_write(utils.delete_cycles)


def from_two_files(session: Session, node_file_path: str, edge_file_path: str) -> None:
    pass