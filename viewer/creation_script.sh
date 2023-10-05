#!/bin/bash
git clone 'https://github.com/kishik/xeokit-bim-viewer-app.git' 'kishik-no-demo'
mv ./kishik-no-demo ./xeokit-bim-viewer-app
cd ./xeokit-bim-viewer-app
npm install
npm run build
# cd //
