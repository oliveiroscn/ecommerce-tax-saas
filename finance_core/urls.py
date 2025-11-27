from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrganizationViewSet, TaxProfileViewSet, ProductCostViewSet, MLAuthStartView, MLAuthCallbackView, ShopeeAuthStartView, ShopeeAuthCallbackView
from .analytics_views import NetMarginAnalyticsView, TaxSimulationView

router = DefaultRouter()
router.register(r'organizations', OrganizationViewSet)
router.register(r'tax-profiles', TaxProfileViewSet)
router.register(r'costs', ProductCostViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('ml/auth/start/', MLAuthStartView.as_view(), name='ml-auth-start'),
    path('ml/auth/callback/', MLAuthCallbackView.as_view(), name='ml-auth-callback'),
    path('shopee/auth/start/', ShopeeAuthStartView.as_view(), name='shopee-auth-start'),
    path('integrations/shopee/callback/', ShopeeAuthCallbackView.as_view(), name='shopee-auth-callback'),
    path('analytics/net-margin/', NetMarginAnalyticsView.as_view(), name='analytics-net-margin'),
    path('analytics/simulate-tax/', TaxSimulationView.as_view(), name='analytics-simulate-tax'),
]
