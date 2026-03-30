"""
Core Chatbot Engine
Handles: intent detection, FAQ matching, lead capture state machine,
         response building, and AI fallback orchestration.
"""
import re
from models import db
from models.faq import FAQ
from models.lead import Lead
from models.conversation import Conversation
from services.ai_service import AIService


class IntentDetector:
    """Matches incoming message text against FAQ keyword triggers."""

    @staticmethod
    def normalize(text: str) -> str:
        return re.sub(r"[^a-z0-9\s]", " ", text.lower()).strip()

    @staticmethod
    def _levenshtein_ratio(s1: str, s2: str) -> float:
        """Calculate similarity ratio between 0 and 1."""
        if not s1 or not s2: return 0.0
        if s1 == s2: return 1.0
        
        rows = len(s1) + 1
        cols = len(s2) + 1
        dist = [[0 for _ in range(cols)] for _ in range(rows)]

        for i in range(1, rows): dist[i][0] = i
        for i in range(1, cols): dist[0][i] = i

        for col in range(1, cols):
            for row in range(1, rows):
                cost = 0 if s1[row-1] == s2[col-1] else 1
                dist[row][col] = min(dist[row-1][col] + 1,      # deletion
                                 dist[row][col-1] + 1,      # insertion
                                 dist[row-1][col-1] + cost) # substitution
        
        return 1.0 - (dist[rows-1][cols-1] / max(len(s1), len(s2)))

    @staticmethod
    def score(message: str, keywords: list) -> int:
        """Return the number of keyword hits in the message with typo tolerance."""
        normalized = IntentDetector.normalize(message)
        msg_words = normalized.split()
        score = 0
        
        for kw in keywords:
            kw_norm = IntentDetector.normalize(kw)
            # 1. Direct substring match (good for phrases)
            if kw_norm in normalized:
                score += 1
                continue
                
            # 2. Fuzzy word match (good for typos in single keywords)
            kw_words = kw_norm.split()
            for kw_word in kw_words:
                best_word_score = 0
                for msg_word in msg_words:
                    # High threshold for accuracy (0.8)
                    ratio = IntentDetector._levenshtein_ratio(msg_word, kw_word)
                    if ratio >= 0.8:
                        best_word_score = 1
                        break
                score += best_word_score
        return score

    @staticmethod
    def find_best_faq(message: str, faqs: list):
        """Return the highest-scoring FAQ or None if no match."""
        best, best_score = None, 0
        for faq in faqs:
            s = IntentDetector.score(message, faq.get_keywords())
            # weight by FAQ priority too
            weighted = s * (1 + faq.priority * 0.1)
            if weighted > best_score:
                best_score = weighted
                best = faq
        return best if best_score > 0 else None


class ResponseBuilder:
    """Builds a formatted reply from an FAQ match."""

    @staticmethod
    def build(faq: FAQ) -> str:
        text = faq.response
        if faq.cta_label and faq.cta_url:
            text += f"\n\n👉 [{faq.cta_label}]({faq.cta_url})"
        return text


class LeadCaptureFlow:
    """
    State machine for collecting lead details.
    States: idle → capture_name → capture_phone → done
    """

    TRIGGER_KEYWORDS = ["book", "interested", "want", "appointment", "contact", "call me", "reach"]

    @staticmethod
    def should_trigger(message: str) -> bool:
        normalized = re.sub(r"[^a-z0-9\s]", " ", message.lower()).strip()
        words = normalized.split()
        
        for kw in LeadCaptureFlow.TRIGGER_KEYWORDS:
            for word in words:
                # Use a slightly more relaxed threshold for engagement (0.75)
                if IntentDetector._levenshtein_ratio(word, kw) >= 0.75:
                    return True
        return False

    @staticmethod
    def handle(conv: Conversation, user_message: str, business_id: int) -> str:
        """
        Process lead capture state transitions.
        Returns the reply text and updates conv.state in-place.
        """
        state = conv.state

        if state == "capture_name":
            conv.temp_name = user_message.strip()
            conv.state = "capture_phone"
            return (
                f"Nice to meet you, *{conv.temp_name}*! 😊\n"
                "What's the best phone number to reach you on?"
            )

        if state == "capture_phone":
            phone = user_message.strip()
            # Save lead
            lead = Lead(
                business_id=business_id,
                platform="instagram",
                sender_id=conv.session_id,
                name=conv.temp_name,
                phone=phone,
            )
            db.session.add(lead)
            db.session.commit()
            conv.state = "idle"
            conv.temp_name = None
            return (
                f"✅ Got it! We've saved your details and our team will reach out to "
                f"*{phone}* shortly. Looking forward to connecting! 🎉"
            )

        return None  # Not in a capture state


class ChatbotService:
    """
    Top-level orchestrator. Receives an incoming message + business context,
    returns the appropriate reply.
    """

    def __init__(self, business):
        self.business = business
        self.ai = AIService(business)

    def get_or_create_conversation(self, session_id: str) -> Conversation:
        conv = Conversation.query.filter_by(session_id=session_id).first()
        if not conv:
            conv = Conversation(
                session_id=session_id,
                business_id=self.business.id,
            )
            db.session.add(conv)
            db.session.commit()
        return conv

    def process(self, session_id: str, user_message: str) -> str:
        """Main entry point. Returns reply string."""
        conv = self.get_or_create_conversation(session_id)
        conv.add_message("user", user_message)

        # 1. Handle active lead capture flow
        if conv.state in ("capture_name", "capture_phone"):
            reply = LeadCaptureFlow.handle(conv, user_message, self.business.id)
            conv.add_message("bot", reply)
            db.session.commit()
            return reply

        # 2. Check if user explicitly wants to be contacted
        if LeadCaptureFlow.should_trigger(user_message) and conv.state == "idle":
            conv.state = "capture_name"
            db.session.commit()
            reply = (
                "That's great! I'd love to connect you with our team. 🙌\n"
                "Could I get your *name* first?"
            )
            conv.add_message("bot", reply)
            db.session.commit()
            return reply

        # 3. FAQ intent matching
        faqs = FAQ.query.filter_by(business_id=self.business.id).all()
        matched_faq = IntentDetector.find_best_faq(user_message, faqs)

        if matched_faq:
            reply = ResponseBuilder.build(matched_faq)
        else:
            # 4. AI fallback (The "2% solution")
            history = conv.get_messages()
            reply = self.ai.get_reply(history, user_message)

            # Flag for human attention in the Lead Inbox
            lead = Lead.query.filter_by(business_id=self.business.id, sender_id=session_id).first()
            if not lead:
                # Create a "Ghost Lead" so the owner sees the unanswered question
                lead = Lead(
                    business_id=self.business.id,
                    platform="instagram",
                    sender_id=session_id,
                    note=f"Unanswered: {user_message[:50]}..."
                )
                db.session.add(lead)
            lead.needs_attention = True
            db.session.commit()

        # Append a light CTA nudge for non-lead messages (only randomly, ~20%)
        import random
        if matched_faq and self.business.booking_url and random.random() < 0.2:
            reply += f"\n\n💬 Have more questions? Just ask!"

        conv.add_message("bot", reply)
        db.session.commit()
        return reply
