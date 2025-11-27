from .models import IntegrationProfile, IntegrationErrorLog
from .utils import refresh_ml_token, fetch_and_process_ml_orders, fetch_and_process_shopee_orders, send_alert_email
from .shopee_utils import sign_shopee_request, SHOPEE_API_URL
import requests
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

# ... (Previous tasks remain unchanged)

def refresh_shopee_token(profile):
    """
    Refreshes Shopee Access Token.
    """
    path = "/auth/access_token/get"
    body = {
        "refresh_token": profile.shopee_refresh_token,
        "partner_id": int(profile.shopee_partner_id),
        "shop_id": int(profile.shopee_shop_id)
    }
    
    try:
        sign, timestamp = sign_shopee_request(path, int(profile.shopee_partner_id), profile.shopee_partner_key)
        url = f"{SHOPEE_API_URL}{path}?partner_id={profile.shopee_partner_id}&timestamp={timestamp}&sign={sign}"
        
        resp = requests.post(url, json=body)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get('error'):
            error_msg = f"Shopee Refresh Error for {profile.organization.name}: {data.get('message')}"
            logger.error(error_msg)
            log = IntegrationErrorLog.objects.create(
                organization=profile.organization,
                platform='SHOPEE',
                task_name='refresh_shopee_token',
                error_message=error_msg
            )
            send_alert_email(log)
            return

        profile.shopee_access_token = data['access_token']
        profile.shopee_refresh_token = data['refresh_token']
        # Shopee tokens expire in 4 hours usually
        expires_in = data.get('expire_in', 14400) 
        profile.shopee_token_expiry_date = timezone.now() + timedelta(seconds=expires_in)
        profile.save()
        logger.info(f"Shopee Token Refreshed for {profile.organization.name}")
        
    except Exception as e:
        error_msg = f"Error refreshing Shopee token: {e}"
        logger.error(error_msg)
        log = IntegrationErrorLog.objects.create(
            organization=profile.organization,
            platform='SHOPEE',
            task_name='refresh_shopee_token',
            error_message=error_msg
        )
        send_alert_email(log)

@shared_task
def renew_all_platform_tokens():
    """
    Periodic task to renew tokens for all platforms.
    """
    logger.info("Starting Token Renewal Task...")
    profiles = IntegrationProfile.objects.all()
    
    for profile in profiles:
        # 1. Mercado Livre
        if profile.ml_refresh_token:
            # Check expiry or just force refresh if close? 
            # utils.refresh_ml_token handles the check/refresh logic usually, 
            # but let's assume we want to ensure it's fresh.
            # The utils function checks expiry. We can just call it.
            refresh_ml_token(profile)
            
        # 2. Shopee
        if profile.shopee_refresh_token and profile.shopee_partner_id:
            refresh_shopee_token(profile)
            
    logger.info("Token Renewal Task Completed.")

@shared_task
def fetch_all_new_orders():
    """
    Periodic task to fetch new orders.
    """
    logger.info("Starting Order Collection Task...")
    
    # We can optimize this to fetch per profile inside the task or spawn sub-tasks.
    # For now, sequential per profile.
    
    profiles = IntegrationProfile.objects.all()
    for profile in profiles:
        # ML
        if profile.ml_access_token:
            # We might want to refactor fetch_and_process_ml_orders to take a profile arg
            # Currently it iterates all. 
            # Let's call the bulk function if it iterates all, OR refactor.
            # The existing fetch_and_process_ml_orders iterates ALL profiles.
            pass

    # Actually, the existing functions iterate ALL profiles. 
    # So we just call them once.
    fetch_and_process_ml_orders()
    
    # Shopee function also iterates all profiles?
    # Let's check utils.py... 
    # "fetch_and_process_shopee_orders(tenant_profile)" takes a profile!
    # "fetch_and_process_ml_orders()" iterates all.
    
    # So:
    # ML is bulk.
    # Shopee needs iteration.
    
    for profile in profiles:
        if profile.shopee_access_token:
            fetch_and_process_shopee_orders(profile)
            
    logger.info("Order Collection Task Completed.")

def refresh_shopee_token(profile):
    """
    Refreshes Shopee Access Token.
    """
    path = "/auth/access_token/get"
    body = {
        "refresh_token": profile.shopee_refresh_token,
        "partner_id": int(profile.shopee_partner_id),
        "shop_id": int(profile.shopee_shop_id)
    }
    
    try:
        sign, timestamp = sign_shopee_request(path, int(profile.shopee_partner_id), profile.shopee_partner_key)
        url = f"{SHOPEE_API_URL}{path}?partner_id={profile.shopee_partner_id}&timestamp={timestamp}&sign={sign}"
        
        resp = requests.post(url, json=body)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get('error'):
            logger.error(f"Shopee Refresh Error for {profile.organization.name}: {data.get('message')}")
            return

        profile.shopee_access_token = data['access_token']
        profile.shopee_refresh_token = data['refresh_token']
        # Shopee tokens expire in 4 hours usually
        expires_in = data.get('expire_in', 14400) 
        profile.shopee_token_expiry_date = timezone.now() + timedelta(seconds=expires_in)
        profile.save()
        logger.info(f"Shopee Token Refreshed for {profile.organization.name}")
        
    except Exception as e:
        logger.error(f"Error refreshing Shopee token: {e}")
