import hmac
import hashlib
import time
import requests
import json
from decimal import Decimal
from django.utils import timezone
from .models import IntegrationProfile, SaleTransaction, ProductCost, LogisticsCostTable
from .utils import calculate_net_margin

SHOPEE_API_URL = "https://partner.shopeemobile.com/api/v2" # Production URL (use test for sandbox)

def sign_shopee_request(path, partner_id, partner_key, shop_id=None, access_token=None):
    """
    Generates the HMAC-SHA256 signature for Shopee API V2.
    Base String: partner_id + path + timestamp + [access_token] + [shop_id]
    """
    timestamp = int(time.time())
    base_string = f"{partner_id}{path}{timestamp}"
    
    if access_token:
        base_string += f"{access_token}"
    if shop_id:
        base_string += f"{shop_id}"
        
    sign = hmac.new(
        partner_key.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return sign, timestamp

def fetch_and_process_shopee_orders():
    """
    Fetches orders from Shopee for all active profiles.
    """
    profiles = IntegrationProfile.objects.filter(shopee_partner_id__isnull=False)
    
    for profile in profiles:
        if not profile.shopee_access_token or not profile.shopee_shop_id:
            continue
            
        # 1. Get Order List
        path = "/order/get_order_list"
        partner_id = int(profile.shopee_partner_id)
        shop_id = int(profile.shopee_shop_id)
        access_token = profile.shopee_access_token
        
        sign, timestamp = sign_shopee_request(path, partner_id, profile.shopee_partner_key, shop_id, access_token)
        
        url = f"{SHOPEE_API_URL}{path}?partner_id={partner_id}&timestamp={timestamp}&access_token={access_token}&shop_id={shop_id}&sign={sign}"
        
        # Time range (last 15 days for example)
        time_from = int(time.time()) - (15 * 24 * 3600)
        time_to = int(time.time())
        
        params = {
            "time_range_field": "create_time",
            "time_from": time_from,
            "time_to": time_to,
            "page_size": 20
        }
        
        try:
            resp = requests.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get('error'):
                print(f"Shopee Error: {data['error']} - {data.get('message')}")
                continue
                
            order_sn_list = [o['order_sn'] for o in data.get('response', {}).get('order_list', [])]
            
            if order_sn_list:
                process_shopee_order_details(profile, order_sn_list)
                
        except Exception as e:
            print(f"Error fetching Shopee orders: {e}")

def process_shopee_order_details(profile, order_sn_list):
    """
    Fetches details for a list of order_sns and saves them.
    """
    path = "/order/get_order_detail"
    partner_id = int(profile.shopee_partner_id)
    shop_id = int(profile.shopee_shop_id)
    access_token = profile.shopee_access_token
    
    sign, timestamp = sign_shopee_request(path, partner_id, profile.shopee_partner_key, shop_id, access_token)
    
    url = f"{SHOPEE_API_URL}{path}?partner_id={partner_id}&timestamp={timestamp}&access_token={access_token}&shop_id={shop_id}&sign={sign}"
    
    params = {
        "order_sn_list": ",".join(order_sn_list),
        "response_optional_fields": "total_amount,shipping_carrier,actual_shipping_fee,create_time,item_list"
    }
    
    try:
        resp = requests.get(url, params=params)
        data = resp.json()
        
        for order in data.get('response', {}).get('order_list', []):
            save_shopee_order(profile.organization, order)
            
    except Exception as e:
        print(f"Error details Shopee: {e}")

def save_shopee_order(organization, order_data):
    """
    Maps Shopee fields to SaleTransaction and calculates margin.
    """
    order_sn = order_data['order_sn']
    amount = Decimal(order_data['total_amount'])
    create_time = timezone.datetime.fromtimestamp(order_data['create_time'], tz=timezone.utc)
    
    # Logistics
    shipping_carrier = order_data.get('shipping_carrier', 'Standard')
    actual_shipping_fee = Decimal(order_data.get('actual_shipping_fee', 0)) # Cost paid by seller usually
    
    # Find Fixed Cost
    fixed_cost = Decimal('0.00')
    is_fixed_applied = False
    try:
        cost_rule = LogisticsCostTable.objects.get(
            organization=organization, 
            platform='SHOPEE', 
            shipping_method=shipping_carrier
        )
        fixed_cost = cost_rule.fixed_cost_value
        if fixed_cost > 0:
            is_fixed_applied = True
    except LogisticsCostTable.DoesNotExist:
        pass

    # Save
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
    
    # Link Items (simplified)
    for item in order_data.get('item_list', []):
        item_sku = item.get('item_sku') or str(item.get('item_id'))
        # Try link...
