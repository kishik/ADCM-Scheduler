def excel_upload(request):
    if request.method == "POST":
        print('hi')
        path = request.FILES['excel_file']
        data = pd.read_excel(
            path,
            dtype=str,
            # usecols="A:F"
            # skiprows=[0, 1, 2, 3],
            # index_col=3,
        )
        data = data[data["Шифр"].str.startswith("1.") == False]
        data = data[data["Шифр"].str.startswith("ОКЦ") == False]
        info = 'Проект,Смета,Шифр,НаименованиеПолное'

        # обработка excel

        myJson = {
            "data": [
                {

                    "wbs1": volume['Проект'] or "None",
                    "wbs2": volume['Смета'] or "None",
                    "wbs3_id": str(volume['Шифр']) or "None",
                    "wbs3": str(volume['Шифр']) or "None",

                    "name": volume['НаименованиеПолное'] or "None",
                    "value": 0,
                    "wbs": ''.join((re.search(r'№\S*', volume['Смета']).group(0)[1:], '.', str(volume['Пункт']))),
                    # "wbs3_id": ''.join((item.building or "", item.storey.name if item.storey else "", item.name)),
                    'number': int(re.search(r'№\S*', volume['Смета']).group(0)[1:].split('-')[0])
                }
                for item, volume in data.iterrows()
            ]
        }

        dins = {key['wbs3'] for key in myJson['data']}
        # add async
        user_graph = neo4jexplorer.Neo4jExplorer(uri=URL)
        driver_hist = GraphDatabase.driver('neo4j+s://0fdb78bd.databases.neo4j.io:7687', auth=(USER, PASS))
        driver_user = GraphDatabase.driver(URL, auth=(USER, '231099'))
        # тут ресторю в свой граф из эксель
        time_now = datetime.now()
        try:
            print(os.getcwd())
            graph_copy(driver_hist.session(), driver_user.session())
        except Exception as e:
            print("views.py 402", e.args)
        user_graph.create_new_graph_algo(dins)

        global graph_data
        graph_data = myJson["data"]
        graph_data.sort(
            key=lambda x: (
                x.get("number", "") or "",
                x.get("wbs3_id", "") or "",
            )
        )
        return render(
            request,
            "myapp/excel_table.html",
            {
                "myJson": myJson["data"],
            }
        )

    return render(
        request,
        "myapp/excel.html"
    )