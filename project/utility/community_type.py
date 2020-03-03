from togther.models import (Community, Community_Legacy,
                            Community_Profession, Community_Interest,
                            Community_Geography, Tags_lpig,
                            Category, Attributes)
from django.db.models import Q
from django.http.response import JsonResponse, HttpResponse
from utility.states import CommunityTypes, CommunityAttributes
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt


class CommunityType(View):
    city_exists = False
    legacy_queryset = None
    profession_queryset = None
    interest_queryset = None
    geography_queryset = None
    community_instance = None

    def __init__(self, *args, **kwargs):
        super(CommunityType, self).__init__(*args, **kwargs)

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(CommunityType, self).dispatch(*args, **kwargs)

    def get(self, request=None, community_id=None, response_type=None):
        self.community_instance = Community.objects.get(pk=community_id)

        response = self.get_community_type()
        if response_type == None:
            return JsonResponse(response)
        else:
            return HttpResponse(repr(response))
            # return response

    def post(self, request=None, community_id=None, response_type=None, community_instance=None):
        try:
            if community_instance:
                self.community_instance = community_instance
            elif community_id:
                self.community_instance = Community.objects.get(pk=community_id)
            else:
                raise ValueError

        except ValueError:
            return JsonResponse({"Error": "Provide Community ID or Instance "})

        response = self.get_community_type()
        if not self.community_instance.type:
            self.community_instance.type = response['Map']
            self.community_instance.save()

        if response_type == None:
            return JsonResponse(response)
        else:
            return HttpResponse(repr(response))
            # return response

    def get_community_type(self):

        if self.community_instance.type:
            response = {"Type": self.community_instance.type, "Map": self.community_instance.type}

        else:
            self.city_exists = self.contains_gc()

            self.legacy_queryset = Community_Legacy.objects.filter(community_id=self.community_instance).select_related(
                'tags_id')
            self.profession_queryset = Community_Profession.objects.filter(
                community_id=self.community_instance).select_related(
                'tags_id')
            self.interest_queryset = Community_Interest.objects.filter(community_id=self.community_instance).select_related(
                'tags_id')

            community_type = ''
            community_type_map = -1

            if not self.city_exists and self.legacy_queryset.exists() and self.profession_queryset.exists() and self.interest_queryset.exists():
                pass

            elif self.is_community_type_lc_gc():
                community_type = "LC_GC"
                community_type_map = CommunityTypes.TYPE_LC_GC

            elif self.is_community_type_lh_gc():
                community_type = "LH_GC"
                community_type_map = CommunityTypes.TYPE_LH_GC

            elif self.is_community_type_lc_ps():
                community_type = "LC_PS"
                community_type_map = CommunityTypes.TYPE_LC_PS

            elif self.is_community_type_ih_gc():
                community_type = "IH_GC"
                community_type_map = CommunityTypes.TYPE_IH_GC

            elif self.is_community_type_is_gc():
                community_type = "IS_GC"
                community_type_map = CommunityTypes.TYPE_IS_GC

            elif self.is_community_type_if_gc():
                community_type = "IF_GC"
                community_type_map = CommunityTypes.TYPE_IF_GC

            elif self.is_community_type_ic_gc():
                community_type = "IC_GC"
                community_type_map = CommunityTypes.TYPE_IC_GC

            elif self.is_community_type_pi_gc():
                community_type = "PI_GC"
                community_type_map = CommunityTypes.TYPE_PI_GC

            elif self.is_community_type_ps_gc():
                community_type = "PS_GC"
                community_type_map = CommunityTypes.TYPE_PS_GC

            # elif self.is_community_type_gn:
            #     community_type = "GN"
            #     community_type_map = CommunityTypes.TYPE_GN
            #
            # elif self.is_community_type_ss_gn:
            #     community_type = "SS_GN"
            #     community_type_map = CommunityTypes.TYPE_SS_GN
            #
            # elif self.is_community_type_ss_gc:
            #     community_type = "SS_GC"
            #     community_type_map = CommunityTypes.TYPE_SS_GC

            community_type_value = community_type_map if isinstance(community_type_map, int) else community_type_map.value
            response = {"Type": community_type, "Map": community_type_value}

        return response

    # LC_GC
    def is_community_type_lc_gc(self):
        college = self.legacy_queryset.filter(tags_id__attribute_id__id=CommunityAttributes.Legacy_education)
        if college.exists() and self.city_exists:
            return True
        return False

    # LH_GC
    def is_community_type_lh_gc(self):
        hometown = self.legacy_queryset.filter(tags_id__attribute_id__id=CommunityAttributes.Legacy_hometown)
        if hometown.exists() and self.city_exists:
            return True
        return False

    # LC_PS
    def is_community_type_lc_ps(self):
        college = self.legacy_queryset.filter(tags_id__attribute_id__id=CommunityAttributes.Legacy_education)
        skill = self.profession_queryset.filter(tags_id__attribute_id__id=CommunityAttributes.Profession_skill)
        if college.exists() and skill.exists():
            return True
        return False

    # IH_GC
    def is_community_type_ih_gc(self):
        hobby = self.interest_queryset.filter(tags_id__attribute_id__id=CommunityAttributes.Interests_hobby)
        if hobby.exists() and self.city_exists:
            return True
        return False

    # IS_GC
    def is_community_type_is_gc(self):
        sports = self.interest_queryset.filter(tags_id__attribute_id__id=CommunityAttributes.Interests_sports)
        if sports.exists() and self.city_exists:
            return True
        return False

    # IF_GC
    def is_community_type_if_gc(self):
        fan = self.interest_queryset.filter(tags_id__attribute_id__id=CommunityAttributes.Interests_fan)
        if fan.exists() and self.city_exists:
            return True
        return False

    # PS_GC
    def is_community_type_ic_gc(self):
        cause = self.interest_queryset.filter(tags_id__attribute_id__id=CommunityAttributes.Interests_cause)
        if cause.exists() and self.city_exists:
            return True
        return False

    # PS_GC
    def is_community_type_pi_gc(self):
        industry = self.profession_queryset.filter(tags_id__attribute_id__id=CommunityAttributes.Profession_industry)
        if industry.exists() and self.city_exists:
            return True
        return False

    # PS_GC
    def is_community_type_ps_gc(self):
        skill = self.profession_queryset.filter(tags_id__attribute_id__id=CommunityAttributes.Profession_skill)
        if skill.exists() and self.city_exists:
            return True
        return False

    # # GN
    # def is_community_type_gn(self):
    #
    #     college = self.legacy_queryset.filter(tags_id__attribute_id__id = 2)
    #     city = self.geography_queryset.filter(attribute_id__id = 12)
    #     if college.exists() and city.exists():
    #         return True
    #     return False
    #
    # # SS_GN
    # def is_community_type_ss_gn(self):
    #
    #     college = self.legacy_queryset.filter(attribute_id__id = 2)
    #     if college.exists() and self.is_community_type_gn():
    #         return True
    #     return False
    #
    # # SS_GC
    # def is_community_type_ss_gc(self):
    #
    #     college = self.legacy_queryset.filter(attribute_id__id = 2)
    #     if college.exists() and self.city_exists:
    #         return True
    #     return False

    def contains_gc(self):
        self.geography_queryset = Community_Geography.objects.filter(community_id=self.community_instance).select_related(
            'tags_id')
        city = self.geography_queryset.filter(tags_id__attribute_id__id=CommunityAttributes.Geography_city)
        return city.exists()


community_type_view = CommunityType.as_view()
