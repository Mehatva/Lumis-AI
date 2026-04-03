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
from services.email_service import EmailService


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
        
        # Stop words to ignore during single-word matching
        STOP_WORDS = {"how", "what", "where", "when", "why", "is", "are", "the", "a", "an", "do", "you", "get"}

        for kw in keywords:
            kw_norm = IntentDetector.normalize(kw)
            kw_words = kw_norm.split()
            
            # 1. Direct phrase match (highest confidence)
            if kw_norm in normalized:
                # Give more weight to full phrase matches
                score += (2 if len(kw_words) > 1 else 1)
                continue
                
            # 2. Fuzzy word match (only for meaningful words)
            if len(kw_words) == 1:
                if kw_norm in STOP_WORDS: continue # Skip common words as single triggers
                
                for msg_word in msg_words:
                    if IntentDetector._levenshtein_ratio(msg_word, kw_norm) >= 0.85:
                        score += 1
                        break
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
        
        # EXCLUSIONS: Words that might fuzzy match but aren't lead intents for a gym
        EXCLUSIONS = {"teach", "chess", "game", "play"}
        
        for kw in LeadCaptureFlow.TRIGGER_KEYWORDS:
            for word in words:
                if word in EXCLUSIONS: continue
                # Higher threshold (0.85) to avoid "teach" -> "reach" false positive
                if IntentDetector._levenshtein_ratio(word, kw) >= 0.85:
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
            # Smart name extraction
            # Handles "My name is Ayman", "I am Ayman", etc.
            clean = re.sub(r"(my name is|i am|i'm|call me|name is)\s+", "", user_message, flags=re.IGNORECASE).strip()
            # Take the first 2 words max if it's long
            name = " ".join(clean.split()[:2]).title()
            conv.temp_name = name
            conv.state = "capture_phone"
            return (
                f"Nice to meet you, *{name}*! 😊\n"
                "What's the best phone number to reach you on?"
            )

        if state == "capture_phone":
            # Extract only the phone number part (digits and optional +)
            match = re.search(r"(\+?\d[\d\s\-]{9,}\d)", user_message)
            phone = match.group(1).strip() if match else user_message.strip()
            
            conv.temp_phone = phone
            conv.state = "confirm_details"
            return (
                f"Got it! Let me confirm those details:\n\n"
                f"👤 Name: *{conv.temp_name}*\n"
                f"📞 Phone: *{conv.temp_phone}*\n\n"
                "Is this correct? (Reply *YES* to confirm or *NO* to edit) ✅"
            )

        if state == "confirm_details":
            choice = user_message.lower().strip()
            if "yes" in choice or "correct" in choice or "ok" in choice:
                # Find and update existing lead
                lead = Lead.query.filter_by(business_id=business_id, sender_id=conv.session_id).first()
                if not lead:
                    lead = Lead(business_id=business_id, platform="instagram", sender_id=conv.session_id)
                    db.session.add(lead)
                
                lead.name = conv.temp_name
                lead.phone = conv.temp_phone
                lead.needs_attention = True  # New leads need attention
                
                db.session.commit()
                conv.state = "idle"
                name, phone = conv.temp_name, conv.temp_phone
                conv.temp_name = None
                conv.temp_phone = None
                return (
                    f"✅ All set, *{name}*! We've saved your details and our team will reach out to "
                    f"*{phone}* shortly. Looking forward to connecting! 🎉"
                )
            elif "no" in choice or "wrong" in choice or "edit" in choice:
                conv.state = "capture_name"
                return "No problem! Let's try again. 😊\n\nWhat is your *name*?"

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
        # 1. Primary lookup by both session_id and business_id
        conv = Conversation.query.filter_by(session_id=session_id, business_id=self.business.id).first()
        if conv:
            return conv

        # 2. Safety check: maybe it exists for another business? 
        # If the DB has a global UNIQUE constraint, we must handle it.
        # But logically, it should only be unique for this business.
        try:
            conv = Conversation(
                session_id=session_id,
                business_id=self.business.id,
            )
            db.session.add(conv)
            db.session.commit()
            return conv
        except Exception as e:
            db.session.rollback()
            # If still failing, let's try to regain control of the record if it belongs to someone else
            # (In a real SaaS, we'd handle this more gracefully, but for demo, let's just make it work)
            conv = Conversation.query.filter_by(session_id=session_id).first()
            if conv:
                conv.business_id = self.business.id
                db.session.commit()
                return conv
            raise e

    def process(self, session_id: str, user_message: str) -> str:
        """Main entry point. Returns reply string with usage gating."""
        
        # ─── SUPPORT MODE (Human Handoff) ───
        # If the business has manually muted the bot for human support
        if self.business.support_mode:
            current_app.logger.info(f"Support Mode Active for {self.business.name}. AI is muted.")
            # Return a subtle message or silence depending on preference. 
            # We return a placeholder that the webhook can choose to ignore or send.
            return (
                "👋 A human specialist from our team is currently reviewing our chat "
                "to provide you with the most accurate assistance. Please hold on! 😊"
            )

        # ─── USAGE GATE ───
        # 1. Check if business has reached its plan limit
        if self.business.credits_used >= self.business.credits_limit:
            # Inform the user politely as discussed
            return (
                "We're experiencing high volume! 😊\n"
                f"Please call us directly at *{self.business.phone or 'our office'}* for immediate assistance. "
                "We look forward to helping you!"
            )

        conv = self.get_or_create_conversation(session_id)
        conv.add_message("user", user_message)

        # 0. Ensure a lead placeholder exists for tracking
        lead = Lead.query.filter_by(business_id=self.business.id, sender_id=session_id).first()
        if not lead:
            lead = Lead(
                business_id=self.business.id,
                platform="instagram",
                sender_id=session_id,
                note=f"First contact: {user_message[:50]}..."
            )
            db.session.add(lead)
            db.session.commit()

        # 1. Handle active lead capture flow
        if conv.state in ("capture_name", "capture_phone", "confirm_details"):
            reply = LeadCaptureFlow.handle(conv, user_message, self.business.id)
            conv.add_message("bot", reply)
            db.session.commit()
            return reply

        # 2. Human Escape Hatch
        human_keywords = ["human", "real person", "specialist", "agent", "manager", "talk to someone"]
        if any(kw in user_message.lower() for kw in human_keywords):
            reply = (
                "I understand! I'm flagging this conversation for our *Team Specialist* right now. 🔔\n"
                "They will review our chat and get back to you here as soon as possible. "
                "Is there anything specific you'd like them to know? 😊"
            )
            lead.needs_attention = True
            db.session.commit()
            conv.add_message("bot", reply)
            return reply

        # 3. Check if user explicitly wants to be contacted
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

        # 4. Personalized AI Response (RAG)
        faqs = FAQ.query.filter_by(business_id=self.business.id).all()
        history = conv.get_messages()
        reply = self.ai.get_reply(history, user_message, faqs)

        # 5. Intelligence: Flag for human attention if it's an AI fallback
        if "personally flagged this" in reply:
            lead.needs_attention = True
        
        # Update note with latest activity if name isn't set yet
        if not lead.name:
            lead.note = f"Latest activity: {user_message[:50]}..."

        db.session.commit()

        # Append a light CTA nudge randomly (~15%)
        import random
        if self.business.booking_url and random.random() < 0.15:
            reply += f"\n\n💬 Have more questions? Just ask!"

        conv.add_message("bot", reply)
        
        # ─── INCREMENT CREDITS & CHECK THRESHOLDS ───
        self.business.credits_used += 1
        
        # 80% Threshold Detection
        threshold_80 = int(self.business.credits_limit * 0.8)
        if self.business.credits_used == threshold_80:
            EmailService.send_usage_alert(self.business, 80)
            
        # 100% Threshold Detection
        if self.business.credits_used >= self.business.credits_limit:
            EmailService.send_limit_reached(self.business)
            
        db.session.commit()
        
        return reply
