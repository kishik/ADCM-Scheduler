import json
import re
from datetime import timedelta, datetime

import pandas as pd
import requests
from asgiref.sync import sync_to_async
from django.http import HttpResponseRedirect, HttpResponseNotFound, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import UpdateView, DetailView
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import AllowAny

from myapp.serializers import TaskSerializer
from myapp.serializers import LinkSerializer
import myapp.graph_creation.yml as yml
from myapp.forms import UploadFileForm, RuleForm, WbsForm, AddNode, AddLink
from django.views.generic.edit import FormView
from .forms import FileFieldForm
from myapp.models import URN, ActiveLink, Rule, Wbs, Link, Task2
from .gantt import data_collect, net_hierarhy
from .graph_creation import add, neo4jexplorer

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
import asyncio
import httpx

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
    # user_graph = neo4jexplorer.Neo4jExplorer(uri=NEW_URL)
    # try:
    #     user_graph.restore_graph()
    # except Exception:
    #     print("passed")
    context = {'form': UploadFileForm(), 'url': NEW_URL, 'user_graph': USER, 'pass': PASS, 'link': AddLink(),
               'node': AddNode()}
    return render(request, 'myapp/hist_graph.html', context)


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
    project = ActiveLink.objects.filter(userId=request.user.id).last().projectId
    form = FileFieldForm()
    return render(request, "myapp/urn_index.html", {"urns": urns, "project": project, 'form': form})


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


def graph_from_csv(file: str = 'plan.csv') -> list:
    df = pd.read_csv(file, dtype={'din': str})
    # df = df.filter(items=['title', 'level', 'count'])
    df.fillna(0, inplace=True)

    df.rename(columns={"title": "wbs1",
                       "level": "wbs2",
                       "count": "wbs3",
                       "din": "wbs3_id",
                       "type": "name",
                       "volume": "value",
                       },
              inplace=True)
    df['wbs'] = df.wbs1 + df.wbs3_id

    dins = set(df.wbs3_id)

    data = df.to_dict('records')
    return data


@csrf_exempt
def upload_gantt(request):
    """
    Загрузка графа в виде файла в исторический граф
    :param request:
    :return:
    """
    if not request.user.is_authenticated:
        return redirect('/login/')

    if request.method == 'POST':
        # handle_uploaded_file(request.FILES['file'])
        # print('works')
        files = request.FILES.getlist('file_field')

        dins = set()
        global graph_data
        graph_data = []
        for f in files:
            # Do something with each file.
            graph_data.extend(net_hierarhy.ifc_parse(f.temporary_file_path()))
            print(f)
        user_graph = neo4jexplorer.Neo4jExplorer(uri=URL)
        try:
            user_graph.restore_graph()
        except Exception as e:
            print('views.py 352', e.args)
        user_graph.create_new_graph_algo(dins)

        return render(request, 'myapp/volumes.html', {
            "myJson": graph_data,
        })

    return redirect('/schedule/')


class FileFieldFormView(FormView):
    form_class = FileFieldForm
    template_name = 'myapp/new_gantt.html'  # Replace with your template.
    success_url = '/schedule/'  # Replace with your URL or reverse(). "upload_gantt"

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        files = request.FILES.getlist('file_field')
        if form.is_valid():
            for f in files:
                # Do something with each file.
                print(f)
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


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
        request.session['model'] = urn.urn
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
    request_url = 'http://4d-model.acceleration.ru:8000/acc/get_spec/{0}/project/{1}/model/{2}'
    if request.session['wbs'] != 0:
        res = requests.get(request_url.format(request.session['specs'], project.projectId, URN.objects.get(
            type=Wbs.objects.get(id=request.session['wbs']).docsdiv).urn))
        print(res.request.url)
    else:
        for wbs in Wbs.objects.all():
            print(URN.objects.get(
                type=wbs.docsdiv).urn)
            res = requests.get(request_url.format(wbs.specs[2:-2], project.projectId, URN.objects.get(
                type=wbs.docsdiv).urn))
            print(res.request.url)
            try:
                res = res.json()
            except:
                continue
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
        temp = el['wbs1']
        el['wbs1'] = el['wbs2']
        el['wbs2'] = el['wbs3_id']
        el['wbs3_id'] = el['wbs3']
        el['wbs3'] = temp
        el["wbs"] = str(el["wbs1"]) + str(el["wbs3_id"])
        dins.add(el["wbs3_id"])

    # add async
    user_graph = neo4jexplorer.Neo4jExplorer(uri=URL)
    # тут ресторю в свой граф из эксель
    time_now = datetime.now()
    try:
        user_graph.restore_graph()
    except Exception as e:
        print('views.py 352', e.args)
    print(datetime.now() - time_now)
    # заменить функцией copy
    # graph_copy.graph_copy(authentication(url=NEW_URL, user=NEW_USER, password=NEW_PASS),
    #                       authentication(url=URL, user=USER, password=PASS))
    #
    global graph_data
    graph_data = myJson['data']
    time_now = datetime.now()
    user_graph.create_new_graph_algo(dins)
    print(datetime.now() - time_now)
    print(myJson['data'])
    myJson['data'] = sorted(myJson['data'], key=lambda x: (x['wbs1'], x['wbs2'], x['wbs3_id']))
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


