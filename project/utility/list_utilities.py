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

    @staticmethod
    def merge_lists(list_one: list, list_two: list) -> list:
        """
        returns a merged list having elements from list_one and list_two,
        duplicates aren't handled
        """
        return list_one + list_two

    @staticmethod
    def remove_duplicates(input_list: list) -> list:
        """
        returns original list with duplicate elements removed,
        element order is preserved
        """
        if not input_list:
            return []

        return [*set(input_list)]

    @staticmethod
    def sort_dictionary_list(input_list: list, dict_key: str, reverse_order: bool = False) -> list:
        """
        return a list with items sorted in order of dictionary key
        """
        return sorted(input_list, key=lambda i: i[dict_key], reverse=reverse_order)

    @staticmethod
    def get_common_elements(input_list_one: list, input_list_two: list) -> list:
        """
        returns elements common in both lists
        """
        if not input_list_one or not input_list_two:
            return []

        return list(set(input_list_one).intersection(input_list_two))
