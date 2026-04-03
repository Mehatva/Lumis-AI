import os
from models.business import Business
from models.faq import FAQ
from services.ai_service import get_groq_client, get_openai_client, Groq
from datetime import datetime
from models import db

class TrainingService:
    @staticmethod
    def train_business(business_id: int) -> bool:
        """
        Takes a business's raw details and FAQs and 'compresses' them 
        into a dense narrative Knowledge Base profile.
        """
        business = Business.query.get(business_id)
        if not business:
            return False

        faqs = FAQ.query.filter_by(business_id=business_id).all()
        
        # 1. Build the training context
        context = f"Business Name: {business.name}\n"
        context += f"Niche: {business.niche}\n"
        context += f"Tone: {business.tone}\n"
        context += f"Location: {business.location}\n"
        context += f"Phone: {business.phone}\n\n"
        
        context += "--- BUSINESS FAQs ---\n"
        for f in faqs:
            context += f"Q: {f.question}\nA: {f.response}\n"

        # 2. Create the Synthesis Prompt
        prompt = (
            "You are an AI Architect. Your task is to 'compress' the following business data "
            "into a dense, highly specialized Knowledge Base for a conversational AI Agent.\n\n"
            "**OBJECTIVE**:\n"
            "Create a structured profile that allows an AI to 'know' the business innately. "
            "Instead of a list of FAQs, write a coherent summary that includes:\n"
            "1. The business identity and value proposition.\n"
            "2. All key operational details (hours, prices, specific policies).\n"
            "3. Personal nuances and tone.\n\n"
            "**RULES**:\n"
            "- Be dense and factual. Do not waste tokens on fluff.\n"
            "- Ensure all specific data points (like ₹999/month) are preserved exactly.\n"
            "- Output should be a single, structured narrative block (2-4 paragraphs).\n"
            "\n--- DATA TO COMPRESS ---\n"
            f"{context}"
        )

        try:
            # Try Groq first
            groq_key = os.getenv("GROQ_API_KEY")
            trained_content = ""

            if groq_key and Groq:
                client = get_groq_client()
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "You are a professional AI Knowledge Architect. You specialize in data compression and persona synthesis."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3, # Low temperature for factual accuracy
                    max_tokens=800
                )
                trained_content = response.choices[0].message.content.strip()
            else:
                # Fallback to OpenAI
                client = get_openai_client()
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                trained_content = response.choices[0].message.content.strip()

            if trained_content:
                business.knowledge_base = trained_content
                business.last_trained_at = datetime.utcnow()
                db.session.commit()
                return True

        except Exception as e:
            print(f"[TrainingService] Error: {e}")
            return False

        return False
