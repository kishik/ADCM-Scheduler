from django.http import JsonResponse, HttpResponseRedirect, HttpResponseNotFound
from django.shortcuts import render, redirect
# Create your views here.
from django.views.decorators.csrf import csrf_exempt

import myapp.forms
from myapp.models import Work, URN, ActiveLink, Rule, Wbs
from .graph_creation import historical_graph_creation
from myapp.forms import UploadFileForm, RuleForm, WbsForm
import requests
import re
import json


def login(request):
    if not request.user.is_authenticated:
        return redirect('/login/')
    if not request.user.is_authenticated:
        return render(request, 'registration/login.html')


def get_works(request):
    if not request.user.is_authenticated:
        return redirect('/login/')
    return render(request, 'myapp/index1.html', {'works': Work.nodes.all()})


def works_index(request):
    if not request.user.is_authenticated:
        return redirect('/login/')
    works = Work.nodes.all()
    return render(request, 'myapp/index1.html', {
        'works': works
    })


def graph_show(request):
    if not request.user.is_authenticated:
        return redirect('/login/')
    nodes = []
    rels = []
    works = Work.nodes.all()

    for work in works:
        nodes.append({'id': work.id, 'name': work.name})

    return render(request, 'myapp/index1.html', {
        "nodes": nodes, "links": rels
    })


def work_in_progress(request):
    if not request.user.is_authenticated:
        return redirect('/login/')
    return render(request, 'myapp/building.html')


def graph(request):
    if not request.user.is_authenticated:
        return redirect('/login/')
    nodes = []
    rels = []
    works = Work.nodes.all()

    for work in works:
        nodes.append({'id': work.id, 'name': work.name})

        for job in work.incoming:
            print(job)
            rels.append({"source": job.id, "target": work.id})
        for job in work.outcoming:
            rels.append({"source": work.id, "target": job.id})
    print(rels)
    return JsonResponse({"nodes": nodes, "links": rels})


def work_by_id(request, id):
    if not request.user.is_authenticated:
        return redirect('/login/')
    print(id, "id")
    for node in Work.nodes.all():
        if int(id) == node.id:
            return JsonResponse({
                'id': node.id,
                'name': node.name,
            })
    # work = Work.nodes.get(id=int(id))


def search(request):
    if not request.user.is_authenticated:
        return redirect('/login/')
    try:
        q = request.GET["q"]
        print(q, "q")
        print(request.path)
    except KeyError:
        return JsonResponse([])
    goodNodes = []
    for node in Work.nodes.all():
        print(node.id)

        if int(q) == node.id:
            goodNodes.append(node)
            # return JsonResponse({
            #     'id': node.id,
            #     'name': node.name,
            # })
    # print(works[0].id, 'works')
    return JsonResponse([{
        'id': work.id,
        'name': work.name,

    } for work in goodNodes], safe=False)


def new_graph(request):
    if not request.user.is_authenticated:
        return redirect('/login/')
    context = {'form': UploadFileForm()}
    return render(request, 'myapp/test.html', context)


def model_load(request):
    if not request.user.is_authenticated:
        return redirect('/login/')
    return render(request, 'myapp/model_load.html')


def file_upload(request):
    if not request.user.is_authenticated:
        return redirect('/login/')
    return render(request, 'myapp/model_load.html')


def urn_show(request):
    if not request.user.is_authenticated:
        return redirect('/login/')
    urns = URN.objects.all()
    return render(request, "myapp/cdn_model.html", {"urns": urns, "user": request.user})


def urn_index(request):
    if not request.user.is_authenticated:
        return redirect('/login/')
    urns = URN.objects.all()
    return render(request, "myapp/urn_index.html", {"urns": urns})


# сохранение данных в бд
def urn_create(request):
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


# изменение данных в бд
def urn_edit(request, id):
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


# удаление данных из бд
def urn_delete(request, id):
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


def index(request):
    if not request.user.is_authenticated:
        return redirect('/login/')
    return render(request, 'myapp/WebGL Builds/index.html')


