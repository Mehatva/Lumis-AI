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

    # Load authentic business record
    business = None
    if page_id:
        business = Business.query.filter_by(instagram_page_id=page_id, is_active=True).first()

    # SECURITY LOCKDOWN: We no longer fallback to a random business. 
    # The webhook MUST match a registered Instagram Page ID.
    if not business:
        current_app.logger.warning(f"Unauthorized Webhook Context: No active business found for page_id {page_id}")
        return jsonify({"status": "ignored_no_business_match"}), 200

    if not business.access_token:
        current_app.logger.warning(f"Business {business.name} has no Meta Access Token configured.")
        return jsonify({"status": "ignored_no_token"}), 200

    # Parse messages
    insta = InstagramService(access_token=business.access_token)
    messages = InstagramService.parse_incoming(payload)

    chatbot = ChatbotService(business)

    for msg in messages:
        sender_id = msg["sender_id"]
        text = msg["text"]

        current_app.logger.info(f"[Live Webhook] From {sender_id} to Page {page_id}: {text}")

        # Generate response using AI engine
        reply = chatbot.process(sender_id, text)
        
        # Dispatch to real Meta API
        insta.send_message(sender_id, reply)

    return jsonify({"status": "ok"}), 200

