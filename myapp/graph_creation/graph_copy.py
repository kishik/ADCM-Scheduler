import pandas as pd
from neo4j import Session

from myapp.graph_creation.utils import clear_database

Q_NODES_OBTAIN = """
MATCH (n)
RETURN n.name AS n_name, n.DIN AS n_din
"""
Q_NODES_CREATE = """
MERGE (s:Work {DIN: $n_din, name: $n_name})
"""
Q_RELS_OBTAIN = """
MATCH (n)-[r:FOLLOWS]->(m) 
RETURN n.DIN AS n_din, m.DIN AS m_din, properties(r).weight AS weight
"""
Q_RELS_CREATE = """
MATCH (n:Work)
WHERE n.DIN = $n_din
MATCH (m:Work)
WHERE m.DIN = $m_din
MERGE (n)-[r:FOLLOWS]->(m)
SET r.weight = coalesce(r.weight, 0) + 1;
"""


def graph_copy(in_session: Session, out_session: Session):
    # Clearing destination (output) database
    out_session.write_transaction(clear_database)

    node_df = pd.DataFrame(in_session.run(Q_NODES_OBTAIN).data())
    print(node_df.head())
    node_df.apply(lambda row: out_session.run(Q_NODES_CREATE, n_din=row["n_din"], n_name=row["n_name"]), axis=1)

    rel_df = pd.DataFrame(in_session.run(Q_RELS_OBTAIN).data())
    print(rel_df.head())
    rel_df.apply(
        lambda row: out_session.run(
            Q_RELS_CREATE,
            n_din=row["n_din"],
            m_din=row["m_din"],
            wght=row["weight"]
        ), axis=1
    )
