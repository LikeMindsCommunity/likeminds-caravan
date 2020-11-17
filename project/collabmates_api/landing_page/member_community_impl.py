from abc import ABC

from .member_community_manager import MemberCommunityManager


class MemberCommunity(MemberCommunityManager):

    member_id = None
    communities = {
        "response": None
    }

    def __init__(self, member_id: str):
        self.member_id = member_id

    def get_member_id(self):
        return self.member_id

    def set_member_id(self, member_id):
        self.member_id = member_id

    def get_communities(self):
        return self.communities

    def set_communities(self, communities):
        return self.communities

    def extract_member_communities(self):
        """Get communities of the member(user)"""
        member_id = self.get_member_id()
        communities = Member_Engage.objects.filter(member_id=user).order_by('-updated_at')
        return self.get_communities()

    def extract_text(self, full_file_path: str) -> dict:
        """Overrides FormalParserInterface.extract_text()"""
        return
