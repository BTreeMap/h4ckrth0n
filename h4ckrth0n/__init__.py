"""
h4ckrth0n - A library for rapid hackathon development

This module provides tools for quick setup of common hackathon project requirements
including authentication, database operations, API development, and background tasks.
"""

__version__ = "0.0.0"

from .api import API
from .app import create_app
from .auth import Auth
from .database import Database
from .tasks import TaskManager

# Enable friendly imports like: from h4ckrth0n import create_app
__all__ = ["create_app", "Database", "Auth", "API", "TaskManager"]
