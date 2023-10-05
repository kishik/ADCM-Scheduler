import os
import requests
from urllib.parse import urlencode
from fastapi import FastAPI
from pydantic import BaseModel
import gdown
import re


class Project(BaseModel):
    name: str
    link: str

app = FastAPI()


@app.post("/")
async def deploy_project(project: Project):
    k = 'https://drive.google.com/drive/folders/1BMz4mDAzFrxV3SkztJVD16clfWRKZ7Uc?usp=sharing'
    # match = re.search(r'd/.*/view', str(k)) 
    # print(match[0][2:-5] if match else 'Not found')
    url = f"{k[:-12]}"
    print(url)
    gdown.download_folder(url, quiet=True, use_cookies=False, output=f'{project.name}')

    # os.system('wget --no-check-certificate \'https://docs.google.com/uc?export=download&id=FILEID\' -O FILENAME')
    os.system(f'node ./xeokit-bim-viewer-app/createProject.js -p {project.name} -s ../{project.name}/**/*.ifc')
    return 200