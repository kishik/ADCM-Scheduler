import json
import re

import requests
from django.http import JsonResponse, HttpResponseRedirect, HttpResponseNotFound
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from neo4j import GraphDatabase

from myapp.forms import UploadFileForm, RuleForm, WbsForm
from myapp.models import URN, ActiveLink, Rule, Wbs
from .graph_creation import historical_graph_creation
import simplejson
from .graph_creation import add_info, neo4jexplorer, graph_copy
import myapp.yml as yml

cfg: dict = yml.get_cfg("neo4j")

URL = cfg.get('url')
USER = cfg.get('user')
PASS = cfg.get('password')
NEW_URL = cfg.get('new_url')
NEW_USER = cfg.get('new_user')
NEW_PASS = cfg.get('new_password')

graph_data = []


# URL = 'neo4j+s://178ff2cf.databases.neo4j.io'
# USER = 'neo4j'
# PASS = '231099'


def authentication(url=URL, user=USER, password=PASS, database="neo4j"):
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


def login(request):
    if not request.user.is_authenticated:
        return redirect('/login/')
    if not request.user.is_authenticated:
        return render(request, 'registration/login.html')


# def graph_show(request):
#     if not request.user.is_authenticated:
#         return redirect('/login/')
#     nodes = []
#     rels = []
#     works = Work.nodes.all()
#
#     for work in works:
#         nodes.append({'id': work.id, 'name': work.name})
#
#     return render(request, 'myapp/index1.html', {
#         "nodes": nodes, "links": rels
#     })


def work_in_progress(request):
    """
    Заглушка
    :param request:
    :return:
    """
    if not request.user.is_authenticated:
        return redirect('/login/')
    return render(request, 'myapp/building.html')


# def graph(request):
#     if not request.user.is_authenticated:
#         return redirect('/login/')
#     nodes = []
#     rels = []
#     works = Work.nodes.all()
#
#     for work in works:
#         nodes.append({'id': work.id, 'name': work.name})
#
#         for job in work.incoming:
#             rels.append({"source": job.id, "target": work.id})
#         for job in work.outcoming:
#             rels.append({"source": work.id, "target": job.id})
#
#     return JsonResponse({"nodes": nodes, "links": rels})


def new_graph(request):
    """
    Показ исторического графа
    :param request:
    :return:
    """
    if not request.user.is_authenticated:
        return redirect('/login/')
    context = {'form': UploadFileForm(), 'url': URL, 'user_graph': USER, 'pass': PASS}
    return render(request, 'myapp/test.html', context)


# def file_upload(request):
#     """
#     Загрузка файла
#     :param request:
#     :return:
#     """
#     if not request.user.is_authenticated:
#         return redirect('/login/')
#     return render(request, 'myapp/model_load.html')


def urn_show(request):
    """
    Старые модели
    :param request:
    :return:
    """
    if not request.user.is_authenticated:
        return redirect('/login/')
    urns = URN.objects.all()
    return render(request, "myapp/cdn_model.html", {"urns": urns, "user": request.user})


def urn_index(request):
    """
    Выводит все правила выгрузки
    :param request:
    :return:
    """
    if not request.user.is_authenticated:
        return redirect('/login/')
    urns = URN.objects.all()
    return render(request, "myapp/urn_index.html", {"urns": urns})


def urn_create(request):
    """
    Создание URN
    :param request:
    :return:
    """
    if not request.user.is_authenticated:
        return redirect('/login/')
    if request.method == "POST":
        urn = URN()
        urn.type = request.POST.get("type")
        urn.urn = request.POST.get("urn")
        urn.isActive = True
        urn.userId = request.user.id
        urn.save()
    return HttpResponseRedirect("/urn_index/")


def urn_edit(request, id):
    """
    Изменение URN
    :param request:
    :param id:
    :return:
    """
    if not request.user.is_authenticated:
        return redirect('/login/')
    try:
        urn = URN.objects.get(id=id)
        if urn.userId != request.user.id:
            return HttpResponseNotFound("<h2>It's not your URN</h2>")
        if request.method == "POST":
            urn.type = request.POST.get("type")
            urn.urn = request.POST.get("urn")
            urn.save()
            return HttpResponseRedirect("/urn_index/")
        else:
            return render(request, "myapp/urn_edit.html", {"urn": urn})
    except URN.DoesNotExist:
        return HttpResponseNotFound("<h2>URN not found</h2>")


