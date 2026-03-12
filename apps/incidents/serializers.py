from rest_framework import serializers
from .models import Incident, ResponseLog, VouchRecord


class ResponseLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResponseLog
        fields = '__all__'


class IncidentSerializer(serializers.ModelSerializer):
    total_donations_naira = serializers.FloatField(read_only=True)

    class Meta:
        model = Incident
        fields = '__all__'


class IncidentDetailSerializer(serializers.ModelSerializer):
    response_logs = ResponseLogSerializer(many=True, read_only=True)
    total_donations_naira = serializers.FloatField(read_only=True)

    class Meta:
        model = Incident
        fields = '__all__'
