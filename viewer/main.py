import os
import requests
from urllib.parse import urlencode
from fastapi import FastAPI
from pydantic import BaseModel
import gdown
import re
import shutil
import json
import os
import pickle

from new_loader.ifc_to_nx_converter import IfcToNxConverter
from new_loader.nx_to_neo4j_converter import NxToNeo4jConverter
from new_loader.create_group_graph import create_group_graph


class Project(BaseModel):
    name: str
    link: str

app = FastAPI()


@app.post("/")
async def deploy_project(project: Project):
    k = project.link
    # match = re.search(r'd/.*/view', str(k)) 
    # print(match[0][2:-5] if match else 'Not found')
    url = f"{k[39:-12]}"
    print(f'https://drive.google.com/drive/folders/{url}')
    gdown.download_folder(f'https://drive.google.com/drive/folders/{url}', quiet=True, use_cookies=False, output=f'{project.name}')
    # os.system('ls')
    # os.system('wget --no-check-certificate \'https://docs.google.com/uc?export=download&id=FILEID\' -O FILENAME')
    os.chdir('./xeokit-bim-viewer-app/')
    os.system(f'node ./createProject.js -p {project.name} -s ../{project.name}/**/*.ifc')
    os.chdir('..')
    files = [f for f in os.listdir(f'./{project.name}')]
    for file in files:
        print(f'./{project.name}/{file}')
        print(f'./xeokit-bim-viewer-app/data/projects/{project.name}/models/{file[:-4]}/source/geometry.ifc')
        shutil.move(f'./{project.name}/{file}', f'./xeokit-bim-viewer-app/data/projects/{project.name}/models/{file[:-4]}/source/geometry.ifc')
    return 200


@app.get("/load/{project_name}")
async def deploy_project(project_name: str):
    path = f'./xeokit-bim-viewer-app/data/projects/{project_name}/models/'

    create_group_graph()
    nx_exp = IfcToNxConverter()
    nx_exp.create_net_graph(path)

    neo4j_exp = NxToNeo4jConverter()
    G = nx_exp.get_net_graph()
    neo4j_exp.create_neo4j(G)

    neo4j_exp.close()
    return json.dumps(neo4j_exp.get_dict(), indent=4, default=str)
