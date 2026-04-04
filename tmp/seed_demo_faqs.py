import os
import sys

# Add backend to path to import models
sys.path.append(os.getcwd())

from app import create_app
from models import db
from models.business import Business
from models.faq import FAQ

def seed_demo_faqs():
    app = create_app()
    with app.app_context():
        # Find the business for user mehatva06@gmail.com (ID 8)
        business = Business.query.filter_by(user_id=8).first()
        if not business:
            print("Business for user 8 not found.")
            return

        print(f"Seeding FAQs for {business.name}...")

        # Sample FAQs
        faqs_data = [
            {
                "question": "What is Lumis AI?",
                "response": "Lumis AI is a premium multi-tenant SaaS platform that automates customer engagement on Instagram and WhatsApp using advanced AI. We help businesses scale their support and lead generation 24/7.",
                "keywords": "what, about, platform, lumis ai",
                "priority": 10
            },
            {
                "question": "How do I connect my Instagram?",
                "response": "It's simple! Just go to your [Dashboard Settings] and click 'Connect Instagram'. Follow the Meta OAuth prompt to grant permissions, and your bot will be live instantly.",
                "keywords": "connect, instagram, link, setup",
                "priority": 9
            },
            {
                "question": "What plans do you offer?",
                "response": "We offer Trial, Starter, Growth, and Pro plans. The Pro plan includes unlimited AI responses, custom brand identity, and priority support.",
                "keywords": "plans, pricing, cost, subscription, pro",
                "priority": 8
            },
            {
                "question": "Can I capture leads through the bot?",
                "response": "Yes! Lumis AI automatically identifies potential customers and asks for their contact details, saving them directly to your CRM for follow-up.",
                "keywords": "leads, capture, customers, contact",
                "priority": 7
            },
            {
                "question": "Is there a human handoff feature?",
                "response": "Absolutely. If a query is too complex, the bot can alert your team to join the chat manually. You can also 'mute' the bot for specific users at any time.",
                "keywords": "human, talk to agent, person, handoff",
                "priority": 10
            }
        ]

        # Clear existing ones just in case
        FAQ.query.filter_by(business_id=business.id).delete()

        for data in faqs_data:
            faq = FAQ(
                business_id=business.id,
                question=data["question"],
                response=data["response"],
                keywords=data["keywords"],
                priority=data["priority"]
            )
            db.session.add(faq)

        db.session.commit()
        print(f"Successfully seeded {len(faqs_data)} FAQs for {business.name}.")

if __name__ == "__main__":
    seed_demo_faqs()
