from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal

class Organization(models.Model):
    """
    Represents a Tenant (Company/Store).
    Supports multi-tenancy by linking data to this model.
    """
    name = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=14, unique=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organizations')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.cnpj})"

class TaxProfile(models.Model):
    """
    Fiscal configuration for an Organization.
    """
    REGIME_CHOICES = [
        ('LUCRO_REAL', 'Lucro Real'),
        ('LUCRO_PRESUMIDO', 'Lucro Presumido'),
        ('SIMPLES', 'Simples Nacional'),
    ]

    organization = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name='tax_profile')
    regime = models.CharField(max_length=20, choices=REGIME_CHOICES, default='LUCRO_REAL')
    
    # Benefício Fiscal (ex: TTS Minas Gerais)
    icms_benefit_flag = models.BooleanField(default=False, help_text="Ativar se houver benefício fiscal de ICMS (ex: TTS)")
    effective_tax_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.00,
        help_text="Alíquota efetiva de ICMS na saída caso tenha benefício fiscal."
    )

    def __str__(self):
        return f"Tax Profile for {self.organization.name}"

class ProductCost(models.Model):
    """
    Manual entry of product costs and tax credits.
    """
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='product_costs')
    sku = models.CharField(max_length=100)
    ncm = models.CharField(max_length=20)
    
    # Custos e Créditos
    gross_cost = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    
    # Créditos de Entrada (para abater no Lucro Real)
    credit_icms = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    credit_pis = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    credit_cofins = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Custo Líquido (Calculado)
    net_cost = models.DecimalField(max_digits=10, decimal_places=2, editable=False)

    class Meta:
        unique_together = ('organization', 'sku')

    def save(self, *args, **kwargs):
        # Fallback calculation if not handled by serializer/view, though requirement asks for validation before save.
        # We enforce it here too for data integrity.
        self.net_cost = self.gross_cost - (self.credit_icms + self.credit_pis + self.credit_cofins)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sku} - {self.organization.name}"

class SaleTransaction(models.Model):
    """
    Raw sales data from integrations (ML, Shopee).
    """
    PLATFORM_CHOICES = [
        ('ML', 'Mercado Livre'),
        ('SHOPEE', 'Shopee'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='sales')
    external_id = models.CharField(max_length=100)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_date = models.DateTimeField()
    
    # Logistics Data
    transaction_shipping_method = models.CharField(max_length=50, blank=True, null=True)
    shipping_cost_platform = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    calculated_fixed_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_fixed_cost_applied = models.BooleanField(default=False, help_text="Se True, ignora o custo da plataforma e usa apenas o fixo.")
    
    # Profitability
    net_margin = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    class Meta:
        unique_together = ('organization', 'external_id', 'platform')

    def __str__(self):
        return f"{self.platform} {self.external_id} - {self.amount}"

class IntegrationProfile(models.Model):
    """
    Stores credentials for external integrations (Mercado Livre).
    """
    organization = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name='integration_profile')
    
    # Credentials (should be encrypted in production)
    ml_client_id = models.CharField(max_length=255)
    ml_client_secret = models.CharField(max_length=255)
    
    # Tokens
    ml_access_token = models.TextField(blank=True, null=True)
    ml_refresh_token = models.TextField(blank=True, null=True)
    ml_token_expiry_date = models.DateTimeField(blank=True, null=True)
    
    # Shopee Credentials
    shopee_partner_id = models.CharField(max_length=255, blank=True, null=True)
    shopee_partner_key = models.CharField(max_length=255, blank=True, null=True)
    shopee_access_token = models.TextField(blank=True, null=True)
    shopee_refresh_token = models.TextField(blank=True, null=True)
    shopee_shop_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Integration Profile for {self.organization.name}"

class IntegrationErrorLog(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    platform = models.CharField(max_length=50) # 'ML', 'SHOPEE'
    task_name = models.CharField(max_length=100)
    error_message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Error {self.platform} - {self.task_name} at {self.timestamp}"

class LogisticsCostTable(models.Model):
    """
    Fixed logistics costs per platform and shipping method.
    """
    PLATFORM_CHOICES = [
        ('ML', 'Mercado Livre'),
        ('SHOPEE', 'Shopee'),
    ]
    
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='logistics_costs')
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    shipping_method = models.CharField(max_length=50) # e.g., 'Envio Próprio', 'Coleta', 'Full'
    fixed_cost_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        unique_together = ('organization', 'platform', 'shipping_method')

    def __str__(self):
        return f"{self.platform} - {self.shipping_method}: {self.fixed_cost_value}"
