import json


class JsonUtilities:

    @staticmethod
    def dump_json_data(json_data):
        json_string = None

        try:
            json_string = json.dumps(json_data)

        except Exception as e:
            json_string = None

        return json_string

    @staticmethod
    def load_json_data(json_string):
        json_data = {}

        try:
            json_data = json.loads(json_string)

        except Exception as e:
            json_data = {}

        return json_data
