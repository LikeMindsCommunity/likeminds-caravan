
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

    try:
        og_tags['title']=title['content']
    except:
        pass

    try:
        og_tags['image'] = image['content']
    except:
        pass

    try:
        og_tags['description'] = description['content']
    except:
        pass

    try:
        og_tags['url']=url['content']
    except:
        pass


    return og_tags

