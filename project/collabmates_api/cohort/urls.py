from django.urls import path

from collabmates_api.cohort.cohort_view_impl import CreateCohortView, DeleteCohortView, FetchCohortWithMemberCountView, \
    FetchCohortView, RemoveMemberFromCohortView, UpdateCohortView, FetchMemberCohortsView, \
    FetchCohortAccessForChatroomView

urlpatterns = [
    path('create', CreateCohortView.as_view(), name="create_cohort"),
    path('update', UpdateCohortView.as_view(), name="update_cohort"),
    path('delete', DeleteCohortView.as_view(), name="delete_cohort"),
    path('fetch', FetchCohortView.as_view(), name="fetch_cohort"),
    path('remove_member', RemoveMemberFromCohortView.as_view(), name="remove_member_from_cohort"),
    path('fetch_community_cohorts', FetchCohortWithMemberCountView.as_view(), name="community_cohorts"),
    path('fetch_member_cohorts', FetchMemberCohortsView.as_view(), name="member_cohorts"),
    path('fetch_cohort_access', FetchCohortAccessForChatroomView.as_view(), name="fetch_cohort_access")

]
