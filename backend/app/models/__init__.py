# Import every model in this file so that Alembic can find all tables.
from app.models.user import User

__all__ = ["User"]