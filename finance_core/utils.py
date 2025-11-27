import requests
from django.utils import timezone
from datetime import timedelta
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import logging
import time
from django.core.mail import send_mail
from django.conf import settings
from .models import IntegrationProfile, SaleTransaction, ProductCost, LogisticsCostTable, IntegrationErrorLog
from .shopee_api import ShopeeClient

logger = logging.getLogger(__name__)

ML_AUTH_URL = "https://auth.mercadolivre.com.br/authorization"
ML_TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
ML_API_BASE = "https://api.mercadolibre.com"

# ... (Previous ML functions remain here: refresh_ml_token, fetch_and_process_ml_orders, process_single_order)

def calculate_net_margin(transaction: SaleTransaction):
    """
    Calculates the Net Margin (Lucro Líquido) for a given transaction.
    Formula: Revenue - Adjusted COGS - Taxes - Commissions - Total Logistics
    """
    revenue = transaction.amount
    organization = transaction.organization
    
    # Placeholder COGS/Credits logic (as per previous steps)
    cogs = Decimal('0.00')
    credits = Decimal('0.00')
    
    # Taxes
    tax_profile = getattr(organization, 'tax_profile', None)
    taxes = Decimal('0.00')
    
    if tax_profile:
        if tax_profile.icms_benefit_flag:
            taxes += revenue * (tax_profile.effective_tax_rate / 100)
            taxes += revenue * Decimal('0.0925')
        else:
            standard_rate = Decimal('0.18') + Decimal('0.0925')
            tax_liability = revenue * standard_rate
            taxes = tax_liability - credits
            if taxes < 0: taxes = 0

    # Commissions (Platform)
    commission_rate = Decimal('0.16') # Default ML
    if transaction.platform == 'SHOPEE':
        commission_rate = Decimal('0.14') # Example Shopee rate
        
    commission = revenue * commission_rate

    # Logistics
    if transaction.is_fixed_cost_applied:
        total_logistics = transaction.calculated_fixed_cost
    else:
        total_logistics = transaction.shipping_cost_platform + transaction.calculated_fixed_cost
    
    # Final Calculation
    net_margin = revenue - cogs - taxes - commission - total_logistics
    
    transaction.net_margin = net_margin
    transaction.save()
    return net_margin

def send_alert_email(log_entry):
    """
    Sends an email alert for critical integration errors.
    """
    subject = f"CRITICAL: Integration Error - {log_entry.platform} - {log_entry.task_name}"
    message = f"An error occurred in the integration system.\n\n" \
              f"Organization: {log_entry.organization.name}\n" \
              f"Platform: {log_entry.platform}\n" \
              f"Task: {log_entry.task_name}\n" \
              f"Time: {log_entry.timestamp}\n\n" \
              f"Error Message:\n{log_entry.error_message}\n\n" \
              f"Please investigate immediately."
    
    try:
        # Use a default admin email if not set in settings
        recipient_list = getattr(settings, 'ADMIN_EMAILS', ['admin@example.com'])
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list, fail_silently=True)
    except Exception as e:
        logger.error(f"Failed to send alert email: {e}")

def refresh_ml_token(profile: IntegrationProfile):
    """
    Refreshes the Mercado Livre Access Token if expired or about to expire.
    """
    if not profile.ml_refresh_token:
        return

    # Check if expired or expiring in < 10 minutes
    if profile.ml_token_expiry_date and profile.ml_token_expiry_date > timezone.now() + timedelta(minutes=10):
        return

    data = {
        'grant_type': 'refresh_token',
        'client_id': profile.ml_client_id,
        'client_secret': profile.ml_client_secret,
        'refresh_token': profile.ml_refresh_token,
    }

    try:
        response = requests.post(ML_TOKEN_URL, data=data)
        response.raise_for_status()
        token_data = response.json()

        profile.ml_access_token = token_data['access_token']
        profile.ml_refresh_token = token_data['refresh_token']
        profile.ml_token_expiry_date = timezone.now() + timedelta(seconds=token_data['expires_in'])
        profile.save()
        logger.info(f"Token refreshed for {profile.organization.name}")

    except Exception as e:
        error_msg = f"Error refreshing ML token: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
             error_msg += f" | Response: {e.response.text}"
        
        logger.error(error_msg)
        
        log = IntegrationErrorLog.objects.create(
            organization=profile.organization,
            platform='ML',
            task_name='refresh_ml_token',
            error_message=error_msg
        )
        send_alert_email(log)

