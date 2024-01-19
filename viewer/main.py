from fastapi import FastAPI
from pydantic import BaseModel
import gdown
import shutil
import json
import os
from fastapi.responses import JSONResponse
from new_loader.ifc_to_neo4j import IfcToNeo4jConverter
from new_loader.create_group_graph import create_group_graph


class Project(BaseModel):
    name: str
    link: str


# need to execute in separate docker in future
create_group_graph()

app = FastAPI()

path_to_explorer = dict()


@app.post("/")
async def deploy_project(project: Project):
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