def urn_delete(request, id):
    """
    Удаление URN
    :param request:
    :param id:
    :return:
    """
    if not request.user.is_authenticated:
        return redirect('/login/')
    try:
        urn = URN.objects.get(id=id)
        if urn.userId != request.user.id:
            return HttpResponseNotFound("<h2>It's not your URN</h2>")
        urn.delete()
        return HttpResponseRedirect("/urn_index/")
    except URN.DoesNotExist:
        return HttpResponseNotFound("<h2>URN not found</h2>")


def easter(request):
    if not request.user.is_authenticated:
        return redirect('/login/')
    return render(request, 'myapp/WebGL Builds/index.html')


@csrf_exempt
def upload(request):
    """
    Загрузка графа в виде файла в исторический граф
    :param request:
    :return:
    """
    if not request.user.is_authenticated:
        return redirect('/login/')

    if request.method == 'POST':
        # historical_graph_creation.main(request.FILES['file'])
        add_info.add_info(request.FILES['file'])

    return redirect('/new_graph/')


def families(request):
    if not request.user.is_authenticated:
        return redirect('/login/')
    families_all = Rule.objects.all()
    return render(request, "myapp/families.html", {"families": families_all})


def model(request, id):
    """
    Выбор модели для использования
    :param request:
    :param id:
    :return:
    """
    if not request.user.is_authenticated:
        return redirect('/login/')
    try:
        urn = URN.objects.get(id=id)
        if urn.userId != request.user.id:
            return HttpResponseNotFound("<h2>It's not your URN</h2>")
        request.session['urn'] = id
        request.session['model_type'] = urn.type
        request.session['model'] = 'urn%' + urn.urn
        return redirect('/families/')

    except URN.DoesNotExist:
        return HttpResponseNotFound("<h2>URN not found</h2>")


def family(request, id):
    if not request.user.is_authenticated:
        return redirect('/login/')
    try:
        family = Rule.objects.get(id=id)
        if family.userId != request.user.id:
            return HttpResponseNotFound("<h2>It's not your URN</h2>")
        request.session['urn'] = id
        return redirect('/families/')

    except URN.DoesNotExist:
        return HttpResponseNotFound("<h2>URN not found</h2>")


def settings(request):
    """
    Настройки
    :param request:
    :return:
    """
    project = ActiveLink.objects.filter(userId=request.user.id).last()
    if not project:
        project = ActiveLink()
        project.projectId = None
        project.modelId = None
    return render(request, 'myapp/settings.html', {
        "userId": request.user.id,
        "projectId": project.projectId,
        "modelId": project.modelId
    })


@csrf_exempt
def saveModel(request):
    """
    Сохранение модели в настройках(settings)
    :param request:
    :return:
    """
    link = ActiveLink()
    link.userId = request.user.id
    string = request.POST.get("link")
    project = re.search(r'projects.*folderUrn', string)
    project = project[0][9:-10]
    link.projectId = project
    model = re.search(r'entityId=.*&viewModel', string)
    model = model[0][9:-10]
    link.modelId = model
    link.save()
    return redirect('/settings/')


def volumes(request):
    """
    Ведомость объемов
    :param request:
    :return:
    """
    flag = False
    project = ActiveLink.objects.filter(userId=request.user.id).last()

    if request.session['wbs'] != 0:
        res = requests.get('http://4d-model.acceleration.ru:8000/acc/get_spec/' +
                           request.session['specs'] + '/project/' + project.projectId +
                           '/model/' + request.session['model'])

    else:
        for wbs in Wbs.objects.all():
            res = requests.get('http://4d-model.acceleration.ru:8000/acc/get_spec/' +
                               wbs.specs[2:-2] + '/project/' + project.projectId +
                               '/model/' + request.session['model'])

            res = res.json()
            res = json.loads(res)
            if not flag:
                data = res
            else:
                data['data'].extend(res['data'])
            flag = True

        res = data

    if flag:
        data['data'] = sorted(data['data'], key=lambda x: x['wbs1'])
        myJson = data
    else:
        myJson = res.json()
        myJson = json.loads(myJson)

    # import xlwt
    #
    # # Initialize a workbook
    # book = xlwt.Workbook(encoding="utf-8")
    #
    # # Add a sheet to the workbook
    # sheet1 = book.add_sheet("Python Sheet 1")
    # if len(myJson['data']) > 0:
    #     i = 0
    #     for k, v in myJson['data'][0].items():
    #         sheet1.write(0, i, k)
    #         i = i + 1
    #     i = 1
    #     j = 0
    #     for element in myJson['data']:
    #         for k, v in element.items():
    #             sheet1.write(i, j, v)
    #             j = j + 1
    #         j = 0
    #         i = i + 1
    #     name = r"C:\Users\kishi\PycharmProjects\protodjango\spreadsheet.xls"
    #     book.save(name)
    # Write to the sheet of the workbook
    # sheet1.write(0, 0, "This is the First Cell of the First Sheet")
    #
    # # Save the workbook
    # book.save("spreadsheet.xls")
    dins = set()
    for el in myJson['data']:
        el["wbs"] = el["wbs1"] + el["wbs3_id"]
        dins.add(el["wbs3_id"])

    # add async
    user_graph = neo4jexplorer.Neo4jExplorer()
    print(dins)
    # заменить функцией copy
    graph_copy.main()
    #
    global graph_data
    graph_data = myJson['data']

    user_graph.create_new_graph_algo(dins)

    return render(request, 'myapp/volumes.html', {
        "myJson": myJson['data'],
    })


