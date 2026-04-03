"""
Flask Application Factory
"""
from flask import Flask
from flask_cors import CORS
from config import get_config
from extensions import db, bcrypt, jwt, limiter
from flask_migrate import Migrate
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

def create_app():
    config = get_config()

    # 1. Initialize Sentry (if DSN is provided)
    if config.SENTRY_DSN:
        sentry_sdk.init(
            dsn=config.SENTRY_DSN,
            integrations=[FlaskIntegration()],
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
        )

    app = Flask(__name__, static_folder="../frontend", static_url_path="")
    app.config.from_object(config)

    # Initialize Extensions from Hub
    CORS(app)
    db.init_app(app)
    Migrate(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    limiter.init_app(app)

    @app.route("/")
    def index():
        return app.send_static_file("index.html")

    @app.route("/dashboard")
    def dashboard():
        return app.send_static_file("dashboard.html")

    # Register blueprints
    from routes.webhook import webhook_bp
    from routes.leads import leads_bp
    from routes.dashboard import dashboard_bp
    from routes.auth import auth_bp
    from routes.billing import billing_bp
    from routes.training import training_bp

    app.register_blueprint(webhook_bp)
    app.register_blueprint(leads_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(training_bp)

    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            print(f"DEBUG: db.create_all error (mostly harmless in production): {e}")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5001)
