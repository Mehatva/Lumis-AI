"""Instagram Graph API service — send messages and parse incoming webhooks."""
import os
import requests


GRAPH_API_BASE = "https://graph.facebook.com/v19.0"


class InstagramService:

    def __init__(self, access_token: str = None):
        self.access_token = access_token or os.getenv("INSTAGRAM_ACCESS_TOKEN", "")

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
                    text = messaging.get("message", {}).get("text")
                    if sender_id and text:
                        messages.append({"sender_id": sender_id, "text": text})
        except Exception as e:
            print(f"[InstagramService] parse error: {e}")
        return messages

    def send_typing_indicator(self, recipient_id: str, on: bool = True) -> dict:
        """
        Send a typing indicator to a user.
        on=True: "typing_on", on=False: "typing_off"
        """
        mock_mode = os.getenv("MOCK_MODE", "true").lower() == "true"
        if mock_mode:
            print(f"[MOCK] Typing indicator {'ON' if on else 'OFF'} for {recipient_id}")
            return {"mock": True}

        if not self.access_token:
            return {"error": "missing_token"}

        action = "typing_on" if on else "typing_off"
        url = f"{GRAPH_API_BASE}/me/messages"
        payload = {
            "recipient": {"id": recipient_id},
            "sender_action": action
        }
        params = {"access_token": self.access_token}

        try:
            r = requests.post(url, json=payload, params=params, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"[InstagramService] Typing indicator error: {e}")
            return {"error": str(e)}

    # ─── Send message ──────────────────────────────────────────────────────

    def send_message(self, recipient_id: str, text: str) -> dict:
        """
        Send a text message to a user via the Instagram Messaging API.
        In MOCK_MODE, this just prints the message.
        """
        mock_mode = os.getenv("MOCK_MODE", "true").lower() == "true"

        if mock_mode:
            print(f"\n[MOCK] → Instagram reply to {recipient_id}:\n{text}\n")
            return {"mock": True, "recipient_id": recipient_id, "text": text}

        if not self.access_token:
            print("[InstagramService] ERROR: No access token provided.")
            return {"error": "missing_token"}

        url = f"{GRAPH_API_BASE}/me/messages"
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": text},
            "messaging_type": "RESPONSE",
        }
        params = {"access_token": self.access_token}

        try:
            r = requests.post(url, json=payload, params=params, timeout=10)
            r.raise_for_status()
            return r.json()
        except requests.HTTPError as e:
            # Safely attempt to parse Meta's specific JSON error response
            meta_error = "Unknown HTTP Error"
            try:
                meta_error = r.json()
            except Exception:
                pass
            print(f"[InstagramService] Meta API Error: {meta_error}")
            return {"error": "meta_api_error", "details": meta_error}
        except requests.RequestException as e:
            print(f"[InstagramService] Network Error: {e}")
            return {"error": "network_error", "details": str(e)}

    # ─── OAuth Flow ────────────────────────────────────────────────────────

    @staticmethod
    def get_auth_url(redirect_uri: str) -> str:
        """
        Generates the Meta OAuth URL for Instagram Messaging permissions.
        """
        app_id = os.getenv("META_APP_ID", "")
        # Required scopes for Instagram Messaging
        scopes = [
            "instagram_basic",
            "instagram_manage_messages",
            "pages_manage_metadata",
            "pages_show_list"
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