def sdrs(request):
    """
    Вывод правил выгрузки
    :param request:
    :return:
    """
    if not request.user.is_authenticated:
        return redirect('/login/')
    form = WbsForm()
    sdrs_all = Wbs.objects.all()
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = WbsForm(request.POST)

        # check whether it's valid:
        if form.is_valid():
            wbs = Wbs()
            wbs.wbs_code = form["wbs_code"].data
            wbs.docsdiv = form["docsdiv"].data
            wbs.wbs1 = form["wbs1"].data
            wbs.wbs2 = form["wbs2"].data
            wbs.wbs3 = form["wbs3"].data
            wbs.specs = form["specs"].data
            wbs.userId = request.user.id
            wbs.isActive = True
            wbs.save()
            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:
            return HttpResponseRedirect('/sdrs/')

    return render(request, "myapp/sdr.html", {"form": form, "sdrs_all": sdrs_all})


def sdr(request, id):
    """
    Выбор правила выгрузки
    :param request:
    :param id:
    :return:
    """
    if not request.user.is_authenticated:
        return redirect('/login/')
    try:
        if id == 0:
            request.session['wbs'] = 0
            request.session['specs'] = 0
            return redirect('/volumes/')

        wbs = Wbs.objects.get(id=id)
        if wbs.userId != request.user.id:
            return HttpResponseNotFound("<h2>It's not your WBS</h2>")
        request.session['wbs'] = id
        request.session['specs'] = wbs.specs[2:-2]

        return redirect('/volumes/')

    except URN.DoesNotExist:
        return HttpResponseNotFound("<h2>WBS not found</h2>")


def sdr_delete(request, id):
    """
    Удаление правила выгрузки
    :param request:
    :param id:
    :return:
    """
    if not request.user.is_authenticated:
        return redirect('/login/')
    try:
        wbs = Wbs.objects.get(id=id)
        if wbs.userId != request.user.id:
            return HttpResponseNotFound("<h2>It's not your WBS</h2>")
        wbs.delete()
        return HttpResponseRedirect("/sdrs/")
    except Wbs.DoesNotExist:
        return HttpResponseNotFound("<h2>WBS not found</h2>")


def rule_create(request):
    """
    Создание правила выгрузки
    :param request:
    :return:
    """
    if not request.user.is_authenticated:
        return redirect('/login/')
    form = RuleForm()
    families_all = Rule.objects.all()
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = RuleForm(request.POST)

        # check whether it's valid:
        if form.is_valid():
            rule = Rule()
            rule.name = form["name"].data
            rule.rule = form["rule"].data
            rule.userId = request.user.id
            rule.isActive = True
            rule.save()
            # redirect to a new URL:
            return HttpResponseRedirect('/families/')

    return render(request, "myapp/rule.html", {"form": form, "families": families_all})


def rule_delete(request, id):
    """
    Удаление правила выгрузки
    :param request:
    :param id:
    :return:
    """
    if not request.user.is_authenticated:
        return redirect('/login/')
    try:
        rule = Rule.objects.get(id=id)
        if rule.userId != request.user.id:
            return HttpResponseNotFound("<h2>It's not your Rule</h2>")
        rule.delete()
        return HttpResponseRedirect("/families/")
    except Rule.DoesNotExist:
        return HttpResponseNotFound("<h2>Rule not found</h2>")


