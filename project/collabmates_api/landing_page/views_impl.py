from django.http import JsonResponse

from collabmates_api.landing_page.views_manager import ViewsManager
from collabmates_api.utilities import request_utilities
from collabmates_api.landing_page.member_community_impl import MemberCommunityImpl


class ViewsImpl(ViewsManager):

    def get_member_communities(self) -> JsonResponse:

        member_id = request_utilities.RequestUtilities.get_member_id_from_headers(self)
        member_community_manager = MemberCommunityImpl(member_id)
        member_community_manager.extract_member_communities()
        communities = member_community_manager.get_communities()

        return JsonResponse({"member_communities": communities})
