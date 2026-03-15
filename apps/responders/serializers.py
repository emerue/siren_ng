from rest_framework import serializers
from .models import Responder, ResponderDispatch


class ResponderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Responder
        fields = [
            'id', 'name', 'skill_category', 'status', 'licence_number',
            'home_lat', 'home_lng', 'response_radius_km', 'is_available',
            'responds_to', 'total_responses', 'zone_name', 'created_at',
        ]
        read_only_fields = ['id', 'status', 'total_responses', 'created_at']


class ResponderDispatchSerializer(serializers.ModelSerializer):
    responder_name = serializers.CharField(source='responder.name', read_only=True)
    incident_type  = serializers.CharField(source='incident.incident_type', read_only=True)

    class Meta:
        model = ResponderDispatch
        fields = [
            'id', 'responder', 'responder_name', 'incident', 'incident_type',
            'notified_at', 'accepted', 'on_scene_at', 'completed_at',
        ]
        read_only_fields = ['id', 'notified_at']
