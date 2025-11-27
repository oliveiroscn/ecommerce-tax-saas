from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import redirect
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import requests
from .models import Organization, TaxProfile, ProductCost, IntegrationProfile
from .serializers import OrganizationSerializer, TaxProfileSerializer, ProductCostSerializer
from .utils import ML_AUTH_URL, ML_TOKEN_URL
from .shopee_utils import sign_shopee_request, SHOPEE_API_URL

class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    # permission_classes = [permissions.IsAuthenticated] # Uncomment in production

    def get_queryset(self):
        # Filter by owner for multi-tenancy security
        # return self.queryset.filter(owner=self.request.user)
        return self.queryset # Returning all for initial dev/testing as requested

class TaxProfileViewSet(viewsets.ModelViewSet):
    queryset = TaxProfile.objects.all()
    serializer_class = TaxProfileSerializer

class ProductCostViewSet(viewsets.ModelViewSet):
    queryset = ProductCost.objects.all()
    serializer_class = ProductCostSerializer

    def perform_create(self, serializer):
        # The serializer validation runs before this.
        # The model's save method will handle the final net_cost calculation assignment.
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

class MLAuthStartView(APIView):
    """
    Initiates the OAuth flow.
    Expects 'organization_id' in query params to know which tenant is authenticating.
    """
    def get(self, request):
        org_id = request.query_params.get('organization_id')
        if not org_id:
            return Response({"error": "organization_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Ideally, we should validate the organization exists and belongs to the user
        
        # We need the client_id. In a real app, this might be global or per-tenant.
        # Assuming global app credentials for now, or we fetch from the profile if it exists (but it might not have creds yet if we are just starting).
        # Let's assume the user has already created an IntegrationProfile with client_id/secret but no tokens.
        
        try:
            profile = IntegrationProfile.objects.get(organization_id=org_id)
        except IntegrationProfile.DoesNotExist:
             return Response({"error": "IntegrationProfile not found for this organization. Please create one with Client ID/Secret first."}, status=status.HTTP_404_NOT_FOUND)

        redirect_uri = "http://localhost:8000/api/v1/ml/auth/callback/" # Replace with env var
        state = org_id # Pass org_id as state to retrieve it in callback
        
        auth_url = f"{ML_AUTH_URL}?response_type=code&client_id={profile.ml_client_id}&redirect_uri={redirect_uri}&state={state}"
        
        return redirect(auth_url)

class MLAuthCallbackView(APIView):
    """
    Handles the callback from Mercado Livre.
    """
    def get(self, request):
        code = request.query_params.get('code')
        state = request.query_params.get('state') # This is the org_id
        
        if not code or not state:
            return Response({"error": "Missing code or state"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            profile = IntegrationProfile.objects.get(organization_id=state)
        except IntegrationProfile.DoesNotExist:
            return Response({"error": "Organization not found"}, status=status.HTTP_404_NOT_FOUND)
            
        redirect_uri = "http://localhost:8000/api/v1/ml/auth/callback/"
        
        payload = {
            'grant_type': 'authorization_code',
            'client_id': profile.ml_client_id,
            'client_secret': profile.ml_client_secret,
            'code': code,
            'redirect_uri': redirect_uri,
        }
        
        try:
            response = requests.post(ML_TOKEN_URL, data=payload)
            response.raise_for_status()
            data = response.json()
            
            profile.ml_access_token = data['access_token']
            profile.ml_refresh_token = data['refresh_token']
            expires_in = data.get('expires_in', 21600)
            profile.ml_token_expiry_date = timezone.now() + timedelta(seconds=expires_in)
            profile.save()
            
            return Response({"message": "Mercado Livre authentication successful!", "organization": profile.organization.name})
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ShopeeAuthStartView(APIView):
    """
    Generates Shopee Authorization URL.
    """
    def get(self, request):
        org_id = request.query_params.get('organization_id')
        if not org_id:
            return Response({"error": "organization_id required"}, status=400)
            
        try:
            profile = IntegrationProfile.objects.get(organization_id=org_id)
        except IntegrationProfile.DoesNotExist:
            return Response({"error": "Profile not found"}, status=404)
            
        if not profile.shopee_partner_id or not profile.shopee_partner_key:
            return Response({"error": "Shopee Partner ID/Key missing"}, status=400)
            
        path = "/shop/auth_partner"
        redirect_url = "http://localhost:8000/api/v1/integrations/shopee/callback/"
        
        sign, timestamp = sign_shopee_request(path, int(profile.shopee_partner_id), profile.shopee_partner_key)
        
        auth_url = f"{SHOPEE_API_URL}{path}?partner_id={profile.shopee_partner_id}&timestamp={timestamp}&sign={sign}&redirect={redirect_url}&state={org_id}"
        
        return redirect(auth_url)

class ShopeeAuthCallbackView(APIView):
    """
    Shopee Callback. Receives code and shop_id.
    """
    def get(self, request):
        code = request.query_params.get('code')
        shop_id = request.query_params.get('shop_id')
        state = request.query_params.get('state') # org_id
        
        if not code or not shop_id or not state:
            return Response({"error": "Missing params"}, status=400)
            
        try:
            profile = IntegrationProfile.objects.get(organization_id=state)
        except IntegrationProfile.DoesNotExist:
            return Response({"error": "Organization not found"}, status=404)
            
        # Exchange code for token
        path = "/auth/token/get"
        body = {
            "code": code,
            "shop_id": int(shop_id),
            "partner_id": int(profile.shopee_partner_id)
        }
        
        sign, timestamp = sign_shopee_request(path, int(profile.shopee_partner_id), profile.shopee_partner_key)
        
        url = f"{SHOPEE_API_URL}{path}?partner_id={profile.shopee_partner_id}&timestamp={timestamp}&sign={sign}"
        
        try:
            resp = requests.post(url, json=body)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get('error'):
                 return Response({"error": f"Shopee API Error: {data.get('message')}"}, status=400)

            profile.shopee_access_token = data['access_token']
            profile.shopee_refresh_token = data['refresh_token']
            profile.shopee_shop_id = str(shop_id)
            profile.save()
            
            return Response({"message": "Shopee Auth Successful!"})
            
        except Exception as e:
            return Response({"error": str(e)}, status=500)
