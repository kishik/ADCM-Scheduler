from fastapi import FastAPI
from pydantic import BaseModel
import gdown
import shutil
import json
import os
from fastapi.responses import JSONResponse
from new_loader.ifc_to_neo4j import IfcToNeo4jConverter
import requests


class Project(BaseModel):
    name: str
    link: str

class ADCMProject(BaseModel):
    id: int
    name: str
    link: str


app = FastAPI()

path_to_explorer = dict()


@app.post("/")
async def deploy_project(project: Project):
    os.chdir('/app/')
    k = project.link
    # match = re.search(r'd/.*/view', str(k)) 
    # print(match[0][2:-5] if match else 'Not found')
    url = f"{k[39:-12]}"
    print(f'https://drive.google.com/drive/folders/{url}')
    gdown.download_folder(f'https://drive.google.com/drive/folders/{url}', quiet=True, use_cookies=False,
                          output=f'{project.name}')
    # os.system('ls')
    # os.system('wget --no-check-certificate \'https://docs.google.com/uc?export=download&id=FILEID\' -O FILENAME')
    os.chdir('./xeokit-bim-viewer-app/')
    os.system(f'node ./createProject.js -p {project.name} -s ../{project.name}/**/*.ifc')
    os.chdir('..')
    files = [f for f in os.listdir(f'./{project.name}')]
    for file in files:
        print(f'./{project.name}/{file}')
        print(f'./xeokit-bim-viewer-app/data/projects/{project.name}/models/{file[:-4]}/source/geometry.ifc')
        shutil.move(f'./{project.name}/{file}',
                    f'./xeokit-bim-viewer-app/data/projects/{project.name}/models/{file[:-4]}/source/geometry.ifc')

    neo4j_exp = IfcToNeo4jConverter()
    path = f'./xeokit-bim-viewer-app/data/projects/{project.name}/models/'
    neo4j_exp.create(path)
    path_to_explorer[path] = neo4j_exp
    return 200


@app.get("/load/{project_name}")
async def get_nodes(project_name: str):
    path = f'./xeokit-bim-viewer-app/data/projects/{project_name}/models/'
    neo4j_exp = path_to_explorer.get(path)

    return JSONResponse(content=json.dumps(neo4j_exp.get_nodes()))
    # neo4j_exp.close()


@app.get("/links/{project_name}")
async def get_links(project_name: str):
    path = f'./xeokit-bim-viewer-app/data/projects/{project_name}/models/'
    neo4j_exp = path_to_explorer.get(path)

    return JSONResponse(content=json.dumps(neo4j_exp.get_edges()))


@app.get("/copy/{project_id}")
async def load_project(project_id: int):
    os.chdir('/app/')
    if os.path.isdir(f'./{project_id}'):
        shutil.rmtree(f'./{project_id}')
    if os.path.isdir(f'./xeokit-bim-viewer-app/data/projects/{project_id}/'):    
        # shutil.rmtree(f'./xeokit-bim-viewer-app/data/projects/{project_id}/')
        os.chdir('./xeokit-bim-viewer-app/')
        os.system(f'node deleteProject.js -p {project_id}')
        os.chdir('/app/')
    
    os.mkdir(f'{project_id}')
    # download project
    os.chdir(f'./{project_id}/')
    r = requests.get(f'http://51.250.41.223:8880/projects/info/{project_id}')
    for el in r.json()['models']:
        m = requests.get(el['ifc'], allow_redirects=True)
        open(f'{el["name"]}.ifc', 'wb').write(m.content)
    os.chdir('/app/')

    os.chdir('./xeokit-bim-viewer-app/')
    os.system(f'node ./createProject.js -p {project_id} -s ../{project_id}/**/*.ifc')
    os.chdir('/app/')
    files = [f for f in os.listdir(f'./{project_id}')]
    for file in files:
        # print(f'./{project.name}/{file}')
        # print(f'./xeokit-bim-viewer-app/data/projects/{project.name}/models/{file[:-4]}/source/geometry.ifc')
        shutil.move(f'./{project_id}/{file}',
                    f'./xeokit-bim-viewer-app/data/projects/{project_id}/models/{file[:-4]}/source/geometry.ifc')

    neo4j_exp = IfcToNeo4jConverter()
    path = f'./xeokit-bim-viewer-app/data/projects/{project_id}/models/'
    neo4j_exp.create(path)
    path_to_explorer[path] = neo4j_exp
    return 200
