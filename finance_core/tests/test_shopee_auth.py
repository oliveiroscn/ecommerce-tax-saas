from django.test import TestCase
from finance_core.shopee_utils import sign_shopee_request
import hmac
import hashlib

class ShopeeAuthTest(TestCase):
    def test_sign_shopee_request(self):
        partner_id = 123456
        partner_key = "secretkey"
        path = "/shop/auth_partner"
        
        # Call function
        sign, timestamp = sign_shopee_request(path, partner_id, partner_key)
        
        # Verify
        base_string = f"{partner_id}{path}{timestamp}"
        expected_sign = hmac.new(
            partner_key.encode('utf-8'),
            base_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        self.assertEqual(sign, expected_sign)
        print(f"Signature Verified: {sign}")
