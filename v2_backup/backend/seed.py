"""
Seed Script — Loads sample business configs from JSON and populates the DB.
Run: python seed.py
"""
import json
import os
import sys
import secrets

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from models import db
from models.business import Business
from models.faq import FAQ

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "businesses")


def seed():
    app = create_app()
    with app.app_context():
        # Clear existing data
        FAQ.query.delete()
        Business.query.delete()
        db.session.commit()

        json_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".json")]
        for filename in json_files:
            path = os.path.join(DATA_DIR, filename)
            with open(path) as f:
                data = json.load(f)

            business = Business(
                name=data["name"],
                niche=data["niche"],
                phone=data.get("phone"),
                location=data.get("location"),
                location_url=data.get("location_url"),
                booking_url=data.get("booking_url"),
                welcome_message=data.get("welcome_message"),
                tone=data.get("tone", "friendly"),
                plan="trial",
                api_key=secrets.token_urlsafe(32),
                is_active=True,
            )
            db.session.add(business)
            db.session.flush()  # Get business.id

            for faq_data in data.get("faqs", []):
                faq = FAQ(
                    business_id=business.id,
                    question=faq_data["question"],
                    keywords=json.dumps(faq_data["keywords"]),
                    response=faq_data["response"],
                    cta_label=faq_data.get("cta_label"),
                    cta_url=faq_data.get("cta_url"),
                    priority=faq_data.get("priority", 0),
                )
                db.session.add(faq)

            print(f"  ✅ Seeded: {business.name} ({len(data.get('faqs', []))} FAQs)")

        db.session.commit()
        print("\n🌱 Database seeded successfully!")


if __name__ == "__main__":
    seed()
