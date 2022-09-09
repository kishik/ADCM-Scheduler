from neo4j import Transaction, GraphDatabase
import pandas as pd
import myapp.yml as yml

cfg: dict = yml.get_cfg("neo4j")

URL = cfg.get('url')
USER = cfg.get('user')
PASS = cfg.get('password')


def add_node(tx: Transaction, node_din: str, node_name: str):
    tx.run("MERGE (a:Work {DIN: $din, name: $name});",
           din=node_din,
           name=node_name
           )


def add_rel(tx: Transaction, pred_din: str, flw_din: str):
    q_edge = '''
    MATCH (a:Work) WHERE a.DIN = $din1 
    MATCH (b:Work) WHERE b.DIN = $din2
    MERGE (a)-[r:FOLLOWS]->(b)
    '''
    tx.run(q_edge, din1=pred_din, din2=flw_din)


def add_info(file: str):
    df = pd.read_excel(file, dtype=str)

    print()
    # url = "neo4j+s://178ff2cf.databases.neo4j.io:7687"
    # user = "neo4j"
    # pswd = "231099"
    driver = GraphDatabase.driver(URL, auth=(USER, PASS))
    with driver.session() as session:
        if df.keys().values[0] == 'ADCM_DIN':
            print("nodes")
            df.apply(
                lambda row: session.write_transaction(
                    add_node, row['ADCM_DIN'], row['name']),
                axis=1
            )
        elif df.keys().values[0] == 'pred':
            print("rels")
            df.apply(
                lambda row: session.write_transaction(
                    add_rel, row['pred'], row['flw']),
                axis=1
            )
    driver.close()
