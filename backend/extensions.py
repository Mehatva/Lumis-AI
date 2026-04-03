from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Primary Database Object
db = SQLAlchemy()

# Authentication & Security
bcrypt = Bcrypt()
jwt = JWTManager()

# Resource Protection (Wallet Protection)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["500 per day", "100 per hour"],
    storage_uri="memory://",
)
