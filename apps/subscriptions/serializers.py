from rest_framework import serializers
from .models import LocationSubscription, SubscriptionAlert, SafetyScoreLog, LGASubscription


class LocationSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationSubscription
        fields = [
            'id', 'phone_hash', 'whatsapp_number', 'label', 'subscription_type',
            'location_type', 'location_lat', 'location_lng',
            'office_lat', 'office_lng', 'family_members',
            'alert_radius_km', 'commute_buffer_km', 'peak_only',
            'safety_score', 'is_active', 'incident_types',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'phone_hash', 'created_at', 'updated_at']


class SubscriptionAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionAlert
        fields = ['id', 'subscription', 'incident', 'distance_km', 'alert_type', 'sent_at', 'delivered']
        read_only_fields = ['id', 'sent_at']


class LGASubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LGASubscription
        fields = ['id', 'lga', 'whatsapp_number', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class SafetyScoreLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SafetyScoreLog
        fields = ['id', 'subscription', 'score', 'reason', 'created_at']
        read_only_fields = ['id', 'created_at']
