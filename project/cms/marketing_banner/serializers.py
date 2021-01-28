import json
from rest_framework import serializers
from ..models import MarketingBanner


class BannerSerializer(serializers.ModelSerializer):

    class Meta:
        model = MarketingBanner
        fields = "__all__"

    def to_representation(self, banner):
        data = super(BannerSerializer, self).to_representation(banner)
        fields = self._readable_fields

        convert_fields = ["platform", "community_ids", "user_ids"]

        for field in fields:

            if field.field_name in convert_fields:
                if data[field.field_name] is not None:
                    data[field.field_name] = json.loads(data[field.field_name])

            if data[field.field_name] is None:
                del data[field.field_name]

        return data
