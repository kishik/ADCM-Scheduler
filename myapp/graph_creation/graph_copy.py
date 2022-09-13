from neo4j import GraphDatabase, Transaction, Session

import pandas as pd

Q_NODES_OBTAIN = '''
    MATCH (n)-[r]->(m) 
    RETURN n.name AS n_name, n.DIN AS n_din
    '''
Q_NODES_CREATE = '''
    MERGE (n:Work {DIN: $n_din, name: $n_name})
    '''
Q_RELS_OBTAIN = '''
    MATCH (n)-[r]->(m) 
    RETURN n.DIN AS n_din, m.DIN AS m_din, properties(r).weight AS weight
    '''
Q_RELS_CREATE = '''
    MATCH (n)
    WHERE n.DIN = $n_din
    MATCH (m)
    WHERE m.DIN = $m_din
    MERGE (n)-[r:FOLLOWS {weight: $wght}]->(m);
    '''


def clear_database(tx: Transaction):
    tx.run("MATCH (n) "
           "DETACH DELETE n;"
           )


def graph_copy(in_session: Session, out_session: Session):
    # Clearing destination (output) database
    out_session.write_transaction(clear_database)

    node_df = pd.DataFrame(in_session.run(Q_NODES_OBTAIN).data())
    node_df.apply(
        lambda row: out_session.run(
            Q_NODES_CREATE,
            n_din=row['n_din'], n_name=row['n_name']
        ),
        axis=1
    )

    rel_df = pd.DataFrame(in_session.run(Q_RELS_OBTAIN).data())
    rel_df.apply(
        lambda row: out_session.run(
            Q_RELS_CREATE,
            n_din=row['n_din'], m_din=row['m_din'], wght=row['weight']
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


if __name__ == "__main__":
    main()
