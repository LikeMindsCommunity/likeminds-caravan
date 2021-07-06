class NumberUtilities:

    @staticmethod
    def get_integer_from_string(number_string: str, return_default: int = 1) -> int:
        try:
            return int(number_string)
        except (ValueError, TypeError):
            return return_default

    @staticmethod
    def convert_string_list_to_integer_list(string, delimiter=","):
        map_object = map(int, string.split(delimiter))

        return list(map_object)
