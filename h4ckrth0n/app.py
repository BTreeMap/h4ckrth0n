"""
Application factory module for creating the main app instance.
"""

import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI


def create_app(config: Optional[Dict[str, Any]] = None) -> FastAPI:
    """
    Create and configure a new FastAPI application instance.

    Args:
        config: Optional configuration dictionary to override defaults

    Returns:
        A configured FastAPI application
    """
    # Load environment variables from .env file if present
    load_dotenv()

    # Create FastAPI app with sensible defaults
    app = FastAPI(
        title="Hackathon App",
        description="API created with h4ckrth0n",
        version="0.1.0",
    )

    # Apply configuration if provided
    if config:
        for key, value in config.items():
            setattr(app.state, key, value)

    @app.get("/")
    def read_root():
        return {"message": "Welcome to your h4ckrth0n app!"}

    @app.get("/health")
    def health_check():
        return {"status": "healthy"}

    return app
