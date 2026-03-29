"""
Flask Application Factory
"""
from flask import Flask
from flask_cors import CORS
from config import get_config
from models import db
from models.business import Business
from models.faq import FAQ
from models.lead import Lead
from models.conversation import Conversation


def create_app():
    app = Flask(__name__, static_folder="../frontend", static_url_path="")
    app.config.from_object(get_config())

    CORS(app)
    db.init_app(app)

    @app.route("/")
    def index():
        return app.send_static_file("index.html")

    # Register blueprints
    from routes.webhook import webhook_bp
    from routes.leads import leads_bp
    from routes.dashboard import dashboard_bp

    app.register_blueprint(webhook_bp)
    app.register_blueprint(leads_bp)
    app.register_blueprint(dashboard_bp)

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5001)
