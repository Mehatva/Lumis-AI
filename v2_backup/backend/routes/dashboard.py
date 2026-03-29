"""Routes — Business & FAQ dashboard API."""
import json
import secrets
from flask import Blueprint, jsonify, request
from models import db
from models.business import Business
from models.faq import FAQ
from models.lead import Lead
from models.conversation import Conversation

dashboard_bp = Blueprint("dashboard", __name__)


# ─── Business ─────────────────────────────────────────────────────────────

@dashboard_bp.get("/api/businesses")
def list_businesses():
    businesses = Business.query.all()
    return jsonify([b.to_dict() for b in businesses])


@dashboard_bp.post("/api/businesses")
def create_business():
    data = request.get_json() or {}
    business = Business(
        name=data.get("name", "New Business"),
        niche=data.get("niche", "general"),
        phone=data.get("phone"),
        location=data.get("location"),
        location_url=data.get("location_url"),
        booking_url=data.get("booking_url"),
        instagram_page_id=data.get("instagram_page_id"),
        welcome_message=data.get("welcome_message", "Hi! How can I help you today? 😊"),
        tone=data.get("tone", "friendly"),
        plan=data.get("plan", "trial"),
        api_key=secrets.token_urlsafe(32),
    )
    db.session.add(business)
    db.session.commit()
    return jsonify(business.to_dict()), 201


@dashboard_bp.get("/api/businesses/<int:business_id>")
def get_business(business_id):
    business = Business.query.get_or_404(business_id)
    return jsonify(business.to_dict())


@dashboard_bp.patch("/api/businesses/<int:business_id>")
def update_business(business_id):
    business = Business.query.get_or_404(business_id)
    data = request.get_json() or {}
    allowed = ["name", "niche", "phone", "location", "location_url",
               "booking_url", "instagram_page_id", "welcome_message", "tone"]
    for field in allowed:
        if field in data:
            setattr(business, field, data[field])
    db.session.commit()
    return jsonify(business.to_dict())


# ─── FAQs ─────────────────────────────────────────────────────────────────

@dashboard_bp.get("/api/businesses/<int:business_id>/faqs")
def list_faqs(business_id):
    faqs = FAQ.query.filter_by(business_id=business_id).order_by(FAQ.priority.desc()).all()
    return jsonify([f.to_dict() for f in faqs])


@dashboard_bp.post("/api/businesses/<int:business_id>/faqs")
def create_faq(business_id):
    Business.query.get_or_404(business_id)
    data = request.get_json() or {}
    faq = FAQ(
        business_id=business_id,
        question=data.get("question", ""),
        keywords=json.dumps(data.get("keywords", [])),
        response=data.get("response", ""),
        cta_label=data.get("cta_label"),
        cta_url=data.get("cta_url"),
        priority=data.get("priority", 0),
    )
    db.session.add(faq)
    db.session.commit()
    return jsonify(faq.to_dict()), 201


@dashboard_bp.patch("/api/faqs/<int:faq_id>")
def update_faq(faq_id):
    faq = FAQ.query.get_or_404(faq_id)
    data = request.get_json() or {}
    if "question" in data:
        faq.question = data["question"]
    if "keywords" in data:
        faq.keywords = json.dumps(data["keywords"])
    if "response" in data:
        faq.response = data["response"]
    if "cta_label" in data:
        faq.cta_label = data["cta_label"]
    if "cta_url" in data:
        faq.cta_url = data["cta_url"]
    if "priority" in data:
        faq.priority = data["priority"]
    db.session.commit()
    return jsonify(faq.to_dict())


@dashboard_bp.delete("/api/faqs/<int:faq_id>")
def delete_faq(faq_id):
    faq = FAQ.query.get_or_404(faq_id)
    db.session.delete(faq)
    db.session.commit()
    return jsonify({"deleted": faq_id})


# ─── Analytics ────────────────────────────────────────────────────────────

