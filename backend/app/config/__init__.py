"""
App configuration package initializer.
This allows you to import config values directly via:
    from app.config import config
"""

from . import config, database

__all__ = ["config", "database"]
