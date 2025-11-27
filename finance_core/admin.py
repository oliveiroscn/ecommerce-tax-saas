from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from datetime import timedelta
from .models import Organization, TaxProfile, LogisticsCostTable, IntegrationErrorLog, IntegrationProfile, SaleTransaction, ProductCost

class IntegrationProfileInline(admin.StackedInline):
    model = IntegrationProfile
    can_delete = False
    verbose_name_plural = 'Integration Profile'

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'cnpj', 'health_status')
    readonly_fields = ('health_status',)
    inlines = [IntegrationProfileInline]

    def health_status(self, obj):
        """
        Calculates the health status of the organization's integrations.
        """
        # 1. Check for recent critical errors (last 24h)
        recent_errors = IntegrationErrorLog.objects.filter(
            organization=obj,
            timestamp__gte=timezone.now() - timedelta(hours=24)
        ).count()
        
        if recent_errors > 0:
            return format_html('<span style="color: red; font-weight: bold;">CRITICAL ({} Errors)</span>', recent_errors)
            
        # 2. Check Tokens
        try:
            profile = obj.integrationprofile
            ml_ok = bool(profile.ml_access_token)
            shopee_ok = bool(profile.shopee_access_token)
            
            if ml_ok and shopee_ok:
                return format_html('<span style="color: green; font-weight: bold;">Healthy</span>')
            elif ml_ok or shopee_ok:
                return format_html('<span style="color: orange; font-weight: bold;">Partial (ML: {}, Shopee: {})</span>', 
                                   "OK" if ml_ok else "Missing", 
                                   "OK" if shopee_ok else "Missing")
            else:
                return format_html('<span style="color: gray;">No Integrations</span>')
                
        except IntegrationProfile.DoesNotExist:
             return format_html('<span style="color: gray;">No Profile</span>')

    health_status.short_description = 'Integration Health'

@admin.register(TaxProfile)
class TaxProfileAdmin(admin.ModelAdmin):
    list_display = ('organization', 'regime', 'icms_benefit_flag', 'effective_tax_rate')
    list_filter = ('regime', 'icms_benefit_flag')
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('organization', 'regime')
        }),
        ('Fiscal Benefits (Minas Gerais / TTS)', {
            'classes': ('collapse',),
            'fields': ('icms_benefit_flag', 'effective_tax_rate', 'effective_rate_interstate'),
            'description': 'Configure special tax regimes like TTS/Corredor here. Enable "icms_benefit_flag" to use the effective rate.'
        }),
    )

@admin.register(LogisticsCostTable)
class LogisticsCostTableAdmin(admin.ModelAdmin):
    list_display = ('organization', 'platform', 'shipping_method', 'fixed_cost_value')
    list_filter = ('platform', 'organization')
    search_fields = ('shipping_method',)

class CriticalErrorFilter(admin.SimpleListFilter):
    title = 'Critical Token Error'
    parameter_name = 'is_critical'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes (Token/Auth Errors)'),
            ('no', 'No (Other Errors)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(error_message__icontains='token') | queryset.filter(task_name__icontains='token') | queryset.filter(error_message__icontains='401')
        if self.value() == 'no':
            return queryset.exclude(error_message__icontains='token').exclude(task_name__icontains='token').exclude(error_message__icontains='401')

@admin.register(IntegrationErrorLog)
class IntegrationErrorLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'organization', 'platform', 'task_name', 'short_error')
    list_filter = ('platform', 'task_name', 'organization', CriticalErrorFilter)
    readonly_fields = ('organization', 'platform', 'task_name', 'error_message', 'timestamp')
    search_fields = ('error_message', 'task_name')
    
    def short_error(self, obj):
        return obj.error_message[:50] + '...' if len(obj.error_message) > 50 else obj.error_message
    short_error.short_description = 'Error Message'

# Register other models simply
admin.site.register(SaleTransaction)
admin.site.register(ProductCost)