#########
def nodes(session):
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
        q_data_obtain = f'''
                MATCH (a)-[r]->(c)
                WHERE c.DIN = $din
                RETURN a
                '''
        result = session.run(q_data_obtain, din=element).data()

        nodes[element] = [result[i]['a']['DIN'] for i in range(len(result))]

    return nodes


def children():
    """
    din всех детей
    :return: list с din
    """
    session = authentication()

    q_data_obtain = f'''
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
        q_data_obtain = f'''
                    MATCH (a)-[r]->(c)
                    WHERE a.DIN = $din
                    RETURN c
                    '''
        result = session.run(q_data_obtain, din=element).data()
        nodes[element] = [result[i]['c']['DIN'] for i in range(len(result))]

    return nodes


def parentsByDin(din, session):
    """
    Возвращает всех родителей элемента din
    :param din:
    :param session:
    :return:
    """
    q_data_obtain = f'''
                            MATCH (c)-[r]->(a)
                            WHERE a.DIN = $din
                            RETURN c
                            '''
    result = session.run(q_data_obtain, din=din).data()

    return [result[i]['c']['DIN'] for i in range(len(result))]


def childrenByDin(din, session):
    """
    Возвращает всех детей элемента din
    :param din:
    :param session:
    :return: list динов
    """
    q_data_obtain = f'''
                        MATCH (a)-[r]->(c)
                        WHERE a.DIN = $din
                        RETURN c
                        '''
    result = session.run(q_data_obtain, din=din).data()

    return [result[i]['c']['DIN'] for i in range(len(result))]


def calculateDistance(session):
    """
    Запускает проход по всем нодам, не имеющим родителей
    :return: dict нодов с их глубиной в графе
    """
    distances = {}
    for node in allNodes():
        if parentsByDin(node, session):
            continue
        # print("preprohod")
        prohod(start_din=node, distances=distances, session=session, cur_level=0)
        # print("prohod")
    return distances


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


#################

def allNodes():
    """
    Возвращает все ноды
    :return: список нодов
    """
    session = authentication()
    q_data_obtain = f'''
                        MATCH (n) RETURN n
                        '''
    result = session.run(q_data_obtain).data()
    allNodes = [result[i]['n']['DIN'] for i in range(len(result))]

    return allNodes


def schedule(request):
    """
    Диаграмма Ганта
    :param request:
    :return:
    """
    if not request.user.is_authenticated:
        return redirect('/login/')

    session = authentication(url=NEW_URL, user=NEW_USER, password=NEW_PASS)
    # print(1)
    distances = calculateDistance(session=session)
    # print(2)
    parents = nodes(session=session)
    # print(3)
    q_data_obtain = f'''
                    MATCH (n) RETURN n
                    '''
    # print("preresult")
    result = session.run(q_data_obtain).data()
    # print("preclose")
    session.close()
    allNodes = [result[i]['n']['DIN'] for i in range(len(result))]

    names = {result[i]['n']['DIN']: result[i]['n']['name'] for i in range(len(result))}

    unique_wbs1 = set()
    global graph_data
    result = {}
    # print(graph_data)
    for el in graph_data:
        if el['wbs1'] in result:
            result[el['wbs1']].append(el['wbs3_id'])
        else:
            result[el['wbs1']] = [el['wbs3_id']]
        unique_wbs1.add(el['wbs1'])

    print('result', result)
    elements = []

    for element in allNodes:
        if element not in parents:
            elements.append(
                [str(element), names[element] + " DIN" + element, None, distances[element], 1, 1,
                 distances[element] + 1, 1, 1,
                 None, element, None])
        else:
            elements.append(
                [str(element), names[element] + " DIN" + element, None, distances[element], 1, 1,
                 distances[element] + 1, 1, 1,
                 None,
                 element, ','.join(parents[element])])

    # elements = sorted(elements, key=lambda x: int(x[0]))
    print(result)
    json_list = simplejson.dumps(elements)
    # result = simplejson.dumps(result)
    height = 40
    # print(unique_wbs1)
    print(result)
    return render(request, 'myapp/schedule.html', {'json_list': json_list, 'total_height': (len(elements) + 2) * height,
                                                   'height': height, 'wbs1': unique_wbs1, 'result': result})
