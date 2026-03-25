from rest_framework import serializers
from .models import Incident, ResponseLog, VouchRecord, IncidentMedia


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

    class Meta:
        model = Incident
        fields = '__all__'


class IncidentDetailSerializer(serializers.ModelSerializer):
    response_logs = ResponseLogSerializer(many=True, read_only=True)
    total_donations_naira = serializers.FloatField(read_only=True)
    media = IncidentMediaSerializer(many=True, read_only=True)

    class Meta:
        model = Incident
        fields = '__all__'
