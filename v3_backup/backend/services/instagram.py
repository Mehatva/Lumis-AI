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
        except requests.RequestException as e:
            print(f"[InstagramService] send error: {e}")
            return {"error": str(e)}