class WbsUpdateView(UpdateView):
    model = Wbs
    fields = ['wbs_code', 'docsdiv', 'wbs1', 'wbs2', 'wbs3', 'specs']
    template_name = 'myapp/wbs_edit.html'

    # def form_valid(self, form):
    #     form.instance.userId = self.request.user
    #     form.instance.isActive = True
    #     return super().form_valid(form)


# def sdr_edit(request, id):
#     """
#     Изменение SDR
#     :param request:
#     :param id:
#     :return:
#     """
#     if not request.user.is_authenticated:
#         return redirect('/login/')
#     try:
#         sdr = Wbs.objects.get(id=id)
#         if request.method == "POST":
#             sdr.wbs_code = request.POST.get("wbs_code")
#             sdr.docsdiv = request.POST.get("docsdiv")
#             sdr.wbs1 = request.POST.get("wbs1")
#             sdr.wbs2 = request.POST.get("wbs2")
#             sdr.wbs3 = request.POST.get("wbs3")
#             sdr.specs = request.POST.get("specs")
#             sdr.isActive = request.POST.get("isActive")
#             sdr.userId = request.POST.get("userId")
#             sdr.save()
#             return HttpResponseRedirect("/urn_index/")
#         else:
#             return render(request, "myapp/sdr_edit.html", {"sdr": sdr})
#     except Wbs.DoesNotExist:
#         return HttpResponseNotFound("<h2>SDR not found</h2>")


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


class ArticleDetailView(DetailView):
    model = Rule


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
    if request.method == "POST":
        rule = Rule()
        rule.name = request.POST.get("name")
        rule.names = request.POST.get("names")
        rule.fields = request.POST.get("fields")
        rule.unique_name = request.POST.get("unique_name")
        rule.filters = request.POST.get("filters")
        rule.group_by = request.POST.get("group_by")
        rule.sum_by = request.POST.get("sum_by")
        rule.operations = request.POST.get("operations")
        rule.isActive = True
        rule.userId = request.user.id
        rule.save()

    return render(request, "myapp/rule.html", {"form": form, "families": families_all})


class RuleUpdateView(UpdateView):
    model = Rule
    fields = ['names', 'fields', 'unique_name', 'filters', 'group_by', 'sum_by', 'operations']
    template_name = 'myapp/rule_edit.html'


# def rule_edit(request, id):
#     """
#     Изменение кгду
#     :param request:
#     :param id:
#     :return:
#     """
#     if not request.user.is_authenticated:
#         return redirect('/login/')
#     try:
#         rule = Rule.objects.get(id=id)
#         if rule.userId != request.user.id:
#             return HttpResponseNotFound("<h2>It's not your URN</h2>")
#         if request.method == "POST":
#             rule = Rule()
#             rule.name = request.POST.get("name")
#             rule.names = request.POST.get("names")
#             rule.fields = request.POST.get("fields")
#             rule.unique_name = request.POST.get("unique_name")
#             rule.filters = request.POST.get("filters")
#             rule.group_by = request.POST.get("group_by")
#             rule.sum_by = request.POST.get("sum_by")
#             rule.operations = request.POST.get("operations")
#             rule.isActive = True
#             rule.userId = request.user.id
#             rule.save()
#             return HttpResponseRedirect("/rules/")
#         else:
#             return render(request, "myapp/rule_edit.html", {"form": rule})
#     except URN.DoesNotExist:
#         return HttpResponseNotFound("<h2>URN not found</h2>")


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
        return HttpResponseRedirect("/rules/")
    except Rule.DoesNotExist:
        return HttpResponseNotFound("<h2>Rule not found</h2>")


