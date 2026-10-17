"""
Flask Extensions Registry.

Instantiates shared extensions centrally to avoid circular import issues.
"""

from flask_cors import CORS
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# Central extension instances
db = SQLAlchemy()
cors = CORS()
migrate = Migrate()
