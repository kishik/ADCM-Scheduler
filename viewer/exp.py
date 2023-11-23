import re
import gdown

# a file
k = 'https://drive.google.com/drive/folders/1BMz4mDAzFrxV3SkztJVD16clfWRKZ7Uc?usp=sharing'
# match = re.search(r'd/.*/view', str(k)) 
# print(match[0][2:-5] if match else 'Not found')
url = f"{k[:-12]}"
print(url)
gdown.download_folder(url, quiet=True, use_cookies=False)
