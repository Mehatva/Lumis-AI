import sys
import os
from flask import Flask
from models import db
from models.user import User

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def reset_password(email, new_password):
    from app import create_app
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"User {email} not found.")
            return
        
        user.set_password(new_password)
        db.session.commit()
        print(f"Password for {email} has been reset successfully.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python reset_password.py <email> <password>")
    else:
        reset_password(sys.argv[1], sys.argv[2])
