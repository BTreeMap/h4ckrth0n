"""h4ckath0n – ship hackathon products fast, securely."""

__version__ = "0.1.0"

from h4ckath0n.app import create_app
from h4ckath0n.config import Settings

__all__ = ["create_app", "Settings", "__version__"]
