import os
import sys

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db
from sqlalchemy import text

app = create_app()

def migrate():
    with app.app_context():
        # SQLite doesn't support adding columns with default values easily in some versions via ALTER,
        # but SQLAlchemy text can handle it if the column doesn't exist.
        
        print("Migrating database (Phase 2: Usage & Credits)...")
        
        try:
            # 1. Add credits_used
            db.session.execute(text("ALTER TABLE businesses ADD COLUMN credits_used INTEGER DEFAULT 0"))
            print("Added column: credits_used")
        except Exception as e:
            print(f"Skipping credits_used (likely exists): {e}")
            
        try:
            # 2. Add credits_limit
            db.session.execute(text("ALTER TABLE businesses ADD COLUMN credits_limit INTEGER DEFAULT 50"))
            print("Added column: credits_limit")
        except Exception as e:
            print(f"Skipping credits_limit (likely exists): {e}")
            
        try:
            # 3. Add billing_cycle_start
            # SQLite doesn't have a DATETIME type but uses TEXT/NUMERIC. SQLAlchemy handles the mapping.
            db.session.execute(text("ALTER TABLE businesses ADD COLUMN billing_cycle_start DATETIME"))
            print("Added column: billing_cycle_start")
        except Exception as e:
            print(f"Skipping billing_cycle_start (likely exists): {e}")
            
        # 4. Initialize existing businesses with default limits if null
        from models.business import Business
        from datetime import datetime
        
        businesses = Business.query.all()
        for b in businesses:
            if b.credits_used is None: b.credits_used = 0
            if b.credits_limit is None: b.credits_limit = 50
            if b.billing_cycle_start is None: b.billing_cycle_start = b.created_at or datetime.utcnow()
            
            # Map existing plan strings to realistic credits
            if b.plan == "starter": b.credits_limit = 500
            elif b.plan == "growth": b.credits_limit = 2500
            elif b.plan == "pro" or b.plan == "scale": b.credits_limit = 10000
            
        db.session.commit()
        print("Database migration completed successfully! ✅")

if __name__ == "__main__":
    migrate()