@dashboard_bp.get("/api/businesses/<int:business_id>/analytics")
def get_analytics(business_id):
    Business.query.get_or_404(business_id)
    total_conversations = Conversation.query.filter_by(business_id=business_id).count()
    total_leads = Lead.query.filter_by(business_id=business_id).count()
    converted_leads = Lead.query.filter_by(business_id=business_id, is_converted=True).count()
    total_faqs = FAQ.query.filter_by(business_id=business_id).count()

    # Approximate message count from conversations
    convs = Conversation.query.filter_by(business_id=business_id).all()
    total_messages = sum(len(c.get_messages()) for c in convs)

    needs_attention_count = Lead.query.filter_by(business_id=business_id, needs_attention=True).count()

    return jsonify({
        "total_conversations": total_conversations,
        "total_messages": total_messages,
        "total_leads": total_leads,
        "converted_leads": converted_leads,
        "needs_attention_count": needs_attention_count,
        "conversion_rate": round(converted_leads / total_leads * 100, 1) if total_leads else 0,
        "total_faqs": total_faqs,
    })


# ─── Auth ─────────────────────────────────────────────────────────────────

@dashboard_bp.post("/api/auth")
def authenticate():
    from flask import current_app
    data = request.get_json() or {}
    password = data.get("password")
    
    admin_secret = current_app.config.get("ADMIN_SECRET", "admin123")
    
    if password == admin_secret:
        return jsonify({"token": "ok"}), 200
    return jsonify({"error": "Unauthorized"}), 401


# ─── Chat Demo ────────────────────────────────────────────────────────────

@dashboard_bp.post("/api/chat")
def chat_demo():
    from services.chatbot import ChatbotService
    data = request.get_json() or {}
    business_id = data.get("business_id")
    session_id = data.get("session_id", "demo-user")
    message = data.get("message", "")
    
    if not business_id or not message:
        return jsonify({"error": "Missing parameters"}), 400
        
    business = Business.query.get_or_404(business_id)
    chatbot = ChatbotService(business)
    
    reply = chatbot.process(session_id, message)
    return jsonify({"reply": reply})


@dashboard_bp.post("/api/businesses/<int:business_id>/auto-kb")
def auto_kb(business_id):
    business = Business.query.get_or_404(business_id)
    data = request.get_json() or {}
    url = data.get("url")
    print(f"DEBUG: Received Magic Import URL: {url}")
    if not url:
        return jsonify({"error": "URL is required"}), 400
    
    from services.scraper_service import ScraperService
    from services.ai_service import AIService
    
    # 1. Scrape
    text = ScraperService.scrape_url(url)
    if not text:
        return jsonify({"error": "Failed to extract text from URL"}), 500
        
    # 2. Generate FAQs
    ai = AIService(business)
    faqs_data = ai.generate_faqs_from_text(text, url=url)
    
    if not faqs_data:
        return jsonify({"error": "AI failed to generate FAQs from text"}), 500
        
    # 3. Save to DB (with Duplicate Check)
    existing_faqs = FAQ.query.filter_by(business_id=business_id).all()
    existing_questions = {f.question.lower().strip() for f in existing_faqs}
    
    new_faqs = []
    for item in faqs_data:
        question = item.get("question", "").strip()
        if question.lower() in existing_questions:
            print(f"DEBUG: Skipping duplicate FAQ: {question}")
            continue
            
        faq = FAQ(
            business_id=business_id,
            question=question,
            response=item.get("response", ""),
            keywords=json.dumps(item.get("keywords", [])),
            priority=item.get("priority", 5)
        )
        db.session.add(faq)
        new_faqs.append(faq)
        existing_questions.add(question.lower()) # Prevent duplicates within the same import
    
    db.session.commit()
    
    return jsonify({
        "message": f"Generated {len(new_faqs)} new FAQs",
        "faqs": [f.to_dict() for f in new_faqs],
        "new_count": len(new_faqs),
        "duplicate_count": len(faqs_data) - len(new_faqs)
    }), 201
