import re
import json


class StringUtilities:

    @staticmethod
    def get_string_from_integer(number: int, return_default: str = '') -> str:

        try:
            return str(number)
        except (ValueError, TypeError):
            return return_default

    @staticmethod
    def get_boolean_from_string(string, default: bool = False) -> bool:

        if string == "true":
            return True
        
        elif string == "false":
            return False
        
        return default

    @staticmethod
    def replace_character_in_string(string, char_to_replace, replacement_char):

        return string.lower().replace(char_to_replace, replacement_char)

    @staticmethod
    def replace_in_string(replace_str: str, replacement_str: str, input_str: str) -> str:
        """
        replaces all instances of replace_str with replacement_str
        in input_str
        """
        return re.sub(replace_str, replacement_str, input_str)

    @staticmethod
    def get_list_from_string(string: str, default: list = None):
        try:
            return json.loads(string)

        except (ValueError, TypeError):
            return default
