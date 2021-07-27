from .api_utilites import APIUtilities


class TestUtilities:

    @staticmethod
    def create_user(user_dict):
        response = APIUtilities.post_api_request('/api/v1/login', user_dict)
        response_context = APIUtilities.get_api_request(response)

        return response_context.get('user').get('id')

    @staticmethod
    def create_community(community_dict, creator_id):
        response = APIUtilities.post_api_request('/api/v1/create_community', community_dict,
                                                 {'HTTP_X_MEMBER_ID': creator_id})
        return response

    @staticmethod
    def get_community_questions(community_context, member_id):
        response = APIUtilities.hit_get_api_with_body('/api/questions', community_context,
                                                      {'HTTP_X_MEMBER_ID': member_id})
        return response
