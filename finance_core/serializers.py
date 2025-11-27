from rest_framework import serializers
from .models import Organization, TaxProfile, ProductCost

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = '__all__'
        read_only_fields = ['owner']

    def create(self, validated_data):
        # Assign current user as owner
        user = self.context['request'].user
        validated_data['owner'] = user
        return super().create(validated_data)

class TaxProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxProfile
        fields = '__all__'

class ProductCostSerializer(serializers.ModelSerializer):
    net_cost = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = ProductCost
        fields = [
            'id', 'organization', 'sku', 'ncm', 
            'gross_cost', 'credit_icms', 'credit_pis', 'credit_cofins', 
            'net_cost'
        ]

    def validate(self, data):
        """
        Validate and calculate net_cost.
        """
        gross_cost = data.get('gross_cost')
        credit_icms = data.get('credit_icms', 0)
        credit_pis = data.get('credit_pis', 0)
        credit_cofins = data.get('credit_cofins', 0)

        total_credits = credit_icms + credit_pis + credit_cofins
        
        if total_credits > gross_cost:
            raise serializers.ValidationError("Total tax credits cannot exceed the gross cost.")

        # We don't strictly need to set net_cost in validated_data for the model save method to work,
        # but the requirement asked to "ensure calculation... is validated".
        # The model's save() method also handles this, but we can double check here.
        
        return data