@csrf_exempt
def upload(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    if request.method == 'POST':
        print(request.FILES['file'])
        historical_graph_creation.main(request.FILES['file'])
        # if form.is_valid():
        #     print(request.FILES['file'])
        # return redirect('/new_graph')

    return redirect('/new_graph/')


def families(request):
    if not request.user.is_authenticated:
        return redirect('/login/')
    families_all = Rule.objects.all()
    return render(request, "myapp/families.html", {"families": families_all})


def model(request, id):
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
        # if request.method == "POST":
        #     urn.type = request.POST.get("type")
        #     urn.urn = request.POST.get("urn")
        #     urn.save()
        #     return HttpResponseRedirect("/urn_index/")
        # else:
        #     project_id = """"""
        #     # return render(request, "myapp/urn_edit.html", {"urn": urn})
        #     res = requests.get('https://4d-model.acceleration.ru:8000/acc/viewer/project/' +
        #                        project_id + '/model/' + model_id)
        #     json = res.json()

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
        # if request.method == "POST":
        #     urn.type = request.POST.get("type")
        #     urn.urn = request.POST.get("urn")
        #     urn.save()
        #     return HttpResponseRedirect("/urn_index/")
        # else:
        #     project_id = """"""
        #     # return render(request, "myapp/urn_edit.html", {"urn": urn})
        #     res = requests.get('https://4d-model.acceleration.ru:8000/acc/viewer/project/' +
        #                        project_id + '/model/' + model_id)
        #     json = res.json()

    except URN.DoesNotExist:
        return HttpResponseNotFound("<h2>URN not found</h2>")


def settings(request):
    project = ActiveLink.objects.filter(userId=request.user.id).last()
    return render(request, 'myapp/settings.html', {
        "userId": request.user.id,
        "projectId": project.projectId,
        "modelId": project.modelId
    })


@csrf_exempt
def saveModel(request):
    link = ActiveLink()
    link.userId = request.user.id
    string = request.POST.get("link")
    project = re.search(r'projects.*folderUrn', string)
    project = project[0][9:-10]
    link.projectId = project
    model = re.search(r'entityId=.*&viewModel', string)
    model = model[0][9:-10]
    link.modelId = model
    # print(string)
    # print(project, model)
    link.save()
    return redirect('/settings/')


def volumes(request):
    project = ActiveLink.objects.filter(userId=request.user.id).last()
    res = requests.get('http://4d-model.acceleration.ru:8000/acc/get_spec/' +
                       request.session['specs'] + '/project/' + project.projectId +
                       '/model/' + request.session['model'])

    myJson = res.json()
    myJson = json.loads(myJson)
    # myJson = json.loads(res.json())
    # print(type(myJson))
    # print(myJson['data'])
    # for el in myJson['data']:

    # for k, v in myJson['data'].items():
    #     print(k, v)
    # project = re.search(r'projects.*folderUrn', myJson)

    #                        project_id + '/model/' + model_id)
    #     json = res.json()

    # Import `xlwt`
    import xlwt

    # Initialize a workbook
    book = xlwt.Workbook(encoding="utf-8")

    # Add a sheet to the workbook
    sheet1 = book.add_sheet("Python Sheet 1")
    if len(myJson['data']) > 0:
        i = 0
        for k, v in myJson['data'][0].items():
            sheet1.write(0, i, k)
            i = i + 1
        i = 1
        j = 0
        for element in myJson['data']:
            for k, v in element.items():
                sheet1.write(i, j, v)
                j = j + 1
            j = 0
            i = i + 1
        name = r"C:\Users\kishi\PycharmProjects\protodjango\spreadsheet.xls"
        book.save(name)
    # Write to the sheet of the workbook
    # sheet1.write(0, 0, "This is the First Cell of the First Sheet")
    #
    # # Save the workbook
    # book.save("spreadsheet.xls")

    # for i in range(len(myJson['data'])):
    #     myJson['data'][i][id] = i
    print(myJson['data'])
    return render(request, 'myapp/volumes.html', {
        "myJson": myJson['data'],
    })



def sdrs(request):
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

    SINARA_WBS = [
        {
            'wbs_code': "СМР.1.КЖ.0.",
            'docsdiv': "KJ",
            'wbs1': "СМР",
            'wbs2': "Конструкции железобетонные",
            'wbs3': "Ниже отм. 0.0",
            'specs': ["SIN_KJ_base"]
        },
        {
            'wbs_code': "СМР.1.КЖ.1.",
            'docsdiv': "KJ",
            'wbs1': "СМР",
            'wbs2': "Конструкции железобетонные",
            'wbs3': "Выше отм. 0.0",
            'specs': ["SIN_KJ_karkas"]
        },
        {
            'wbs_code': "СМР.2.АС.1.",
            'docsdiv': "AR",
            'wbs1': "СМР",
            'wbs2': "Архитектурно-строительные решения",
            'wbs3': "Устройство наружных стен",
            'specs': ["SIN_AR_ext_walls"]
        },
        {
            'wbs_code': "СМР.2.АС.2.",
            'docsdiv': "AR",
            'wbs1': "СМР",
            'wbs2': "Архитектурно-строительные решения",
            'wbs3': "Устройство перегородок",
            'specs': ["SIN_AR_int_walls"]
        },
        {
            'wbs_code': "СМР.2.АС.3.",
            'docsdiv': "AR",
            'wbs1': "СМР",
            'wbs2': "Архитектурно-строительные решения",
            'wbs3': "Устройство кровель",
            'specs': ["SIN_AR_roofs"]
        },
        {
            'wbs_code': "СМР.2.АС.3.",
            'docsdiv': "AR",
            'wbs1': "СМР",
            'wbs2': "Архитектурно-строительные решения",
            'wbs3': "Устройство фасадов",
            'specs': ["SIN_AR_facade"]
        },
        {
            'wbs_code': "СМР.2.АС.4.",
            'docsdiv': "AR",
            'wbs1': "СМР",
            'wbs2': "Архитектурно-строительные решения",
            'wbs3': "Устройство окон",
            'specs': ["SIN_AR_windows"]
        },
        {
            'wbs_code': "СМР.2.АС.5.",
            'docsdiv': "AR",
            'wbs1': "СМР",
            'wbs2': "Архитектурно-строительные решения",
            'wbs3': "Устройство витражей",
            'specs': ["SIN_stained"]
        },
        {
            'wbs_code': "СМР.2.АС.6.",
            'docsdiv': "AR",
            'wbs1': "СМР",
            'wbs2': "Черновая отделка",
            'wbs3': "Черновая отделка стен",
            'specs': ["SIN_wall_finish"]
        },
        {
            'wbs_code': "СМР.2.АС.7.",
            'docsdiv': "AR",
            'wbs1': "СМР",
            'wbs2': "Черновая отделка",
            'wbs3': "Устройство полов",
            'specs': ["SIN_AR_floor"]
        },
        {
            'wbs_code': "СМР.2.АС.8.",
            'docsdiv': "AR",
            'wbs1': "СМР",
            'wbs2': "Черновая отделка",
            'wbs3': "Устройство потолков",
            'specs': ["SIN_ceiling"]
        },
        {
            'wbs_code': "СМР.3.ОВ.1.",
            'docsdiv': "OV",
            'wbs1': "СМР",
            'wbs2': "Системы вентиляции",
            'wbs3': "Монтаж воздуховодов",
            'specs': ["SIN_OV_ducts"]
        },
        {
            'wbs_code': "СМР.3.ОВ.2.",
            'docsdiv': "OV",
            'wbs1': "СМР",
            'wbs2': "Система отопления",
            'wbs3': "Монтаж трубопроводов",
            'specs': ["SIN_pipes"]
        },
        {
            'wbs_code': "СМР.3.ОВ.3.",
            'docsdiv': "OV",
            'wbs1': "СМР",
            'wbs2': "Системы отопления и вентиляции",
            'wbs3': "Монтаж оборудования",
            'specs': ["SIN_equip"]
        },
        {
            'wbs_code': "СМР.3.ПТ.1.",
            'docsdiv': "PT",
            'wbs1': "СМР",
            'wbs2': "Система пожаротушения",
            'wbs3': "Монтаж трубопроводов",
            'specs': ["SIN_pipes"]
        },
        {
            'wbs_code': "СМР.3.ПТ.2.",
            'docsdiv': "PT",
            'wbs1': "СМР",
            'wbs2': "Система пожаротушения",
            'wbs3': "Монтаж оборудования",
            'specs': ["SIN_equip"]
        },
        {
            'wbs_code': "СМР.3.ЭМ.1.",
            'docsdiv': "EM",
            'wbs1': "СМР",
            'wbs2': "Система электроснабжения",
            'wbs3': "Прокладка лотковых трасс",
            'specs': ["SIN_EM_lotki"]
        },
        {
            'wbs_code': "СМР.3.ЭМ.2.",
            'docsdiv': "EM",
            'wbs1': "СМР",
            'wbs2': "Система электроснабжения",
            'wbs3': "Монтаж оборудования",
            'specs': ["SIN_EM_equip"]
        },
    ]


def sdr(request, id):
    if not request.user.is_authenticated:
        return redirect('/login/')
    try:
        wbs = Wbs.objects.get(id=id)
        if wbs.userId != request.user.id:
            return HttpResponseNotFound("<h2>It's not your WBS</h2>")
        request.session['wbs'] = id
        request.session['specs'] = wbs.specs[2:-2]
        # print(request.session['specs'])
        return redirect('/volumes/')
        # if request.method == "POST":
        #     urn.type = request.POST.get("type")
        #     urn.urn = request.POST.get("urn")
        #     urn.save()
        #     return HttpResponseRedirect("/urn_index/")
        # else:
        #     project_id = """"""
        #     # return render(request, "myapp/urn_edit.html", {"urn": urn})
        #     res = requests.get('https://4d-model.acceleration.ru:8000/acc/viewer/project/' +
        #                        project_id + '/model/' + model_id)
        #     json = res.json()

    except URN.DoesNotExist:
        return HttpResponseNotFound("<h2>WBS not found</h2>")


def sdr_delete(request, id):
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


def rules(request):
    if not request.user.is_authenticated:
        return redirect('/login/')
    urns = URN.objects.all()
    return render(request, "myapp/urn_index.html", {"urns": urns})


def rule_create(request):
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
            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:
            return HttpResponseRedirect('/families/')

    return render(request, "myapp/rule.html", {"form": form, "families": families_all})


def rule_delete(request, id):
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
