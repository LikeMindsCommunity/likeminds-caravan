import abc


class CohortManager(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return ((hasattr(subclass, 'create_cohort') and callable(subclass.create_cohort)) and
                (hasattr(subclass, 'delete_cohort') and callable(subclass.delete_cohort)) and
                (hasattr(subclass, 'update_cohort') and callable(subclass.update_cohort)) and
                (hasattr(subclass, 'fetch_cohorts_with_community_id') and
                 callable(subclass.fetch_cohorts_with_community_id)) and
                (hasattr(subclass, 'remove_member_from_cohort') and
                 callable(subclass.remove_member_from_cohort)) and
                (hasattr(subclass, 'fetch_cohorts_with_community_and_cohort_id') and
                 callable(subclass.fetch_cohorts_with_community_and_cohort_id)) and
                (hasattr(subclass, 'fetch_member_cohorts') and
                 callable(subclass.fetch_member_cohorts)) and
                (hasattr(subclass, 'update_cohort_access_for_chatroom') and
                 callable(subclass.update_cohort_access_for_chatroom)) and
                (hasattr(subclass, 'fetch_all_cohort_access_for_chatroom') and
                 callable(subclass.fetch_all_cohort_access_for_chatroom)) or
                NotImplemented)

    @abc.abstractmethod
    def create_cohort(self, request_body):
        """
        Creates cohort in a community
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete_cohort(self, cohort_id):
        """
        Deletes cohort in a community
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update_cohort(self, request_body):
        """
        Updates a cohort in a community
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_cohorts_with_community_id(self, community_id, api_revamp_v1_check=False):
        """
        Fetches cohorts with member count in a community
        """
        raise NotImplementedError

    @abc.abstractmethod
    def remove_member_from_cohort(self, request_body):
        """
        Removes a member from a cohort
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_cohorts_with_community_and_cohort_id(self, cohort_id, community_id, api_revamp_v1_check=False):
        """
        Fetches cohort details in a community
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_member_cohorts(self, community_id, member_ids):
        """
        Fetches cohorts of members in a community
        """
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_all_cohort_access_for_chatroom(self, chatroom_id):
        """
        Fetches access for each cohort added in chatroom
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update_cohort_access_for_chatroom(self, request_body):
        """
        Updates access for cohort added in chatroom
        """
        raise NotImplementedError


