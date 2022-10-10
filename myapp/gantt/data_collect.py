from datetime import timedelta, datetime

import pandas as pd
from neo4j import GraphDatabase, Session

import myapp.yml as yml
from myapp.models import Link

cfg: dict = yml.get_cfg("neo4j")

URL = cfg.get('url')
USER = cfg.get('user')
PASS = cfg.get('password')
NEW_URL = cfg.get('new_url')
NEW_USER = cfg.get('new_user')
NEW_PASS = cfg.get('new_password')
LAST_URL = cfg.get('last_url')

types_of_links = {"finish_to_start": "0", "start_to_start": "1", "finish_to_finish": "2", "start_to_finish": "3"}


# мы должны создавать таски и связи в бд

def elements(all_nodes, distances, parents, names):
    elements = []
    cur_date = datetime.now()
    for element in all_nodes:
        end_date = timedelta(14)
        # new_date = cur_date + end_date * int(distances[element])
        new_date = cur_date + end_date * 2
        end_date = new_date + end_date
        if element not in parents:
            elements.append(
                [str(element), names[element] + " DIN" + element, None, new_date.year, new_date.month, new_date.day,
                 end_date.year, end_date.month, end_date.day,
                 None, element, None])
        else:
            elements.append(
                [str(element), names[element] + " DIN" + element, None, new_date.year, new_date.month, new_date.day,
                 end_date.year, end_date.month, end_date.day,
                 None,
                 element, ','.join(parents[element])])
    return elements


def authentication(url=NEW_URL, user=USER, password=PASS, database="neo4j"):
    """
    Создание сессии для работы с neo4j
    :param url:
    :param user:
    :param password:
    :param database:
    :return:
    """
    driver = GraphDatabase.driver(url, auth=(user, password))
    session = driver.session(database=database)
    return session


def allNodes(session):
    """
    Возвращает все ноды
    :return: список нодов
    """

    q_data_obtain = 'MATCH (n) RETURN n'
    result = session.run(q_data_obtain).data()
    return [result[i]['n']['DIN'] for i in range(len(result))]


def parentsByDin(din, session):
    """
    Возвращает всех родителей элемента din
    :param din:
    :param session:
    :return:
    """
    q_data_obtain = '''
    MATCH (c)-[r]->(a)
    WHERE a.DIN = $din
    RETURN c
    '''
    result = session.run(q_data_obtain, din=din).data()
    dins = [result[i]['c']['DIN'] for i in range(len(result))]
    if din in dins:
        dins.remove(din)
    print(dins)
    return dins


def childrenByDin(din, session):
    """
    Возвращает всех детей элемента din
    :param din:
    :param session:
    :return: list динов
    """
    q_data_obtain = '''
    MATCH (a)-[r]->(c)
    WHERE a.DIN = $din
    RETURN c
    '''
    result = session.run(q_data_obtain, din=din).data()

    return [result[i]['c']['DIN'] for i in range(len(result))]


def prohod(start_din, distances, session, cur_level=0):
    """
    Проходит рекурсивный путь по своим детям, указывая максимальную глубину рекурсии,
    сравнивая текущую и полученную сейчас
    :param start_din:
    :param distances:
    :param session:
    :param cur_level:
    """
    if start_din not in distances:
        distances[start_din] = 0

    distances[start_din] = max(cur_level, distances[start_din])

    for element in childrenByDin(start_din, session):
        prohod(element, distances, session, cur_level + 1)


def calculateDistance(session):
    """
    Запускает проход по всем нодам, не имеющим родителей
    :return: dict нодов с их глубиной в графе
    """
    distances = {}
    for node in allNodes(session):
        if parentsByDin(node, session):
            continue
        # print("preprohod")
        prohod(start_din=node, distances=distances, session=session, cur_level=0)
        # print("prohod")
    return distances


def children():
    """
    din всех детей
    :return: list с din
    """
    session = authentication()

    q_data_obtain = '''
    MATCH (top) // though you should use labels if possible)
    WHERE NOT ()-[]->(top)
    RETURN top
    '''
    result = session.run(q_data_obtain).data()
    elements = [result[i]['top']['DIN'] for i in range(len(result))]
    nodes = {}

    q_data_obtain = f'''
                        MATCH (a)-[r]->(c)
                        RETURN a
                        '''
    result = session.run(q_data_obtain).data()
    children = [result[i]['a']['DIN'] for i in range(len(result))]

    for element in children:
        q_data_obtain = '''
        MATCH (a)-[r]->(c)
        WHERE a.DIN = $din
        RETURN c
        '''
        result = session.run(q_data_obtain, din=element).data()
        nodes[element] = [result[i]['c']['DIN'] for i in range(len(result))]

    return nodes


def parents_for_nodes(session):
    """
    Поиск списка родителей для каждого ребенка
    :return:
    """

    nodes = {}

    q_data_obtain = f'''
                    MATCH (a)-[r]->(c)
                    RETURN c
                    '''
    result = session.run(q_data_obtain).data()
    children = [result[i]['c']['DIN'] for i in range(len(result))]

    for element in children:
        q_data_obtain = '''
        MATCH (a)-[r]->(c)
        WHERE c.DIN = $din
        RETURN a
        '''
        result = session.run(q_data_obtain, din=element).data()

        nodes[element] = [result[i]['a']['DIN'] for i in range(len(result))]

    return nodes


def links_creation(session):
    pass
    result = []
    # выбрать связи старт-старт result.append(start-start) (from,to) {from: to}
    # выбрать связи старт-финиш result.append(start-finish)
    # выбрать связи финиш-старт result.append(finish-start)
    # выбрать связи финиш-финиш result.append(finish-finish)


def delete_clones(session):
    pass


def get_typed_edges(session: Session, rel_type: str) -> pd.DataFrame:
    pred_type = flw_type = None
    if rel_type == 'FS':
        pred_type = 'finish'
        flw_type = 'start'
    elif rel_type == 'SS':
        pred_type = flw_type = 'start'
    elif rel_type == 'FF':
        pred_type = flw_type = 'finish'
    elif rel_type == 'SF':
        pred_type = 'start'
        flw_type = 'finish'

    Q_FINISH_START = f'''
    MATCH (n)-[:FOLLOWS]->(m)
    WHERE n.type = '{pred_type}' AND m.type = '{flw_type}' 
    RETURN n.DIN AS pred_din, m.DIN AS flw_din
    '''
    result = session.run(Q_FINISH_START).data()
    return pd.DataFrame(result)


def saving_typed_edges(session, unique_wbs1):
    edges_types = ('FS', 'SS', 'FF', 'SF')
    for i in range(len(edges_types)):
        edges = get_typed_edges(session, edges_types[i])
        for index, row in edges.iterrows():
            print(row['pred_din'], row['flw_din'])
            for wbs1 in unique_wbs1:
                # if row['pred_din'] in  смотрим если ли этот дин с этим wbs1
                Link(source=str(wbs1) + str(row['pred_din']), target=str(wbs1) + str(row['flw_din']),
                     type=str(i), lag=0).save()


if __name__ == '__main__':
    url = 'neo4j+s://99c1a702.databases.neo4j.io:7687'  # NEW_URL
    user = 'neo4j'
    pswd = '231099'
    driver = GraphDatabase.driver(url, auth=(user, pswd))
    with driver.session() as session:
        print(get_typed_edges(session, 'FS').head())
        print(get_typed_edges(session, 'SS').head())
