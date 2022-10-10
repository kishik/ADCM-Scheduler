import json
import re
from datetime import timedelta, datetime

import requests
import simplejson
from django.http import HttpResponseRedirect, HttpResponseNotFound, JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from neo4j import GraphDatabase
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import AllowAny

from myapp.serializers import TaskSerializer
from myapp.serializers import LinkSerializer
import myapp.yml as yml
from myapp.forms import UploadFileForm, RuleForm, WbsForm, AddNode, AddLink
from myapp.models import URN, ActiveLink, Rule, Wbs, Task, Link, Task2
from .gantt import data_collect
from .graph_creation import add, neo4jexplorer, graph_copy

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response


cfg: dict = yml.get_cfg("neo4j")

URL = cfg.get('url')
USER = cfg.get('user')
PASS = cfg.get('password')
NEW_URL = cfg.get('new_url')
NEW_USER = cfg.get('new_user')
NEW_PASS = cfg.get('new_password')
LAST_URL = cfg.get('last_url')

graph_data = []


def login(request):
    if not request.user.is_authenticated:
        return redirect('/login/')
    if not request.user.is_authenticated:
        return render(request, 'registration/login.html')


def work_in_progress(request):
    """
    Заглушка
    :param request:
    :return:
    """
    if not request.user.is_authenticated:
        return redirect('/login/')
    return render(request, 'myapp/building.html')


def new_graph(request):
    """
    Показ исторического графа
    :param request:
    :return:
    """
    if not request.user.is_authenticated:
        return redirect('/login/')
    context = {'form': UploadFileForm(), 'url': LAST_URL, 'user_graph': USER, 'pass': PASS, 'link': AddLink(),
               'node': AddNode()}
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
        session = data_collect.authentication(url=URL, user=USER, password=PASS)
        add.from_one_file(session, request.FILES['file'])

    return redirect('/new_graph/')


def families(request):
    if not request.user.is_authenticated:
        return redirect('/login/')
    return redirect('/sdrs/')
    # families_all = Rule.objects.all()
    # return render(request, "myapp/families.html", {"families": families_all})


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
    print(res)
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
    user_graph = neo4jexplorer.Neo4jExplorer(uri=URL)
    # тут ресторю в свой граф из эксель
    user_graph.restore_graph()
    # заменить функцией copy
    # graph_copy.graph_copy(authentication(url=NEW_URL, user=NEW_USER, password=NEW_PASS),
    #                       authentication(url=URL, user=USER, password=PASS))
    #
    global graph_data
    graph_data = myJson['data']

    user_graph.create_new_graph_algo(dins)
    print(myJson['data'])
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


def schedule(request):
    """
    Диаграмма Ганта
    :param request:
    :return:
    """
    if not request.user.is_authenticated:
        return redirect('/login/')

    session = data_collect.authentication(url=URL, user=USER, password=PASS)
    distances = data_collect.calculateDistance(session=session)
    parents = data_collect.parents_for_nodes(session=session)
    q_data_obtain = f'''
                    MATCH (n) RETURN n
                    '''
    result = session.run(q_data_obtain).data()
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

    elements = data_collect.elements(allNodes, distances, parents, names)

    json_list = simplejson.dumps(elements)
    Task2.objects.all().delete()
    Link.objects.all().delete()
    t1 = Task2(id=1, text="01p",
               start_date="2022-10-05 00:00:00",
               end_date="2022-10-19 00:00:00",
               duration=2, progress=0.5, parent="0")
    t1.save()
    t1 = Task2(id=2, text="02p",
               start_date="2022-10-05 00:00:00",
               end_date="2022-10-19 00:00:00",
               duration=2, progress=0.5, parent="0")
    t1.save()
    height = 40
    sorted(elements, key=lambda element: str(element[3]) + "-" + str(element[4]) + "-" + str(element[5]))
    for element in elements:
        for key, value in result.items():
            if element[0] in value:
                t1 = Task2(id=str(key + str(element[0])), text=element[1],
                           start_date=str(element[3]) + "-" + str(element[4]) + "-" + str(element[5]) + " 00:00",
                           end_date=str(element[6]) + "-" + str(element[7]) + "-" + str(element[8]) + " 00:00",
                           duration=2, progress=0.5, parent=key[1], type=key)
                t1.save()
                print(parents)
                print(element[0])
                if element[0] in parents:
                    for el in parents[element[0]]:
                        l1 = Link(source=str(t1.id[:3] + el), target=t1.id, type="0", lag=0)
                        l1.save()
    return render(request, 'myapp/schedule.html', {'json_list': json_list, 'total_height': (len(elements) + 2) * height,
                                                   'height': height, 'wbs1': unique_wbs1, 'result': result})


