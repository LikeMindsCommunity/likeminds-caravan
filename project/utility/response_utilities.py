class ResponseUtilities:

    @staticmethod
    def get_inner_error_context(error_message):
        """
        function to get error context for apis
        """

        context = {
            'error_message': error_message
        }
        return context

    @staticmethod
    def get_impl_error_context(error_message, status_code):
        """
        function to get impl level error context for apis
        """

        context = {
            'error_message': error_message,
            'status': status_code
        }
        return context

    @staticmethod
    def get_view_impl_error_context(error_message, status_code):
        """
        function to get outer error context for apis
        """

        context = {
            'data': {
                'success': False,
                'error_message': error_message
            },
            'status': status_code
        }
        return context

    @staticmethod
    def get_error_context(success, error_message):
        """
        function to return error context in form of dict
        """
        return {
            'success': success,
            'error_message': error_message
        }
