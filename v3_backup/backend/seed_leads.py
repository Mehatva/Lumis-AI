import sys
import os
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from models import db
from models.business import Business
from models.lead import Lead

def seed_leads():
    app = create_app()
    with app.app_context():
        business = Business.query.first()
        if not business:
            print("❌ No business found. Run seed.py first.")
            return

        # Clear existing leads
        Lead.query.filter_by(business_id=business.id).delete()
        
        leads_data = [
            {
                "name": "Rahul Sharma",
                "phone": "+91 91234 56789",
                "platform": "instagram",
                "captured_at": datetime.utcnow() - timedelta(days=1),
                "is_converted": True,
                "needs_attention": False,
                "note": "Interested in Premium membership."
            },
            {
                "name": "Priya Mehta",
                "phone": "+91 98765 11111",
                "platform": "instagram",
                "captured_at": datetime.utcnow() - timedelta(hours=3),
                "is_converted": False,
                "needs_attention": True,
                "note": "Unanswered: Can I bring a guest for free?"
            },
            {
                "name": "Amit Patel",
                "phone": "+91 77777 22222",
                "platform": "instagram",
                "captured_at": datetime.utcnow() - timedelta(hours=6),
                "is_converted": False,
                "needs_attention": False,
                "note": "Asking about morning batches."
            },
            {
                "name": "Sneha Joshi",
                "phone": "+91 99999 33333",
                "platform": "instagram",
                "captured_at": datetime.utcnow() - timedelta(days=2),
                "is_converted": True,
                "needs_attention": False,
                "note": "Joined after free trial."
            }
        ]

        for ld in leads_data:
            lead = Lead(
                business_id=business.id,
                name=ld["name"],
                phone=ld["phone"],
                platform=ld["platform"],
                captured_at=ld["captured_at"],
                is_converted=ld["is_converted"],
                needs_attention=ld["needs_attention"],
                note=ld["note"]
            )
            db.session.add(lead)
        
        db.session.commit()
        print(f"✅ Seeded {len(leads_data)} leads for {business.name}")

if __name__ == "__main__":
    seed_leads()
