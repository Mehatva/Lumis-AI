import base64
import hashlib
import hmac
import json
import logging
from config import get_config

logger = logging.getLogger(__name__)
config = get_config()

class ComplianceService:
    @staticmethod
    def parse_signed_request(signed_request):
        """
        Parses and verifies a Meta signed_request.
        Format: encoded_sig.payload
        """
        try:
            if not signed_request or '.' not in signed_request:
                return None

            encoded_sig, payload = signed_request.split('.', 2)
            
            # Decode signature
            sig = base64.urlsafe_b64decode(encoded_sig + "==")
            
            # Decode data
            data = json.loads(base64.urlsafe_b64decode(payload + "==").decode('utf-8'))
            
            # Verify signature
            secret = config.META_APP_SECRET
            if not secret:
                logger.warning("META_APP_SECRET not configured. Skipping signature verification (INSECURE).")
                return data

            expected_sig = hmac.new(
                secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).digest()

            if not hmac.compare_digest(sig, expected_sig):
                logger.error("Invalid Meta signed_request signature.")
                return None

            return data
        except Exception as e:
            logger.error(f"Error parsing signed_request: {e}")
            return None

    @staticmethod
    def handle_data_deletion(user_id):
        """
        Handles the data deletion log as required by Meta.
        Returns a confirmation URL and a unique deletion code.
        """
        try:
            # TODO: Add logic to mark the Business record for deletion
            # Or just log the request if that's the preferred policy
            
            confirmation_code = f"DEL-{hashlib.sha1(str(user_id).encode()).hexdigest()[:10].upper()}"
            url = f"{config.BASE_URL}/api/auth/deletion-status/{confirmation_code}"
            
            return {
                "url": url,
                "confirmation_code": confirmation_code
            }
        except Exception as e:
            logger.error(f"Error handling data deletion: {e}")
            return None
