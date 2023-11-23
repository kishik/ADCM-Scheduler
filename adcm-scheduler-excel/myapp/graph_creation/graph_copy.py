import pandas as pd
from neo4j import Session
import logging
from myapp.graph_creation.utils import clear_database

Q_NODES_OBTAIN = """
MATCH (n)
WHERE n.type = 'start'
RETURN n.name AS n_name, n.DIN AS n_din
"""
Q_NODES_CREATE = """
MERGE (s:Work {DIN: $n_din, name: $n_name, type: 'start'})
MERGE (f:Work {DIN: $n_din, name: $n_name, type: 'finish'})
MERGE (s)-[r:EXECUTION {weight: 100}]->(f)
"""
Q_RELS_OBTAIN = """
RETURN n.type AS pred_type 
RETURN n.DIN AS n_din, m.DIN AS m_din, properties(r).weight AS weight
"""
Q_RELS_CREATE = """
MATCH (n:Work)
WHERE n.DIN = $n_din AND n.type = 'finish'
MATCH (m:Work)
WHERE m.DIN = $m_din AND m.type = 'start'
MERGE (n)-[r:FOLLOWS]->(m)
SET r.weight = coalesce(r.weight, 0) + 1;
"""


logger = logging.getLogger(__name__)


def graph_copy(in_session: Session, out_session: Session):
    # Clearing destination (output) database
    out_session.write_transaction(clear_database)
    node_df = pd.DataFrame(in_session.run(Q_NODES_OBTAIN).data())
    logger.debug(node_df.head())
    node_df.apply(lambda row: out_session.run(Q_NODES_CREATE, n_din=row["n_din"], n_name=row["n_name"]), axis=1)
    rel_df = pd.DataFrame(in_session.run(Q_RELS_OBTAIN).data())
    logger.debug('links which we got')
    logger.debug(rel_df)
    rel_df.apply(
        lambda row: out_session.run(
            Q_RELS_CREATE,
            n_din=row["n_din"],
            m_din=row["m_din"],
            wght=row["weight"]
        ), axis=1
    )