@csrf_exempt
def add_link(request):
    if not request.user.is_authenticated:
        return redirect('/login/')
    session = data_collect.authentication(url=NEW_URL, user=USER, password=PASS)
    add.edge(session, request.POST['from_din'], request.POST['to_din'], request.POST['weight'])
    session.close()
    return redirect('/new_graph/')


@csrf_exempt
def add_node(request):
    if not request.user.is_authenticated:
        return redirect('/login/')
    session = data_collect.authentication(url=NEW_URL, user=USER, password=PASS)
    add.node(session=session, node_din=request.POST['din'], node_name=request.POST['name'])
    session.close()
    return redirect('/new_graph/')


def new_gantt(request):
    return render(request, 'myapp/new_gantt.html')


@api_view(['GET'])
@authentication_classes([BasicAuthentication])
@permission_classes([AllowAny])
def data_list(request, offset):
    if request.method == 'GET':
        tasks = Task2.objects.all()
        links = Link.objects.all()
        task_data = TaskSerializer(tasks, many=True)
        link_data = LinkSerializer(links, many=True)
        return Response({
            "tasks": task_data.data,
            "links": link_data.data
        })


@api_view(['POST'])
@authentication_classes([BasicAuthentication])
@permission_classes([AllowAny])
def task_add(request):
    if request.method == 'POST':
        serializer = TaskSerializer(data=request.data)
        print(serializer)

        if serializer.is_valid():
            task = Task2(id=request.data['parent'][:3], text=request.data['text'],
                         start_date=request.data['start_date'],
                         end_date=request.data['end_date'],
                         duration=request.data['duration'], progress=request.data['progress'],
                         parent=request.data['parent'], type=request.data['parent'][:3])
            task.save()
            return JsonResponse({'action': 'inserted', 'tid': task.id})
        return JsonResponse({'action': 'error'})


@api_view(['PUT', 'DELETE'])
@authentication_classes([BasicAuthentication])
@permission_classes([AllowAny])
def task_update(request, pk):
    try:
        task = Task2.objects.get(pk=pk)
    except Task2.DoesNotExist:
        return JsonResponse({'action': 'error2'})

    if request.method == 'PUT':
        serializer = TaskSerializer(task, data=request.data)
        print(serializer)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse({'action': 'updated'})
        return JsonResponse({'action': 'error'})

    if request.method == 'DELETE':
        task.delete()
        return JsonResponse({'action': 'deleted'})


@api_view(['POST'])
@authentication_classes([BasicAuthentication])
@permission_classes([AllowAny])
def link_add(request):
    if request.method == 'POST':
        serializer = LinkSerializer(data=request.data)
        print(serializer)

        if serializer.is_valid():
            link = serializer.save()
            return JsonResponse({'action': 'inserted', 'tid': link.id})
        return JsonResponse({'action': 'error'})


@api_view(['PUT', 'DELETE'])
@authentication_classes([BasicAuthentication])
@permission_classes([AllowAny])
def link_update(request, pk):
    try:
        link = Link.objects.get(pk=pk)
    except Link.DoesNotExist:
        return JsonResponse({'action': 'error'})

    if request.method == 'PUT':
        serializer = LinkSerializer(link, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse({'action': 'updated'})
        return JsonResponse({'action': 'error'})

    if request.method == 'DELETE':
        link.delete()
        return JsonResponse({'action': 'deleted'})
