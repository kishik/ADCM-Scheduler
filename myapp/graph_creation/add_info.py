from neo4j import Session


def add_info(session: Session, node_din: str, node_name: str = None, flw_din: str = None):
    q_add_node = "MERGE (a:Work {DIN: $din, name: $name});"
    q_add_rel = '''
        MATCH (a:Work) WHERE a.DIN = $din1 
        MATCH (b:Work) WHERE b.DIN = $din2
        MERGE (a)-[r:FOLLOWS {weight: 1}]->(b);
        '''

    if node_name:
        session.run(q_add_node, din=node_din, name=node_name)
    elif flw_din:
        session.run(q_add_rel, din1=node_din, din2=flw_din)
