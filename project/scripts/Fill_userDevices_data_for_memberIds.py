import json, time

from togther.models import (ModelUtilities, userDevices, Members)

def get_json_data_from_file(json_file):
    """
        open file and return parsed json data (file should be in json format)
    """

    with open(json_file) as f:
        data = json.load(f)
        return data
    
def fill_userDevices_data(members_data: list):
    """
        members_data: list of dict with keys: x_member_id, platform_code, version_code

        This function will create or update userDevices model for each member_id
    """

    if not isinstance(members_data, list):
        return
    
    for member_data in members_data:
        
        member_id = member_data.get("x_member_id")
        platform_code = member_data.get("platform_code")
        version_code = member_data.get("version_code")
        
        member = ModelUtilities.get_model_filter(Members, {"member_id": member_id})
        
        if member:
            filter_dict = {"user_id": member_id, "mobile_os": "Android"}
            update_dict = {"platform_code": platform_code, "version_code": version_code}

            _, created = ModelUtilities.update_or_create_model(userDevices, filter_dict, update_dict)

            if created: 
                print("Instance created for member_id: ", member_id)
            
            else:
                print("Instance updated for member_id: ", member_id)

        else:
            print("member not found: ", member_id)

def run_script():

    # JSON file path relative to scripts folder
    json_file = "scripts/members_json_data.json"
    json_data = get_json_data_from_file(json_file)

    start_time = time.time()
    fill_userDevices_data(json_data)
    end_time = time.time()

    print("Time taken: ", end_time - start_time)

run_script()
if __name__ == "__main__":
    run_script()
