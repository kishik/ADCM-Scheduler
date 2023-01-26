import pandas as pd
from neo4j import Session, Transaction

Q_NODES_OBTAIN = """
    MATCH (n)
    RETURN n.name AS n_name, n.DIN AS n_din
    """
Q_NODES_CREATE = """
    MERGE (n:Work {DIN: $n_din, name: $n_name})
    """
Q_RELS_OBTAIN = """
    MATCH (n)-[r]->(m) 
    RETURN n.DIN AS n_din, m.DIN AS m_din, properties(r).weight AS weight
    """
Q_RELS_CREATE = """
    MATCH (n)
    WHERE n.DIN = $n_din
    MATCH (m)
    WHERE m.DIN = $m_din
    MERGE (n)-[r:FOLLOWS {weight: $wght}]->(m);
    """


def clear_database(tx: Transaction):
    tx.run("MATCH (n) " "DETACH DELETE n;")


def graph_copy(in_session: Session, out_session: Session):
    # Clearing destination (output) database
    out_session.write_transaction(clear_database)

    node_df = pd.DataFrame(in_session.run(Q_NODES_OBTAIN).data())
    node_df.apply(lambda row: out_session.run(Q_NODES_CREATE, n_din=row["n_din"], n_name=row["n_name"]), axis=1)

    rel_df = pd.DataFrame(in_session.run(Q_RELS_OBTAIN).data())
    rel_df.apply(
        lambda row: out_session.run(Q_RELS_CREATE, n_din=row["n_din"], m_din=row["m_din"], wght=row["weight"]), axis=1
    )
