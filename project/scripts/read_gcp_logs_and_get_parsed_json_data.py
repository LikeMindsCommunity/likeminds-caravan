import json, time

def get_textPayload_from_gcp_log(log):

    try:

        textPayload = log.get("textPayload")

        if not textPayload:
            return ""
        
        #remove first 30 characters from textPayload 
        textPayload = textPayload[30:]

        #convert string to json
        jsonPayload = json.loads(textPayload)

    except Exception as e:
        print("Error getting textPayload: ", e)
        jsonPayload = {}

    return jsonPayload

def get_headers_from_gcp_log(log):

    try:
        
        textPayload = get_textPayload_from_gcp_log(log)

        # get headers from textPayload
        headers = textPayload["text"]["request"]["headers"]

    except Exception as e:
        print("Error getting headers: ", e)
        headers = {}

    return headers

def get_members_data_for_userDevices_from_logs(json_data):
  
    userDevices_data = []
    member_ids = set()

    for log in json_data:   

        # get headers from log
        headers = get_headers_from_gcp_log(log)

        if not headers:
            continue
        
        member_data = {}

        for key, value in headers.items():

            if key == "x_member_id":
                
                # if member_id already exists in member_ids set then break
                if value in member_ids:
                    break
                else:
                    member_ids.add(value)

            if key in ["x_member_id", "platform_code", "version_code"]:
                member_data[key] = value
        
        # If member_data is not empty then append it to userDevices_data
        if member_data:
            userDevices_data.append(member_data)
        
        print("Member Data: ", member_data)

    print("Total members_data parsed: ", len(userDevices_data))

    return userDevices_data

def open_json_file_and_get_data(filepath):

    try:
        with open(filepath) as f:
            data = json.load(f)

            print("JSON file opened: ", filepath)

            return data
        
    except Exception as e:
        print("Error opening json file: ", e)
        return None
    
def dump_json_data_to_file(json_data, file_path: str = "output.json"):

    try:
        with open(file_path, "w") as f:
            json.dump(json_data, f)

            print("JSON data dumped to file: ", file_path)

    except Exception as e:
        print("Error dumping json data to file: ", e)


def run_script():

    start_time = time.time()

    # JSON file path relative to project directory
    input_file = "scripts/input.json"

    # Output file path relative to project directory
    output_file = "scripts/output.json"
    
    # Open JSON file and get data
    json_logs = open_json_file_and_get_data(input_file)

    # Filter JSON data and get required data
    members_data_for_userDevices = get_members_data_for_userDevices_from_logs(json_logs)

    dump_json_data_to_file(members_data_for_userDevices, output_file)

    end_time = time.time()

    print("Time taken: ", end_time - start_time)


if __name__ == "__main__":
    run_script()

