from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import Incident, ResponseLog, VouchRecord, IncidentMedia


def _resolved_to_closed(obj):
    if obj.status == 'RESOLVED':
        cutoff = timezone.now() - timedelta(days=30)
        if obj.created_at < cutoff:
            return 'CLOSED'
    return obj.status


class ResponseLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResponseLog
        fields = '__all__'


class IncidentMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidentMedia
        fields = ['id', 'media_type', 'public_url', 'file_size', 'upload_timestamp']


class IncidentSerializer(serializers.ModelSerializer):
    total_donations_naira = serializers.FloatField(read_only=True)
    status = serializers.SerializerMethodField()

    def get_status(self, obj):
        return _resolved_to_closed(obj)

    class Meta:
        model = Incident
        fields = '__all__'


class IncidentDetailSerializer(serializers.ModelSerializer):
    response_logs = ResponseLogSerializer(many=True, read_only=True)
    total_donations_naira = serializers.FloatField(read_only=True)
    media = IncidentMediaSerializer(many=True, read_only=True)
    status = serializers.SerializerMethodField()

    def get_status(self, obj):
        return _resolved_to_closed(obj)

    class Meta:
        model = Incident
        fields = '__all__'
