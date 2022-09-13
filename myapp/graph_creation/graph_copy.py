from neo4j import GraphDatabase, Transaction, Session

import pandas as pd

Q_DATA_OBTAIN = '''
    MATCH (n)-[r]->(m) 
    RETURN n.name AS n_name, n.DIN AS n_din, properties(r).weight AS weight, m.name AS m_name, m.DIN AS m_din
    '''
Q_CREATE = '''
    MERGE (n:Work {DIN: $n_din, name: $n_name})
    MERGE (m:Work {DIN: $m_din, name: $m_name})
    CREATE (n)-[r:FOLLOWS {weight: $wght}]->(m);
    '''


def clear_database(tx: Transaction):
    tx.run("MATCH (n) "
           "DETACH DELETE n;"
           )


def graph_copy(in_session: Session, out_session: Session):
    # Clearing destination (output) database
    out_session.write_transaction(clear_database)

    graph_df = pd.DataFrame(in_session.run(Q_DATA_OBTAIN).data())
    graph_df.apply(
        lambda row: out_session.run(
            Q_CREATE,
            n_din=row['n_din'], n_name=row['n_name'],
            m_din=row['m_din'], m_name=row['m_name'],
            wght=row['weight']
        ),
        axis=1
    )


def main():
    SRC_URI = "neo4j+s://178ff2cf.databases.neo4j.io:7687"
    SRC_USER = "neo4j"
    SRC_PSWD = "231099"
    DEST_URI = "neo4j+s://99c1a702.databases.neo4j.io"
    DEST_USER = "neo4j"
    DEST_PSWD = "231099"

    in_ses = GraphDatabase.driver(SRC_URI, auth=(SRC_USER, SRC_PSWD)).session()
    out_ses = GraphDatabase.driver(DEST_URI, auth=(DEST_USER, DEST_PSWD)).session()
    graph_copy(in_ses, out_ses)
    in_ses.close()
    out_ses.close()
