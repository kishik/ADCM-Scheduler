from datetime import timedelta, datetime

import numpy as np
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


def get_name_by_din(session: Session, din: str) -> str:
    q_get_name = '''
    MATCH (n) WHERE n.DIN = $din
    RETURN n.name AS name
    '''
    result = session.run(q_get_name, din=din).data()
    return result[0]['name']


# мы должны создавать таски и связи в бд

def get_edge_type(session: Session, pred_din: str, flw_din: str) -> str:
    q_get_rel = '''
    MATCH (n)-[r:FOLLOWS]->(m)
    WHERE n.DIN = $din1 AND m.DIN = $din2
    RETURN n.type AS pred_type, m.type AS flw_type
    '''
    result = session.run(q_get_rel, din1=pred_din, din2=flw_din).data()
    pred_type = result[0]['pred_type']
    flw_type = result[0]['flw_type']
    if pred_type == 'start':
        if flw_type == 'start':
            return 'SS'
        return 'SF'
    if flw_type == 'start':
        return 'FS'
    return 'FF'


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

    q_data_obtain = 'MATCH (n) RETURN n.DIN AS din'
    result = session.run(q_data_obtain).data()
    return np.array([item['din'] for item in result])


def parentsByDin(din, session):
    """
    Возвращает всех родителей элемента din
    :param din:
    :param session:
    :return: np.array массив DINов родителей элемента
    """

    q_data_obtain = '''
    MATCH (c)-[r]->(a)
    WHERE a.DIN = $din
    RETURN c.DIN AS din
    '''
    result = session.run(q_data_obtain, din=din).data()
    dins_arr = np.array([item['din'] for item in result])
    if din in dins_arr:
        dins_arr = dins_arr[dins_arr != din]
    return dins_arr


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
    RETURN c.DIN AS din
    '''
    result = session.run(q_data_obtain, din=din).data()
    children_arr = np.array([item['din'] for item in result])
    if din in children_arr:
        children_arr = children_arr[children_arr != din]
    return children_arr


def prohod(start_din, distances, session, dins, cur_level=0):
    """
    Проходит рекурсивный путь по своим детям, указывая максимальную глубину рекурсии,
    сравнивая текущую и полученную сейчас
    :param start_din:
    :param distances: dict din to level
    :param session:
    :param cur_level:
    """
    if start_din not in dins:
        for element in childrenByDin(start_din, session):
            prohod(element, distances, session, dins, cur_level)
    else:
        if start_din not in distances:
            distances[start_din] = 0

        distances[start_din] = max(cur_level, distances[start_din])
        for element in childrenByDin(start_din, session):
            if start_din == element:
                continue
            if get_edge_type(session, start_din, element) == "FS":
                prohod(element, distances, session, dins, cur_level + 1)
                continue
            elif get_edge_type(session, start_din, element) == "SS":
                # если связь типа старт-старт то prohod(element, distances, session, cur_level)
                prohod(element, distances, session, dins, cur_level)


def calculateDistance(session, dins):
    """
    Запускает проход по всем нодам, не имеющим родителей
    :return: dict нодов с их глубиной в графе
    """
    distances = {}
    for node in allNodes(session):
        if parentsByDin(node, session).size > 0:
            continue
        prohod(start_din=node, distances=distances, session=session, cur_level=0, dins=dins)
    return distances


def prohod_hist(start_din, distances, session, cur_level=0):
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
        if start_din == element:
            continue
        if get_edge_type(session, start_din, element) == "FS":
            prohod_hist(element, distances, session, cur_level + 1)
            continue
        elif get_edge_type(session, start_din, element) == "SS":
            # если связь типа старт-старт то prohod(element, distances, session, cur_level)
            prohod_hist(element, distances, session, cur_level)


def calculate_hist_distance(session):
    """
    Запускает проход по всем нодам, не имеющим родителей
    :return: dict нодов с их глубиной в графе
    """
    distances = {}
    for node in allNodes(session):
        if parentsByDin(node, session):
            continue
        prohod_hist(start_din=node, distances=distances, session=session, cur_level=0)
    return distances


def children():
    """
    din всех детей
    :return: list с din
    """
    session = authentication()
    # UPD 24.10 По-моему, все  что закоменчено ниже не используется
    #
    # q_data_obtain = '''
    # MATCH (top) // though you should use labels if possible)
    # WHERE NOT ()-[]->(top)
    # RETURN top
    # '''
    # result = session.run(q_data_obtain).data()
    # elements = [result[i]['top']['DIN'] for i in range(len(result))]
    nodes = {}

    q_data_obtain = '''
    MATCH (a)-[r]->(c)
    RETURN a.DIN AS din
    '''
    result = session.run(q_data_obtain).data()
    children = np.array([item['din'] for item in result])

    for element in children:
        q_data_obtain = '''
        MATCH (a)-[r]->(c)
        WHERE a.DIN = $din
        RETURN c.DIN AS din
        '''
        result = session.run(q_data_obtain, din=element).data()
        nodes[element] = np.array([item['din'] for item in result])

    return nodes


def parents_for_nodes(session):
    """
    Поиск списка родителей для каждого ребенка
    :return:
    """

    nodes = {}

    q_data_obtain = '''
    MATCH (a)-[r]->(c)
    RETURN c.DIN AS din
    '''
    result = session.run(q_data_obtain).data()
    children = np.array([item['din'] for item in result])

    for element in children:
        q_data_obtain = '''
        MATCH (a)-[r]->(c)
        WHERE c.DIN = $din
        RETURN a.DIN AS din
        '''
        result = session.run(q_data_obtain, din=element).data()

        nodes[element] = np.array([item['din'] for item in result])

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


def saving_typed_edges(session):
    edges_types = ('FS', 'SS', 'FF', 'SF')
    for i in range(len(edges_types)):
        edges = get_typed_edges(session, edges_types[i])
        for index, row in edges.iterrows():
            Link(source=str(row['pred_din']), target=str(row['flw_din']),
                 type=str(i), lag=0).save()


def saving_typed_edges_with_wbs(session, result):
    edges_types = ('FS', 'SS', 'FF', 'SF')
    for i in range(len(edges_types)):
        edges = get_typed_edges(session, edges_types[i])
        for index, row in edges.iterrows():
            print(row['pred_din'], row['flw_din'])
            for wbs1 in result:
                for wbs2 in result[wbs1].keys():
                    # if row['pred_din'] in  смотрим если ли эти дины с этим wbs1
                    Link(source=str(wbs1) + wbs2 + str(row['pred_din']), target=str(wbs1) + wbs2 + str(row['flw_din']),
                         type=str(i), lag=0).save()


if __name__ == '__main__':
    url = 'neo4j+s://99c1a702.databases.neo4j.io:7687'  # NEW_URL
    user = 'neo4j'
    pswd = '231099'
    driver = GraphDatabase.driver(url, auth=(user, pswd))
    with driver.session() as session:
        print(get_typed_edges(session, 'FS').head())
        print(get_typed_edges(session, 'SS').head())
