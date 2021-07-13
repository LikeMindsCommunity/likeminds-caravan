from django.urls import path

from cms.in_app_review.in_app_review_views_impl import ShownReviewPopUpView, EnableReviewPopUpView

urlpatterns = [
    path('enable', EnableReviewPopUpView.as_view(), name="review_popup_enable"),
    path('shown', ShownReviewPopUpView.as_view(), name="review_popup_shown")
]
