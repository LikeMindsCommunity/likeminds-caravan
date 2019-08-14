# file containing common functions of both android and web
from bs4 import BeautifulSoup
import requests
from togther.models import *

def decode_meta_from_url(url):

    '''function to take meta tags from url'''

    r = requests.get(url)

    soup = BeautifulSoup(r.text,'html.parser')
    title = soup.find("meta", property="og:title")
    image=soup.find("meta",property="og:image")
    description=soup.find("meta",property="og:description")
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
    og_tags['url']=url
    return og_tags

def get_nominated_admin_details(community_id,email):
    '''fetching nominated promoter details from temp admin table'''
    community = get_object_or_404(Community, pk = community_id)
    details = temp_admin.objects.filter(community_id=community,email=email)
    if details:
        '''details are present,return s true'''
        print('details are present')
        return True
    else:
        '''details are not present, returns false'''
        print('details are not present')
        return False


def update_member_count(community_id):
    ''' update members count of a community , when a promoter or member joins a community '''
    community = Community.objects.get(id=community_id)
    # getting the count of members including admins in a community
    count = Members.objects.filter(community_id=community).filter(Q(state=1)|Q(state=2)|Q(state=4)|Q(state=7)).count()
    # updating count
    Community.objects.filter(id=community_id).update(members_count = count)
    return count



def set_user_tag(user_id, community_id):
    ''' function to set hidden tag for user '''
    community = Community.objects.get(id=community_id)
    iit_tag = Community_tags.objects.filter(community_id=community, tags_id=41)
    nsit_tag = Community_tags.objects.filter(community_id=community, tags_id=42)
    check = True
    # we have only two hidden tags now
    # if we have more hidden tags this function is gonna change
    if iit_tag:
        tag_id = 41
        check = check_user_tag(user_id=user_id, tag_id=tag_id)
    elif nsit_tag:
        tag_id = 42
        check = check_user_tag(user_id=user_id, tag_id=tag_id)
    if not check:
        user_tag = userinfo_tags()
        user_tag.user_id = user_id
        user_tag.tag_id = tag_id
        user_tag.save()
    return


def get_user_tag(user_id):
    ''' function to get user hidden tag '''
    user_tag = userinfo_tags.objects.all().filter(user_id=user_id)
    return user_tag


def get_or_create_tag(tag):
    ''' function to update city tag for user '''
    tag = tag.strip()
    try:
        tag = Tags.objects.get(category_name = tag)
    except:
        tag = Tags()
        tag.category_name = loc
        tag.state =1
        tag.save()
    return tag.id