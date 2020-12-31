class NumberUtilities:

    @staticmethod
    def get_integer_from_string(number_string: str, return_default: int = 1) -> int:
        try:
            return int(number_string)
        except ValueError:
            return return_default
