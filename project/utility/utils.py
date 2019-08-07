
# file containing common functions of both android and web
from bs4 import BeautifulSoup
import requests

def decode_meta_from_url(url):

    '''function to take meta tags from url'''

    r = requests.get(url)

    soup = BeautifulSoup(r.text,'html.parser')
    title = soup.find("meta", property="og:title")
    image=soup.find("meta",property="og:image")
    description=soup.find("meta",property="og:description")
    url=soup.find("meta",property="og:url")
    og_tags={}
    if title['content']:
        og_tags['title']=title['content']
    else:
        og_tags['title']=''

    if image['content']:
        og_tags['image'] = image['content']
    else:
        og_tags['image'] = ''

    if description['content']:
        og_tags['description'] = description['content']
    else:
        og_tags['description'] = ''

    if url['content']:
        og_tags['url']=url['content']
    else:
        og_tags['url']=''

    return og_tags