def fetch_and_process_ml_orders():
    """
    Fetches orders from Mercado Livre for all active profiles and processes them.
    """
    profiles = IntegrationProfile.objects.filter(ml_access_token__isnull=False)

    for profile in profiles:
        try:
            refresh_ml_token(profile) # Ensure token is valid

            headers = {'Authorization': f'Bearer {profile.ml_access_token}'}
            
            # 1. Search for orders (last 30 days for example, or since last sync)
            # Simplified: Fetch recent orders
            search_url = f"{ML_API_BASE}/orders/search?seller={profile.ml_client_id}&order.date_created.from=2023-01-01T00:00:00.000-00:00" 
            # In prod, manage 'from' date dynamically
            
            response = requests.get(search_url, headers=headers)
            response.raise_for_status()
            orders_data = response.json()

            for order in orders_data.get('results', []):
                process_single_order(profile.organization, order)
                
        except Exception as e:
            error_msg = f"Error fetching ML orders: {str(e)}"
            logger.error(error_msg)
            log = IntegrationErrorLog.objects.create(
                organization=profile.organization,
                platform='ML',
                task_name='fetch_and_process_ml_orders',
                error_message=error_msg
            )
            send_alert_email(log)

# --- Shopee Processing ---

def fetch_and_process_shopee_orders(tenant_profile: IntegrationProfile):
    """
    Fetches and processes Shopee orders for a specific tenant using ShopeeClient.
    """
    if not tenant_profile.shopee_access_token or not tenant_profile.shopee_shop_id:
        logger.warning(f"Shopee credentials missing for {tenant_profile.organization.name}")
        return

    client = ShopeeClient(
        partner_id=tenant_profile.shopee_partner_id,
        partner_key=tenant_profile.shopee_partner_key,
        access_token=tenant_profile.shopee_access_token,
        shop_id=tenant_profile.shopee_shop_id
    )

    # Time range: Last 15 days
    time_to = int(time.time())
    time_from = time_to - (15 * 24 * 3600)

    try:
        # 1. Get Order List
        resp = client.get_order_list(time_from, time_to)
        if resp.get('error'):
            error_msg = f"Shopee API Error: {resp.get('message')}"
            logger.error(error_msg)
            log = IntegrationErrorLog.objects.create(
                organization=tenant_profile.organization,
                platform='SHOPEE',
                task_name='fetch_and_process_shopee_orders',
                error_message=error_msg
            )
            send_alert_email(log)
            return

        order_list = resp.get('response', {}).get('order_list', [])
        order_sn_list = [o['order_sn'] for o in order_list]

        if not order_sn_list:
            return

        # 2. Get Order Details (Batch)
        details_resp = client.get_order_detail(order_sn_list)
        orders_details = details_resp.get('response', {}).get('order_list', [])

        for order_data in orders_details:
            process_shopee_single_order(tenant_profile.organization, order_data)

    except Exception as e:
        error_msg = f"Error processing Shopee orders: {e}"
        logger.error(error_msg)
        log = IntegrationErrorLog.objects.create(
            organization=tenant_profile.organization,
            platform='SHOPEE',
            task_name='fetch_and_process_shopee_orders',
            error_message=error_msg
        )
        send_alert_email(log)

def process_shopee_single_order(organization, order_data):
    """
    Maps Shopee order data to SaleTransaction and applies logic.
    """
    order_sn = order_data['order_sn']
    amount = Decimal(order_data['total_amount'])
    create_time = timezone.datetime.fromtimestamp(order_data['create_time'], tz=timezone.utc)
    
    # Logistics Mapping
    shipping_carrier = order_data.get('shipping_carrier', 'Standard')
    actual_shipping_fee = Decimal(order_data.get('actual_shipping_fee', 0))
    
    # Logic: Check Fixed Cost
    fixed_cost = Decimal('0.00')
    is_fixed_applied = False
    
    try:
        cost_rule = LogisticsCostTable.objects.get(
            organization=organization, 
            platform='SHOPEE', 
            shipping_method=shipping_carrier
        )
        fixed_cost = cost_rule.fixed_cost_value
        # If we found a rule, we assume it applies. 
        # Prompt 11B: "zerando o shipping_cost_platform ... quando o is_fixed_cost_applied for TRUE"
        # This logic is handled in calculate_net_margin, but we must set the flag here.
        if fixed_cost > 0: # Or just if rule exists? Prompt says "applying... calculated_fixed_cost... when... TRUE"
            is_fixed_applied = True
            
    except LogisticsCostTable.DoesNotExist:
        pass

    # Save Transaction
    transaction, created = SaleTransaction.objects.get_or_create(
        organization=organization,
        external_id=order_sn,
        platform='SHOPEE',
        defaults={
            'amount': amount,
            'transaction_date': create_time,
            'transaction_shipping_method': shipping_carrier,
            'shipping_cost_platform': actual_shipping_fee,
            'calculated_fixed_cost': fixed_cost,
            'is_fixed_cost_applied': is_fixed_applied
        }
    )
    
    # Calculate Margin
    calculate_net_margin(transaction)
