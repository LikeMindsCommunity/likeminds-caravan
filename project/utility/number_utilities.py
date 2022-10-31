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

    @staticmethod
    def convert_list_to_integer_list_or_raise_exception(list_to_convert: list):

        if not isinstance(list_to_convert, list):
            raise Exception(f"Expected list but got {type(list_to_convert)}")

        integer_list = []

        for value in list_to_convert:
            integer_list.append(int(value))

        return integer_list

    @staticmethod
    def convert_list_to_integer_list_with_conversion_status(list_to_convert: list):

        integer_list = []
        status = False

        if not isinstance(list_to_convert, list):
            return status, integer_list

        try:
            for value in list_to_convert:
                integer_list.append(int(value))

            status = True
        except Exception as error:
            print("Error in converting to integers", error)

        return status, integer_list
