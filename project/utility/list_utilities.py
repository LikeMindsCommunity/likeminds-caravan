class ListUtilities:

    @staticmethod
    def convert_elements_int_to_str(input_list_int: list, return_default: list = []) -> list:

        try:
            return list(map(str, input_list_int))
        except (ValueError, TypeError):
            return return_default

    @staticmethod
    def remove_list_elements(input_list: list, remove_list: list) -> list:
        try:
            return [i for i in input_list if i not in remove_list]
        except (ValueError, TypeError):
            return input_list
