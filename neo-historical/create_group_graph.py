import os

import pandas as pd
from neo4j import GraphDatabase, Transaction


EXCEL_GESN_PATH = "./solution.xls"
GROUPS_URI = 'neo4j://neo4j_historical:7687'
# GROUPS_URI = "neo4j://localhost:7688"
classes = (
    'IfcWall',
    'IfcBeam',
    # 'IfcDoor',
    'IfcBuildingElementProxy',
    # 'IfcWindow',
    "IfcStair",
    "IfcStairFlight",
    'IfcSlab',
    "IfcFlowTerminal",
    "IfcFurniture",
    'IfcCurtainWall',
    "IfcFooting",
    "IfcColumn",
)


def add_class(tx: Transaction, class_name: str, label: str):
    q_class = f'''
    MERGE (n:{label} {{name: $name}})
    '''
    tx.run(q_class, name=class_name)


def add_rel(tx, pred_name: str, flw_name: str):
    q_rel = '''
    MATCH (a) WHERE a.name = $name1
    MATCH (b) WHERE b.name = $name2
    MERGE (a)-[r:FOLLOWS]->(b)
    '''
    tx.run(q_rel, name1=pred_name, name2=flw_name)


def create_group_graph():
    print(GROUPS_URI)
    group_driver = GraphDatabase.driver(
        GROUPS_URI,
        auth=("neo4j", "23109900")
    )
    group_driver.verify_connectivity()

    df = pd.read_excel(
        EXCEL_GESN_PATH,
        sheet_name=0,
        header=None,
        names=["GESN", "name"]
    ).dropna()
    gesn_list = df.GESN.to_numpy()

    df_gesn_links = pd.read_excel(
        EXCEL_GESN_PATH,
        sheet_name=1,
    ).dropna()

    with group_driver.session() as session:
        # session.run('MATCH (n) DETACH DELETE n')

        for ind, gesn in enumerate(gesn_list):
            session.execute_write(add_class, gesn, "WBS3")
            if ind != 0:
                session.execute_write(add_rel, pred_gesn, gesn)
            pred_gesn = gesn
        session.execute_write(add_class, "no GESN", "WBS3")
        session.execute_write(add_rel, gesn_list[-1], "no GESN")
        session.execute_write(add_rel, gesn_list[-2], "no GESN")
        df_gesn_links.apply(
            lambda row: session.execute_write(add_rel, row.pred, row.flw),
            axis=1
        )

        for i in classes:
            session.execute_write(add_class, i, "IfcClass")

        session.execute_write(add_rel, 'IfcFooting', 'IfcWall')
        session.execute_write(add_rel, 'IfcSlab', 'IfcColumn')
        session.execute_write(add_rel, 'IfcFooting', 'IfcSlab')
        session.execute_write(add_rel, 'IfcBuildingElementProxy', 'IfcWall')
        session.execute_write(add_rel, 'IfcBuildingElementProxy', 'IfcStair')
        session.execute_write(add_rel, 'IfcSlab', 'IfcWall')
        session.execute_write(add_rel, 'IfcSlab', 'IfcBuildingElementProxy')
        session.execute_write(add_rel, 'IfcBuildingElementProxy', 'IfcBeam')
        session.execute_write(add_rel, 'IfcBuildingElementProxy', 'IfcColumn')
        session.execute_write(add_rel, 'IfcWall', 'IfcWindow')
        session.execute_write(add_rel, 'IfcWall', "IfcFlowTerminal")
        session.execute_write(add_rel, 'IfcWall', 'IfcCurtainWall')
        session.execute_write(add_rel, 'IfcWall', "IfcFurniture")
        session.execute_write(add_rel, 'IfcWall', "IfcStair")
        session.execute_write(add_rel, "IfcColumn", 'IfcBeam')
        session.execute_write(add_rel, "IfcStair", "IfcStairFlight")
        session.execute_write(add_rel, 'IfcBuildingElementProxy', 'IfcDoor')
        session.execute_write(add_rel, 'IfcDoor', 'IfcWindow')


if __name__ == "__main__":
    print(os.getcwd())
    print("create group graph")
    create_group_graph()
