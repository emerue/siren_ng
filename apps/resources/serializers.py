from rest_framework import serializers
from .models import ResourceItem, ResourceClaim, Donation


class ResourceClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceClaim
        fields = ['id', 'resource', 'claimer_hash', 'claimer_name', 'claimer_phone', 'claimed_at']
        read_only_fields = ['id', 'claimed_at']


class ResourceItemSerializer(serializers.ModelSerializer):
    claim_count = serializers.SerializerMethodField()

    class Meta:
        model = ResourceItem
        fields = [
            'id', 'incident', 'category', 'label', 'status',
            'suggested_by_hash', 'suggested_by_name', 'suggested_via',
            'confirmed_by_hash', 'confirmed_at',
            'created_at', 'updated_at', 'claim_count',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'claim_count']

    def get_claim_count(self, obj):
        return obj.claims.count()


class DonationSerializer(serializers.ModelSerializer):
    amount_naira = serializers.SerializerMethodField()

    class Meta:
        model = Donation
        fields = [
            'id', 'incident', 'donor_name', 'amount_kobo', 'amount_naira',
            'fund_choice', 'status', 'paystack_reference',
            'created_at', 'confirmed_at',
        ]
        read_only_fields = ['id', 'status', 'paystack_reference', 'created_at', 'confirmed_at']

    def get_amount_naira(self, obj):
        return obj.amount_naira


class DonationSummarySerializer(serializers.Serializer):
    total_naira     = serializers.FloatField()
    donation_count  = serializers.IntegerField()
    fund_breakdown  = serializers.DictField(child=serializers.FloatField())
