from rest_framework import serializers
from .models import Organisation


class OrganisationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organisation
        fields = [
            'id', 'name', 'org_type', 'status', 'location_lat', 'location_lng',
            'address', 'zone_name', 'response_radius_km', 'contact_name',
            'contact_whatsapp', 'contact_phone', 'responds_to', 'operating_hours',
            'cac_number', 'total_responses', 'created_at',
        ]
        read_only_fields = ['id', 'status', 'total_responses', 'created_at']