def hist_gantt(request):
    """
        Диаграмма Ганта для исторического графа
        :param request:
        :return:
        """
    if not request.user.is_authenticated:
        return redirect('/login/')
    session = data_collect.authentication(url=LAST_URL, user=USER, password=PASS)
    if 'hist_restored' not in request.session:
        user_graph = neo4jexplorer.Neo4jExplorer(uri=LAST_URL)
        user_graph.restore_graph()
        request.session['hist_restored'] = True
    Task2.objects.all().delete()
    Link.objects.all().delete()
    distances = data_collect.calculate_hist_distance(session=session)
    data_collect.saving_typed_edges(session)
    duration = 1
    data = data_collect.allNodes(session)
    data = sorted(data, key=lambda x: distances[x])
    for node in data:
        Task2(id=node, text=data_collect.get_name_by_din(session, node) + ' DIN-' + str(node),
              start_date=datetime.today() + timedelta(days=distances[node]),
              duration=duration).save()

    return render(request, 'myapp/new_gantt.html')


def schedule(request):
    """
    Диаграмма Ганта
    :param request:
    :return:
    """
    if not request.user.is_authenticated:
        return redirect('/login/')

    session = data_collect.authentication(url=URL, user=USER, password=PASS)
    # distances = data_collect.calculateDistance(session=session)
    distances = ()
    dins = []
    unique_wbs1 = set()
    global graph_data
    result = {}
    result_din = {}
    names = {}
    for el in graph_data:
        if el['wbs1'] not in result:
            result[el['wbs1']] = {}
            result_din[el['wbs1']] = {}
        if el['wbs2'] not in result[el['wbs1']]:
            result[el['wbs1']][el['wbs2']] = []
            result_din[el['wbs1']][el['wbs2']] = []
        if el['wbs3'] not in result[el['wbs1']][el['wbs2']]:
            result[el['wbs1']][el['wbs2']].append(el['wbs3_id'] + str(el['wbs3']))
            result_din[el['wbs1']][el['wbs2']].append(el['wbs3_id'])
        dins.append(el['wbs3_id'])
        names[el['wbs3_id'] + str(el['wbs3'])] = el['name']

    Task2.objects.all().delete()
    Link.objects.all().delete()

    data_collect.saving_typed_edges_with_wbs(session, result)
    created = set()
    prev_level = 0
    prev_building = None
    pre_pre_dur = 0
    for wbs1 in result.keys():
        if prev_building:
            pre_pre_dur = prev_building.duration = prev_level - pre_pre_dur
            prev_building.save()

        if not wbs1:
            continue
        wbs1_str = str(wbs1)
        if wbs1_str not in created:
            Task2(id=wbs1_str, text=wbs1,
                  # min(start_date of levels)
                  start_date=datetime.today() + timedelta(prev_level),
                  # duration = max([distances[din] for din in result[wbs1]])
                  duration=10).save()
            prev_building = Task2.objects.get(id=wbs1_str)
            created.add(wbs1_str)
        for wbs2 in result[wbs1].keys():
            if not wbs2:
                continue
            wbs2_str = str(wbs2)
            # здесь нужно считать дистанцию
            distances = data_collect.calculateDistance(session=session, dins=result_din[wbs1][wbs2])
            new_level = int(max(distances.values(), default=1))
            if (wbs1_str + wbs2_str) not in created:
                Task2(id=wbs1_str + wbs2_str, text=wbs2,
                      # min(start_date of levels)
                      start_date=datetime.today() + timedelta(prev_level),
                      # duration = max([distances[din] for din in result[wbs1]])
                      duration=new_level + 1 if distances and int(max(distances.values()) > 0) else 1,
                      parent=wbs1_str).save()
                created.add((wbs1_str + wbs2_str))

            for wbs3 in result[wbs1][wbs2]:
                if not wbs3:
                    try:
                        if wbs3 != 0:
                            pass
                    except:
                        continue

                wbs3_str = wbs3[:3]
                if wbs3_str not in distances:
                    Task2(id=wbs1_str + wbs2_str + wbs3, text=names[wbs3] + " DIN(" + wbs3_str + ")",
                          # min(start_date of levels)
                          start_date=datetime.today() + timedelta(prev_level),
                          # duration = max([distances[din] for din in result[wbs1]])
                          duration=1, parent=wbs1_str + wbs2_str).save()
                else:
                    Task2(id=wbs1_str + wbs2 + wbs3, text=names[wbs3] + " DIN(" + wbs3_str + ")",
                          # min(start_date of levels)
                          start_date=datetime.today() + timedelta(prev_level) + timedelta(distances[wbs3_str]),
                          # duration = max([distances[din] for din in result[wbs1]])
                          duration=1, parent=wbs1_str + wbs2_str).save()

            prev_level += new_level + 1
    prev_building.duration = prev_level - pre_pre_dur
    prev_building.save()
    session.close()
    # form = FileFieldForm()
    # context = {'form': form}
    return render(request, 'myapp/new_gantt.html')


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
