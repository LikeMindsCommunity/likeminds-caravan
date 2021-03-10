class StringUtilities:

    @staticmethod
    def get_string_from_integer(number: int, return_default: str = '') -> str:

        try:
            return str(number)
        except (ValueError, TypeError):
            return return_default

    @staticmethod
    def get_boolean_from_string(string) -> bool:

        if string == "true":
            return True

        return False

