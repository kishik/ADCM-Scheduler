import numpy as np


def allNodes(session):
    """
    Возвращает все ноды
    :return: список нодов
    """

    q_data_obtain = '''MATCH (n:Element) 
    WHERE NOT n.is_a IN ["IfcBuilding", "IfcBuildingStorey"]
    RETURN DISTINCT n.id AS din'''
    result = session.run(q_data_obtain).data()
    return np.array([item["din"] for item in result])


def parentsByDin(din, session):
    """
    Возвращает всех родителей элемента din
    :param din:
    :param session:
    :return: np.array массив DINов родителей элемента
    """

    q_data_obtain = """
    MATCH (c)-[r:TRAVERSE|TRAVERSE_GROUP]->(a)
    WHERE a.id = $din
    RETURN DISTINCT c.id AS din
    """
    result = session.run(q_data_obtain, din=din).data()
    dins_arr = np.array([item["din"] for item in result])
    dins_arr = dins_arr[~np.isin(dins_arr, din)]
    return dins_arr


def childrenByDin(din, session):
    """
    Возвращает всех детей элемента din
    :param din:
    :param session:
    :return: list динов
    """
    q_data_obtain = """
    MATCH (a)-[r:TRAVERSE|TRAVERSE_GROUP]->(c)
    WHERE a.id = $din
    RETURN DISTINCT c.id AS din
    """
    result = session.run(q_data_obtain, din=din).data()
    children_arr = np.array([item["din"] for item in result])
    children_arr = children_arr[~np.isin(children_arr, din)]
    return children_arr


def prohod(start_din, distances, session, dins, cur_level=0, visited=[]):
    """
    Проходит рекурсивный путь по своим детям, указывая максимальную глубину рекурсии,
    сравнивая текущую и полученную сейчас
    """
    if start_din in visited:
        return
    visited.append(start_din)
    if start_din not in dins:
        for element in childrenByDin(start_din, session):
            prohod(element, distances, session, dins, cur_level, visited)
    else:
        if start_din not in distances:
            distances[start_din] = 0

        distances[start_din] = max(cur_level, distances[start_din])

        for element in childrenByDin(start_din, session):
            if start_din == element:
                continue
            # раньше здесь был get_edge_type, но сейчас у нас всегда тип связи "FS"
            prohod(element, distances, session, dins, cur_level + 1, visited.copy())


def calculateDistance(session, dins):
    """
    Запускает проход по всем нодам, не имеющим родителей
    dins это дины которые нас интересуют в рамках одного отчета
    :return: dict нодов с их глубиной в графе
    """
    distances = {}
    for node in allNodes(session):
        if parentsByDin(node, session).size > 0:
            continue
        prohod(start_din=node, distances=distances, session=session, cur_level=0, dins=dins, visited=list())
    return distances


def prohod_hist(start_din, distances, session, cur_level=0, visited=[]):
    """
    Проходит рекурсивный путь по своим детям, указывая максимальную глубину рекурсии,
    сравнивая текущую и полученную сейчас
    :param start_din:
    :param distances:
    :param session:
    :param cur_level:
    """
    if start_din in visited:
        return
    visited.append(start_din)

    if start_din not in distances:
        distances[start_din] = 0

    distances[start_din] = max(cur_level, distances[start_din])
    for element in childrenByDin(start_din, session):
        if start_din == element:
            continue
        # if get_edge_type(session, start_din, element) == "FS":
        prohod_hist(element, distances, session, cur_level + 1)
        # continue
        # elif get_edge_type(session, start_din, element) == "SS":
        #     # если связь типа старт-старт то prohod(element, distances, session, cur_level)
        #     prohod_hist(element, distances, session, cur_level)


def calculate_hist_distance(session):
    """
    Запускает проход по всем нодам, не имеющим родителей
    :return: dict нодов с их глубиной в графе
    """
    distances = {}
    for node in allNodes(session):
        if parentsByDin(node, session).size > 0:
            continue
        prohod_hist(start_din=node, distances=distances, session=session, cur_level=0)
    return distances
