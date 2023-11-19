from neo4j import GraphDatabase, Transaction


def add_class(tx: Transaction, class_name: str):
    q_class = '''
    MERGE (n:IfcClass {name: $name})
    '''
    tx.run(q_class, name=class_name)


def add_class_rel(tx: Transaction, pred_name: str, flw_name: str):
    q_rel = '''
    MATCH (a:IfcClass) WHERE a.name = $name1
    MATCH (b:IfcClass) WHERE b.name = $name2
    MERGE (a)-[r:FOLLOWS]->(b)
    '''
    tx.run(q_rel, name1=pred_name, name2=flw_name)


def create_group_graph():
    group_driver = GraphDatabase.driver(
        "bolt://neo4j_groups:7687",
        auth=("neo4j", "23109900")
    )
    group_driver.verify_connectivity()

    classes = (
        'IfcWall',
        # 'IfcDoor',
        'IfcBuildingElementProxy',
        # 'IfcWindow',
        "IfcStair",
        'IfcSlab',
        "IfcFlowTerminal",
        "IfcFurniture",
        'IfcCurtainWall',)

    with group_driver.session() as session:
        session.run('MATCH (n) DETACH DELETE n')
        for i in classes:
            if i == "IfcStair":
                print(i)
            session.execute_write(add_class, i)

        session.execute_write(add_class_rel, 'IfcBuildingElementProxy', 'IfcWall')
        session.execute_write(add_class_rel, 'IfcBuildingElementProxy', 'IfcSlab')
        session.execute_write(add_class_rel, 'IfcWall', 'IfcWindow')
        session.execute_write(add_class_rel, 'IfcWall', "IfcFlowTerminal")
        session.execute_write(add_class_rel, 'IfcWall', 'IfcCurtainWall')
        session.execute_write(add_class_rel, 'IfcWall', "IfcFurniture")
        session.execute_write(add_class_rel, 'IfcWall', "IfcStair")
        session.execute_write(add_class_rel, 'IfcBuildingElementProxy', 'IfcDoor')
        session.execute_write(add_class_rel, 'IfcDoor', 'IfcWindow')


if __name__ == "__main__":
    create_group_graph()
