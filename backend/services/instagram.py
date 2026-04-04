"""Instagram Graph API service — send messages and parse incoming webhooks."""
import os
import requests
from flask import current_app

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"


class InstagramService:

    def __init__(self, access_token: str = None, page_id: str = None):
        self.access_token = access_token or os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
        self.page_id = page_id or os.getenv("INSTAGRAM_PAGE_ID", "me")

    # ─── Webhook verification ──────────────────────────────────────────────

    @staticmethod
    def verify_webhook(mode: str, token: str, challenge: str):
        """
        Meta sends a GET request to verify the webhook endpoint.
        Returns challenge string if valid, else None.
        """
        expected_token = os.getenv("INSTAGRAM_VERIFY_TOKEN", "verify123")
        if mode == "subscribe" and token == expected_token:
            return challenge
        return None

    @staticmethod
    def subscribe_app_to_page(page_id: str, page_token: str) -> bool:
        """
        Subscribes the Facebook Page to the App's webhooks.
        This is required for the Page to start sending message events to our server.
        """
        url = f"{GRAPH_API_BASE}/{page_id}/subscribed_apps"
        params = {
            "access_token": page_token,
            "subscribed_fields": "messages,messaging_postbacks,messaging_optins"
        }
        try:
            r = requests.post(url, params=params, timeout=10)
            r.raise_for_status()
            print(f"[InstagramService] Subscribed page {page_id} to webhooks.")
            return True
        except Exception as e:
            print(f"[InstagramService] Subscription error for {page_id}: {e}")
            return False

    # ─── Parse incoming payload ────────────────────────────────────────────

    @staticmethod
    def parse_incoming(payload: dict) -> list[dict]:
        """
        Parse the Instagram webhook payload.
        Returns list of {sender_id, message_text} dicts.
        """
        messages = []
        try:
            for entry in payload.get("entry", []):
                for messaging in entry.get("messaging", []):
                    sender_id = messaging.get("sender", {}).get("id")
                    message_obj = messaging.get("message", {})
                    is_echo = message_obj.get("is_echo", False)
                    text = message_obj.get("text")
                    
                    if sender_id and text and not is_echo:
                        messages.append({"sender_id": sender_id, "text": text})
        except Exception as e:
            current_app.logger.error(f"[InstagramService] parse error: {e}")
        return messages

    def send_typing_indicator(self, recipient_id: str, on: bool = True) -> dict:
        """
        Send a typing indicator (typing_on or typing_off) to the user.
        Uses the '/me/messages' endpoint which is more robust for Page tokens.
        """
        mock_mode = os.getenv("MOCK_MODE", "true").lower() == "true"
        if mock_mode:
            return {"mock": True}

        if not self.access_token:
            return {"error": "missing_token"}

        # Use 'me' instead of explicit ID to ensure the token's context is used
        url = f"{GRAPH_API_BASE}/me/messages"
        payload = {
            "recipient": {"id": recipient_id},
            "sender_action": "typing_on" if on else "typing_off",
        }
        params = {"access_token": self.access_token}

        try:
            r = requests.post(url, json=payload, params=params, timeout=10)
            r.raise_for_status()
            return r.json()
        except requests.HTTPError as e:
            error_details = "Unknown"
            try:
                error_details = r.json()
            except:
                error_details = r.text
            current_app.logger.error(f"[InstagramService] Typing indicator error: {e}. Body: {error_details}")
            return {"error": str(e), "details": error_details}
        except Exception as e:
            current_app.logger.error(f"[InstagramService] Typing indicator unexpected error: {e}")
            return {"error": str(e)}

    # ─── Send message ──────────────────────────────────────────────────────

    def send_message(self, recipient_id: str, text: str) -> dict:
        """
        Send a text message to a user via the Instagram Messaging API.
        Uses the '/me/messages' endpoint.
        """
        mock_mode = os.getenv("MOCK_MODE", "true").lower() == "true"

        if mock_mode:
            current_app.logger.info(f"\n[MOCK] → Instagram reply to {recipient_id}:\n{text}\n")
            return {"mock": True, "recipient_id": recipient_id, "text": text}

        if not self.access_token:
            current_app.logger.error("[InstagramService] ERROR: No access token provided.")
            return {"error": "missing_token"}

        # Use 'me/messages' for Page Tokens
        url = f"{GRAPH_API_BASE}/me/messages"
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": text},
            "messaging_type": "RESPONSE",
        }
        params = {"access_token": self.access_token}

        # Log token prefix for debugging (securely)
        token_prefix = self.access_token[:10] if self.access_token else "NONE"
        current_app.logger.info(f"[InstagramService] Attempting send to {recipient_id} using token {token_prefix}...")

        try:
            r = requests.post(url, json=payload, params=params, timeout=10)
            r.raise_for_status()
            res = r.json()
            current_app.logger.warning(f"[InstagramService] SUCCESS: Message sent to {recipient_id}. Mid: {res.get('message_id')}")
            return res
        except requests.HTTPError as e:
            meta_error = "Unknown HTTP Error"
            try:
                meta_error = r.json()
            except Exception:
                meta_error = r.text
            current_app.logger.error(f"[InstagramService] Meta API Error: {e}. Body: {meta_error}")
            return {"error": "meta_api_error", "details": meta_error}
        except requests.RequestException as e:
            current_app.logger.error(f"[InstagramService] Network Error: {e}")
            return {"error": "network_error", "details": str(e)}

    # ─── OAuth Flow ────────────────────────────────────────────────────────

    @staticmethod
    def get_auth_url(redirect_uri: str) -> str:
        """
        Generates the Meta OAuth URL for Instagram Messaging permissions.
        """
        app_id = os.getenv("META_APP_ID", "")
        if not app_id:
            raise ValueError("META_APP_ID is not configured in environment variables.")

        # Required scopes for Instagram Messaging
        scopes = [
            "public_profile",
            "instagram_basic",
            "instagram_manage_messages",
            "pages_manage_metadata",
            "pages_read_engagement",
            "pages_show_list",
            "business_management"
        ]
        scope_str = ",".join(scopes)
        
        return (
            f"https://www.facebook.com/v19.0/dialog/oauth?"
            f"client_id={app_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scope_str}"
            f"&response_type=code"
        )

    @staticmethod
    def exchange_code_for_token(code: str, redirect_uri: str) -> dict:
        """
        Exchanges the temporal OAuth code for a short-lived user token.
        """
        app_id = os.getenv("META_APP_ID", "")
        app_secret = os.getenv("META_APP_SECRET", "")
        
        url = f"{GRAPH_API_BASE}/oauth/access_token"
        params = {
            "client_id": app_id,
            "redirect_uri": redirect_uri,
            "client_secret": app_secret,
            "code": code
        }
        
        try:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"[InstagramService] Token exchange error: {e}")
            return {"error": str(e)}

    @staticmethod
    def get_long_lived_token(short_token: str) -> str:
        """
        Upgrades a short-lived user token to a 60-day long-lived token.
        """
        app_id = os.getenv("META_APP_ID", "")
        app_secret = os.getenv("META_APP_SECRET", "")
        
        url = f"{GRAPH_API_BASE}/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": short_token
        }
        
        try:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            return r.json().get("access_token", "")
        except Exception as e:
            print(f"[InstagramService] Long-lived token error: {e}")
            return ""

    @staticmethod
    def get_managed_pages(user_token: str) -> list:
        """
        Fetches the list of Facebook Pages managed by the user.
        """
        url = f"{GRAPH_API_BASE}/me/accounts"
        params = {"access_token": user_token}
        
        try:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            return r.json().get("data", [])
        except Exception as e:
            print(f"[InstagramService] Managed pages error: {e}")
            return []

    @staticmethod
    def get_ig_account_for_page(page_id: str, page_token: str) -> str:
        """
        Identifies the linked Instagram Business ID for a specific Page.
        """
        url = f"{GRAPH_API_BASE}/{page_id}"
        params = {
            "fields": "instagram_business_account",
            "access_token": page_token
        }
        
        try:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            return data.get("instagram_business_account", {}).get("id", "")
        except Exception as e:
            print(f"[InstagramService] IG account lookup error: {e}")
            return ""

    @staticmethod
    def get_ig_account_details(ig_id: str, token: str) -> dict:
        """
        Fetches details (like username) for a specific Instagram Business account.
        """
        url = f"{GRAPH_API_BASE}/{ig_id}"
        params = {
            "fields": "username,name",
            "access_token": token
        }
        try:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"[InstagramService] IG details lookup error: {e}")
            return {}
