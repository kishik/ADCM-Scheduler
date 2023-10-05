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
    k = project.link
    # match = re.search(r'd/.*/view', str(k)) 
    # print(match[0][2:-5] if match else 'Not found')
    url = f"{k[39:-12]}"
    print(f'https://drive.google.com/drive/folders/{url}')
    gdown.download_folder(f'https://drive.google.com/drive/folders/{url}', quiet=True, use_cookies=False, output=f'{project.name}')
    os.system('ls')
    # os.system('wget --no-check-certificate \'https://docs.google.com/uc?export=download&id=FILEID\' -O FILENAME')
    os.chdir('./xeokit-bim-viewer-app/')
    os.system(f'node ./createProject.js -p {project.name} -s ../{project.name}/**/*.ifc')
    return 200