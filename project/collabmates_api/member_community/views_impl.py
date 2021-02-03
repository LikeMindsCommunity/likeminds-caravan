from django.http import JsonResponse

from collabmates_api.member_community.member_community_impl import MemberCommunityImpl
from collabmates_api.member_community.views_manager import ViewsManager
from utility.request_utilities import RequestUtilities
from utility.number_utilities import NumberUtilities
from collabmates_api.views import get_error_context


class ViewsImpl(ViewsManager):

    def get_member_communities(self, user_id: int) -> JsonResponse:
        member_community_manager = MemberCommunityImpl(member_id, None)
        request = self

        page = request.GET.get('page', 1)
        page = NumberUtilities.get_integer_from_string(page, 1)

        member_id = RequestUtilities.get_member_id_from_headers(request)
        if not member_id:
            context = get_error_context(False, "member id missing in request")
            return JsonResponse(context, status=400)

        member_community_manager = MemberCommunityImpl(member_id, None)
        communities = member_community_manager.extract_member_communities(page)

        return JsonResponse({"your_communities": communities})
