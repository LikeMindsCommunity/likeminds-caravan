from django.http import JsonResponse

from collabmates_api.landing_page.views_manager import ViewsManager
from collabmates_api.utilities.request_utilities import RequestUtilities
from collabmates_api.utilities.number_utilities import NumberUtilities
from collabmates_api.landing_page.member_community_impl import MemberCommunityImpl


class ViewsImpl(ViewsManager):

    def get_member_communities(self) -> JsonResponse:

        request = self

        page = request.GET.get('page', 1)
        page = NumberUtilities.get_integer_from_string(page, 1)

        member_id = RequestUtilities.get_member_id_from_headers(request)

        member_community_manager = MemberCommunityImpl(member_id, page)
        member_community_manager.extract_member_communities()
        communities = member_community_manager.get_communities()

        return JsonResponse({"member_communities": communities})
