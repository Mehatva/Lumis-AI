"""Unit tests for the core chatbot engine."""
import json
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app
from models import db
from models.business import Business
from models.faq import FAQ
from models.conversation import Conversation
from services.chatbot import IntentDetector, ResponseBuilder, LeadCaptureFlow, ChatbotService


@pytest.fixture
def app():
    os.environ["MOCK_MODE"] = "true"
    os.environ["FLASK_ENV"] = "development"
    application = create_app()
    application.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    application.config["TESTING"] = True
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def business(app):
    with app.app_context():
        import uuid
        b = Business(
            name="Test Gym",
            niche="gym",
            phone="+91 99999 99999",
            location="Test City",
            booking_url="https://example.com/book",
            welcome_message="Welcome!",
            tone="friendly",
            plan="trial",
            api_key=f"test-api-key-{uuid.uuid4()}",
            is_active=True,
        )
        db.session.add(b)
        db.session.flush()
        bid = b.id

        faqs = [
            FAQ(
                business_id=bid,
                question="Pricing",
                keywords=json.dumps(["price", "cost", "membership", "how much"]),
                response="Our gym costs ₹999/month.",
                cta_label="Book Free Trial",
                cta_url="https://example.com/book",
                priority=10,
            ),
            FAQ(
                business_id=bid,
                question="Timings",
                keywords=json.dumps(["timing", "timings", "open", "hours", "time"]),
                response="We are open 6am–10pm.",
                priority=9,
            ),
            FAQ(
                business_id=bid,
                question="Location",
                keywords=json.dumps(["location", "address", "where"]),
                response="We are located at Test City.",
                cta_label="Get Directions",
                cta_url="https://maps.google.com",
                priority=8,
            ),
        ]
        for faq in faqs:
            db.session.add(faq)
        db.session.commit()
        return bid


# ─── IntentDetector tests ──────────────────────────────────────────────────

class TestIntentDetector:
    def test_exact_keyword_match(self, business, app):
        with app.app_context():
            faqs = FAQ.query.filter_by(business_id=business).all()
            result = IntentDetector.find_best_faq("what is the price?", faqs)
            assert result is not None
            assert result.question == "Pricing"

    def test_hindi_romanized_match(self, business, app):
        with app.app_context():
            faqs = FAQ.query.filter_by(business_id=business).all()
            result = IntentDetector.find_best_faq("how much membership cost", faqs)
            assert result is not None
            assert result.question == "Pricing"

    def test_timing_match(self, business, app):
        with app.app_context():
            faqs = FAQ.query.filter_by(business_id=business).all()
            result = IntentDetector.find_best_faq("what are your timings?", faqs)
            assert result is not None
            assert result.question == "Timings"

    def test_no_match(self, business, app):
        with app.app_context():
            faqs = FAQ.query.filter_by(business_id=business).all()
            result = IntentDetector.find_best_faq("do you have parking?", faqs)
            assert result is None


# ─── ResponseBuilder tests ─────────────────────────────────────────────────

class TestResponseBuilder:
    def test_response_with_cta(self, business, app):
        with app.app_context():
            faq = FAQ.query.filter_by(business_id=business, question="Pricing").first()
            reply = ResponseBuilder.build(faq)
            assert "₹999" in reply
            assert "Book Free Trial" in reply
            assert "https://example.com/book" in reply

    def test_response_without_cta(self, business, app):
        with app.app_context():
            faq = FAQ.query.filter_by(business_id=business, question="Timings").first()
            reply = ResponseBuilder.build(faq)
            assert "6am" in reply
            assert "http" not in reply  # No CTA link


# ─── Lead capture flow tests ───────────────────────────────────────────────

class TestLeadCaptureFlow:
    def test_trigger_keywords(self):
        assert LeadCaptureFlow.should_trigger("I want to book") is True
        assert LeadCaptureFlow.should_trigger("I'm interested") is True
        assert LeadCaptureFlow.should_trigger("what are your prices?") is False

    def test_name_capture_state(self, business, app):
        with app.app_context():
            conv = Conversation(
                session_id="test-session-1",
                business_id=business,
                state="capture_name",
            )
            db.session.add(conv)
            db.session.commit()

            reply = LeadCaptureFlow.handle(conv, "Rahul Sharma", business)
            assert "Rahul Sharma" in reply
            assert conv.state == "capture_phone"

    def test_phone_capture_and_lead_saved(self, business, app):
        with app.app_context():
            from models.lead import Lead
            conv = Conversation(
                session_id="test-session-2",
                business_id=business,
                state="capture_phone",
                temp_name="Rahul Sharma",
            )
            db.session.add(conv)
            db.session.commit()

            reply = LeadCaptureFlow.handle(conv, "+91 98765 00000", business)
            assert conv.temp_name is None or "Rahul Sharma" in conv.temp_name
            assert conv.state == "idle"

            lead = Lead.query.filter_by(sender_id="test-session-2").first()
            assert lead is not None
            assert lead.name == "Rahul Sharma"
            assert lead.phone == "+91 98765 00000"


# ─── ChatbotService integration test ──────────────────────────────────────

class TestChatbotService:
    def test_faq_reply(self, business, app):
        with app.app_context():
            b = Business.query.get(business)
            svc = ChatbotService(b)
            reply = svc.process("user-abc", "what is the membership price?")
            assert "₹999" in reply

    def test_lead_capture_trigger(self, business, app):
        with app.app_context():
            b = Business.query.get(business)
            svc = ChatbotService(b)
            reply = svc.process("user-xyz", "I want to book a slot")
            assert "name" in reply.lower()
