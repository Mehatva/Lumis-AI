"""
AI Service — OpenAI GPT fallback for unmatched queries.
"""
import os
import json
from openai import OpenAI
try:
    from groq import Groq
except ImportError:
    Groq = None

_openai_client = None
_groq_client = None


def get_openai_client():
    global _openai_client
    if _openai_client is None:
        import httpx
        _openai_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            http_client=httpx.Client()
        )
    return _openai_client


def get_groq_client():
    global _groq_client
    if _groq_client is None and Groq:
        import httpx
        _groq_client = Groq(
            api_key=os.getenv("GROQ_API_KEY", ""),
            http_client=httpx.Client()
        )
    return _groq_client


class AIService:
    def __init__(self, business):
        self.business = business

    def _system_prompt(self, faqs_text: str = "") -> str:
        b = self.business
        prompt = (
            f"You are a helpful customer support chatbot for *{b.name}*, "
            f"a {b.niche} business located at {b.location or 'their location'}. "
            f"Your tone is {b.tone or 'friendly'}. "
            "Keep replies short (2–4 sentences), helpful, and conversational. "
            "Use emojis sparingly. Never make up prices or information you don't know.\n\n"
            "**STRICT FORMATTING RULES:**\n"
            "- ALWAYS use bullet points (•) for lists like timings, membership plans, or classes.\n"
            "- ALWAYS use bold text (with asterisks, like *text*) for key terms, prices (e.g., *₹999*), and headers.\n"
            "- Use clean line breaks to separate different pieces of information.\n\n"
            "**EXAMPLE OF A PERFECT RESPONSE:**\n"
            "\"Hey! Here are our current *Membership Plans* at FlexZone Gym:\n"
            "• *Basic*: ₹999/month (Gym access 6am–10pm)\n"
            "• *Standard*: ₹1,499/month (Includes 2 Group classes/week)\n\n"
            "Does one of these fit what you're looking for? 💪\""
        )
        
        if b.knowledge_base:
            prompt += (
                "\n\n**YOUR INNATE KNOWLEDGE**:\n"
                "You have been specially trained on this business. Use the following core profile "
                "to understand the business context and history:\n"
                f"{b.knowledge_base}\n"
            )

        if faqs_text:
            prompt += (
                "\n\n**ACTIVE QUICK QUESTIONS (FAQs)**:\n"
                "Use these specific Q&As for immediate accuracy on frequently asked details:\n"
                f"{faqs_text}\n"
            )
        
        prompt += (
            f"\nBooking link: {b.booking_url or 'N/A'}. "
            f"Phone: {b.phone or 'N/A'}."
        )
        return prompt

    def get_reply(self, history: list, message: str, faqs: list = None) -> str:
        """
        Call Groq (preferred) or OpenAI Chat Completions with conversation history and FAQ context.
        """
        groq_api_key = os.getenv("GROQ_API_KEY", "")
        openai_api_key = os.getenv("OPENAI_API_KEY", "")

        faqs_text = ""
        if faqs:
            for f in faqs:
                faqs_text += f"- Q: {f.question}\n  A: {f.response}\n"

        system_content = self._system_prompt(faqs_text)

        # 1. Try Groq (Free and Fast)
        if groq_api_key and Groq:
            try:
                messages = [{"role": "system", "content": system_content}]
                for msg in history[-6:]:
                    role = "assistant" if msg["role"] == "bot" else "user"
                    messages.append({"role": role, "content": msg["text"]})
                messages.append({"role": "user", "content": message})

                client = get_groq_client()
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    max_tokens=300,
                    temperature=0.7,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"[AIService] Groq error: {e}")

        # 2. Fallback to OpenAI
        if openai_api_key and not openai_api_key.startswith("sk-..."):
            try:
                messages = [{"role": "system", "content": system_content}]
                for msg in history[-6:]:
                    role = "assistant" if msg["role"] == "bot" else "user"
                    messages.append({"role": role, "content": msg["text"]})
                messages.append({"role": "user", "content": message})

                response = get_openai_client().chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    max_tokens=200,
                    temperature=0.7,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"[AIService] OpenAI error: {e}")

        return self._fallback_reply()

    def _fallback_reply(self) -> str:
        b = self.business
        return (
            f"That is an excellent inquiry! While I specialize in our primary offerings at *{b.name}*, "
            "I've personally flagged this for our dedicated specialist to provide you with the most precise details. "
            "Our priority is ensuring you receive a tailored response. May I assist with any other details in the meantime? ✨"
        )

    def generate_faqs_from_text(self, text: str, url: str = "") -> list:
        """
        Use OpenAI to turn raw text into a list of structured FAQ objects.
        Returns: list of dicts {question, response, keywords, priority}
        """
        if not text:
            return []

        prompt = (
            f"You are an expert FAQ architect for *{self.business.name}*. "
            f"Based on the following scraped text from their website, extract 10-15 high-quality FAQ pairs. "
            f"Each FAQ should follow the tone: {self.business.tone or 'premium and helpful'}. "
            "Ensure the responses are concise (max 3 sentences). "
            "For each FAQ, also provide 4-6 lowercase keyword triggers. "
            "Output MUST be a JSON array of objects with keys: question, response, keywords (list), priority (1-10)."
            "\n\n--- SCRAPED TEXT ---\n"
            f"{text}"
        )

        if os.getenv("MOCK_MODE", "false").lower() == "true":
            print("MOCK: Generating simulated FAQs for demo...")
            import time
            time.sleep(3) # Simulate thinking time
            
            # Smart Mocking based on URL/Content
            if "apple" in text.lower() or "apple" in url.lower():
                return [
                    {"question": "What is the Apple return policy?", "response": "Most items can be returned within 14 days of receipt. Items must be in their original condition.", "keywords": ["returns", "policy", "14 days"], "priority": 10},
                    {"question": "How do I start a refund?", "response": "You can initiate a return online via your Order Status page or by visiting an Apple Store.", "keywords": ["refund", "start", "online"], "priority": 9},
                    {"question": "Are there any non-returnable items?", "response": "Opened software, personalized products, and Apple Gift Cards are generally non-returnable.", "keywords": ["non-returnable", "software", "gift cards"], "priority": 8}
                ]
            else:
                return [
                    {"question": "What are your business hours?", "response": "We are typically open Monday through Friday, 9 AM to 6 PM, and Saturday 10 AM to 4 PM.", "keywords": ["hours", "timings", "open"], "priority": 10},
                    {"question": "How can I contact support?", "response": "You can reach our team via the 'Contact Us' page on our website or by calling our main office number.", "keywords": ["contact", "support", "help"], "priority": 9},
                    {"question": "Do you offer international shipping?", "response": "Yes, we ship to over 50 countries worldwide. Shipping costs and times vary by location.", "keywords": ["shipping", "international", "delivery"], "priority": 8}
                ]

        try:
            # 1. Try Groq (Preferred: Fast & Free)
            groq_api_key = os.getenv("GROQ_API_KEY", "")
            if groq_api_key and Groq:
                try:
                    client = get_groq_client()
                    print(f"DEBUG: Extracting FAQs via Groq (Llama 3.3) for {self.business.name}")
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "system", "content": "You are a professional JSON generator. Output only valid JSON."},
                                  {"role": "user", "content": prompt}],
                        response_format={"type": "json_object"},
                        max_tokens=2000,
                        temperature=0.3,
                    )
                    content = response.choices[0].message.content
                except Exception as ge:
                    print(f"DEBUG: Groq FAQ Extraction failed: {ge}. Falling back to OpenAI...")
                    content = None
            else:
                content = None

            # 2. Fallback to OpenAI (If Groq failed or not available)
            if not content:
                print(f"DEBUG: Extracting FAQs via OpenAI for {self.business.name}")
                response = get_openai_client().chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": "You are a professional JSON generator."},
                              {"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    max_tokens=2000,
                )
                content = response.choices[0].message.content
            print(f"DEBUG: AI Raw Response: {content}")
            data = json.loads(content)
            
            # 1. Look for a list directly or under common keys
            faqs = []
            if isinstance(data, list):
                faqs = data
            elif isinstance(data, dict):
                if "faqs" in data and isinstance(data["faqs"], list):
                    faqs = data["faqs"]
                elif "faq" in data and isinstance(data["faq"], list):
                    faqs = data["faq"]
                elif len(data) > 0:
                    # Check if it's a dict of objects
                    first_val = next(iter(data.values()))
                    if isinstance(first_val, dict) and "question" in first_val:
                        faqs = list(data.values())
            
            print(f"DEBUG: Extracted {len(faqs)} FAQs")
            return faqs
        except Exception as e:
            # Automatic Fallback for Quota Limits
            if "insufficient_quota" in str(e).lower() or "429" in str(e):
                print(f"WARNING: OpenAI Quota Exceeded. Falling back to SMART MOCK MODE for Business: {self.business.name}")
                return self._generate_smart_mock_faqs(text, url)
            
            print(f"DEBUG: AIService Error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _generate_smart_mock_faqs(self, text: str, url: str) -> list:
        """Fallback mock generator when API is down or quota exceeded."""
        import time
        time.sleep(1) # Brief pause for realism
        
        # Smart detection based on niche or name
        niche = (self.business.niche or "").lower()
        name = self.business.name
        
        if "gym" in niche or "fitness" in niche:
            return [
                {"question": f"What are the membership plans at {name}?", "response": "We offer several plans including Monthly, Quarterly, and Annual memberships. Prices start from ₹999/month.", "keywords": ["membership", "plans", "price"], "priority": 10},
                {"question": "Do you offer personal training?", "response": "Yes! Our certified trainers are available for 1-on-1 sessions. You can book a free consultation via our dashboard.", "keywords": ["trainer", "personal", "booking"], "priority": 9},
                {"question": "What are the gym timings?", "response": "We are open from 6:00 AM to 10:00 PM on weekdays and 7:00 AM to 8:00 PM on weekends.", "keywords": ["timings", "hours", "open"], "priority": 8}
            ]
        elif "salon" in niche or "spa" in niche:
            return [
                {"question": f"What services does {name} offer?", "response": "We specialize in Haircuts, Styling, Facials, and relaxing Spa treatments using premium products.", "keywords": ["services", "haircut", "facial"], "priority": 10},
                {"question": "How do I book an appointment?", "response": "You can book directly through our website booking link or by messaging us here! We'll confirm instantly.", "keywords": ["book", "appointment", "schedule"], "priority": 9},
                {"question": "Do you accept walk-ins?", "response": "While we recommend booking in advance, we do accept walk-ins based on stylist availability.", "keywords": ["walk-in", "available", "now"], "priority": 8}
            ]
        else:
            # Generic but high quality mock
            return [
                {"question": f"What makes {name} special?", "response": f"{name} is dedicated to providing premium service and exceptional quality in the {niche} industry.", "keywords": ["special", "about", "quality"], "priority": 10},
                {"question": "How can I contact the business directly?", "response": f"You can reach us at our location or via the contact details provided in our profile. We are always happy to help!", "keywords": ["contact", "phone", "reach"], "priority": 9},
                {"question": "Is there a trial period for your services?", "response": "We often have introductory offers! Please check our latest updates or ask our team for current promotions.", "keywords": ["trial", "offer", "discount"], "priority": 8}
            ]
