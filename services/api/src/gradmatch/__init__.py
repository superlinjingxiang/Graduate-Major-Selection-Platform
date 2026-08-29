from .__about__ import __version__

__all__ = ["__version__"]
from .celery import app as celery_app

__all__ = ("celery_app",)
