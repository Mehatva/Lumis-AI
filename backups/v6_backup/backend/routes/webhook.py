"""Routes — Instagram webhook endpoints."""
from flask import Blueprint, request, jsonify, current_app
from models.business import Business
from services.instagram import InstagramService
from services.chatbot import ChatbotService

webhook_bp = Blueprint("webhook", __name__)


@webhook_bp.get("/webhook/instagram")
def verify_instagram():
    """Meta calls this GET endpoint to verify the webhook subscription."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    result = InstagramService.verify_webhook(mode, token, challenge)
    if result:
        return result, 200
    return "Verification failed", 403


@webhook_bp.post("/webhook/instagram")
def handle_instagram():
    """
    Receives inbound Instagram DMs.
    Looks up the business by INSTAGRAM_PAGE_ID, runs the chatbot, sends reply.
    """
    payload = request.get_json(silent=True) or {}

    # Determine which page this webhook is for
    page_id = None
    try:
        page_id = payload["entry"][0]["id"]
    except (KeyError, IndexError):
        pass

    # Load business record
    business = None
    if page_id:
        business = Business.query.filter_by(instagram_page_id=page_id, is_active=True).first()

    # Fallback: use first active business (useful during demo/mock mode)
    if not business:
        business = Business.query.filter_by(is_active=True).first()

    if not business:
        current_app.logger.warning("No active business found for incoming webhook.")
        return jsonify({"status": "no_business"}), 200  # Always return 200 to Meta

    # Parse messages
    insta = InstagramService(access_token=business.access_token)
    messages = InstagramService.parse_incoming(payload)

    chatbot = ChatbotService(business)

    for msg in messages:
        sender_id = msg["sender_id"]
        text = msg["text"]

        current_app.logger.info(f"[Webhook] From {sender_id}: {text}")

        reply = chatbot.process(sender_id, text)
        insta.send_message(sender_id, reply)

    return jsonify({"status": "ok"}), 200
