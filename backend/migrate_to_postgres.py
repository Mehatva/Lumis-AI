import os
import sys
import sqlite3
from datetime import datetime

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db
from models.user import User
from models.business import Business
from models.faq import FAQ
from models.lead import Lead
from models.conversation import Conversation
from sqlalchemy import text

app = create_app()

def migrate():
    """
    One-way migration from SQLite to PostgreSQL.
    """
    sqlite_db_path = os.path.join(os.path.dirname(__file__), "instance", "chatbot.db")
    if not os.path.exists(sqlite_db_path):
        print(f"❌ SQLite database not found at {sqlite_db_path}")
        return

    print(f"🚀 Starting migration from SQLite ({sqlite_db_path}) to PostgreSQL...")

    with app.app_context():
        # 0. Ensure Postgres schema is ready
        db.create_all()

        # Connect to SQLite for raw reading
        conn = sqlite3.connect(sqlite_db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Helper to migrate a table
        def migrate_table(table_name, model_class):
            print(f"📦 Migrating {table_name}...")
            cur.execute(f"SELECT * FROM {table_name}")
            rows = cur.fetchall()
            
            count = 0
            for row in rows:
                data = dict(row)
                
                # Check for existing record to avoid dupes
                existing = model_class.query.get(data['id'])
                if existing:
                    continue

                # Handle date types from SQLite strings
                for key, value in data.items():
                    if isinstance(value, str) and (key.endswith('_at') or key.endswith('_start')):
                        try:
                            # Try different formats
                            if value:
                                data[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                        except:
                            pass
                
                # Create and insert
                record = model_class(**data)
                db.session.add(record)
                count += 1
            
            db.session.commit()
            print(f"✅ Migrated {count} records into {table_name}.")

        try:
            # Order matters due to foreign keys
            migrate_table("users", User)
            migrate_table("businesses", Business)
            migrate_table("faqs", FAQ)
            migrate_table("leads", Lead)
            migrate_table("conversations", Conversation)
            
            # Reset Postgres Sequences (since we forced IDs)
            tables = ["users", "businesses", "faqs", "leads", "conversations"]
            for table in tables:
                db.session.execute(text(f"SELECT setval('{table}_id_seq', (SELECT MAX(id) FROM {table}))"))
            db.session.commit()

            print("🎉 MIGRATION SUCCESSFUL! Lumis AI is now running on PostgreSQL! 🐘")
        except Exception as e:
            db.session.rollback()
            print(f"❌ MIGRATION FAILED: {e}")
        finally:
            conn.close()

if __name__ == "__main__":
    migrate()
