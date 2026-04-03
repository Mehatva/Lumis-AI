import os
import sys
from datetime import datetime

# Add current dir to path
sys.path.append(os.getcwd())

from app import create_app
from models import db
from models.user import User
from models.business import Business
from models.lead import Lead
from models.faq import FAQ

def create_demo():
    app = create_app()
    with app.app_context():
        email = "demo@lumisai.in"
        password = "demo_password_123"
        
        # 1. Create/Update User
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(email=email, name="Demo User", is_verified=True)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            print(f"User {email} created.")
        else:
            user.is_verified = True
            user.set_password(password)
            db.session.commit()
            print(f"User {email} restored.")

        # 2. Create/Update Business (Unlock Dashboard with 'growth' plan)
        business = Business.query.filter_by(user_id=user.id).first()
        if not business:
            business = Business(
                user_id=user.id,
                name="Lumis Luxury Fitness",
                niche="gym",
                phone="+91 99999 88888",
                location="Juhu, Mumbai",
                plan="growth", # UNLOCKS DASHBOARD
                access_token=os.getenv("INSTAGRAM_ACCESS_TOKEN", ""), # RESTORE TOKEN
                instagram_page_id=os.getenv("INSTAGRAM_PAGE_ID", "17841435014143545"),
                is_active=True # ACTIVATE FOR WEBHOOK
            )
            db.session.add(business)
            db.session.commit()
            print(f"Business {business.name} created and activated.")
        else:
            business.plan = "growth"
            business.is_active = True # ENSURE ACTIVE
            business.access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN", "") # UPDATE TOKEN
            business.instagram_page_id = os.getenv("INSTAGRAM_PAGE_ID", "17841435014143545")
            db.session.commit()
            print(f"Business '{business.name}' token and status updated.")
        
        print(f"Business '{business.name}' is active on the 'growth' plan.")

        # 3. Add Mock Leads (if empty)
        if Lead.query.filter_by(business_id=business.id).count() == 0:
            leads = [
                Lead(business_id=business.id, name="Aarav Sharma", phone="+91 98765 43210", note="Interested in personal training.", needs_attention=True),
                Lead(business_id=business.id, name="Isha Patel", phone="+91 91234 56789", note="Inquiry about yoga sessions.", is_converted=True),
                Lead(business_id=business.id, name="Vikram Singh", phone="+91 99887 76655", note="Asking for membership prices.")
            ]
            db.session.add_all(leads)
            db.session.commit()

        # 4. Add Mock FAQs (if empty)
        if FAQ.query.filter_by(business_id=business.id).count() == 0:
            faqs = [
                FAQ(business_id=business.id, question="What are your timings?", keywords='["timings", "open", "hours"]', response="We are open from 6:00 AM to 10:00 PM daily."),
                FAQ(business_id=business.id, question="Do you have personal trainers?", keywords='["trainer", "coach"]', response="Yes, we have certified personal trainers available for customized sessions.")
            ]
            db.session.add_all(faqs)
            db.session.commit()

        print("\n✅ Demo environment restored!")
        print(f"Email: {email}")
        print(f"Password: {password}")

if __name__ == "__main__":
    create_demo()
