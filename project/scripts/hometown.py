import time
import xlrd
import sys
sys.path.append("..")
import psycopg2
from scripts.connection import get_connection
from utility.utils import get_city_address
from utility.utils import create_or_categorize_tag
from utility.pre_creation import pre_create_communities
import logging
info_logger=logging.getLogger("info_logger")
print("Hometown Insertion Script")

def read_excell_file():
    loc = ("scripts/tags_collabmates.xlsx")

    wb = xlrd.open_workbook(loc)
    homwtown=wb.sheet_by_name("L_Home Town")
    homwtown_list=[]

    for row in range(1, homwtown.nrows):
        homwtown_list.append(homwtown.cell_value(row,0))

    print("Hometowns are extracted from the list\n")
    return homwtown_list


def get_state_and_country(hometown_list):


    for hometown in hometown_list:

        location=get_city_address(city=hometown)
        city=location['city']
        state=location['state']
        country=location['country']
        tag_id=create_or_categorize_tag(hometown,"Legacy","Legacy_hometown")
        create_or_categorize_tag(city,"Geography","Geography_city")
        create_or_categorize_tag(state,"Geography","Geography_state")
        create_or_categorize_tag(country,"Geography","Geography_country")

        print(hometown," Tag created")
        info_logger.info("""%s created"""%(hometown))

        print(hometown,"tag Pre-creation started\n")
        info_logger.info("""%s hometown Pre-creation started"""%(hometown))

        if tag_id:
            pre_create_communities(tag_id=tag_id.id)
            print("Pre-creation completed for ",hometown)
            info_logger.info("""Pre-creation completed for %s\n"""%(hometown))






current_time = time.time()
hometown_list = read_excell_file()
get_state_and_country(hometown_list)
print("Executing time:")
diff=time.time() - current_time
print(time.time() - current_time)

info_logger.info("Executing time:")
info_logger.info(diff)