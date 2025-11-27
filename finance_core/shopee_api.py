import hmac
import hashlib
import time
import requests
import json

SHOPEE_API_URL = "https://partner.shopeemobile.com/api/v2"

class ShopeeClient:
    def __init__(self, partner_id, partner_key, access_token=None, shop_id=None):
        self.partner_id = int(partner_id)
        self.partner_key = partner_key
        self.access_token = access_token
        self.shop_id = int(shop_id) if shop_id else None

    def _generate_signature(self, path, access_token=None, shop_id=None):
        """
        Generates HMAC-SHA256 signature.
        Base String: partner_id + path + timestamp + [access_token] + [shop_id]
        """
        timestamp = int(time.time())
        base_string = f"{self.partner_id}{path}{timestamp}"
        
        if access_token:
            base_string += f"{access_token}"
        if shop_id:
            base_string += f"{shop_id}"
            
        sign = hmac.new(
            self.partner_key.encode('utf-8'),
            base_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return sign, timestamp

    def _make_request(self, path, params=None):
        """
        Helper to make signed requests.
        """
        if params is None:
            params = {}
            
        sign, timestamp = self._generate_signature(path, self.access_token, self.shop_id)
        
        url = f"{SHOPEE_API_URL}{path}"
        
        # Common params
        query_params = {
            "partner_id": self.partner_id,
            "timestamp": timestamp,
            "sign": sign,
            "access_token": self.access_token,
            "shop_id": self.shop_id
        }
        
        # Merge specific params
        query_params.update(params)
        
        response = requests.get(url, params=query_params)
        response.raise_for_status()
        return response.json()

    def get_user_info(self):
        """
        Test method to check connectivity.
        Wraps /seller/get_shop_info (or similar simple endpoint).
        """
        path = "/shop/get_shop_info"
        return self._make_request(path)

    def get_order_list(self, time_from, time_to, page_size=20):
        """
        Wraps /order/get_order_list
        """
        path = "/order/get_order_list"
        params = {
            "time_range_field": "create_time",
            "time_from": time_from,
            "time_to": time_to,
            "page_size": page_size
        }
        return self._make_request(path, params)

    def get_order_detail(self, order_sn_list):
        """
        Wraps /order/get_order_detail
        """
        path = "/order/get_order_detail"
        params = {
            "order_sn_list": ",".join(order_sn_list),
            "response_optional_fields": "total_amount,shipping_carrier,actual_shipping_fee,create_time,item_list"
        }
        return self._make_request(path, params)
